# Copyright (c) 2026, Amr and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType


def has_voucher_entry_tables():
	return frappe.db.table_exists("Vouchers Entry") and frappe.db.table_exists("Voucher Entry Account")


def execute(filters=None):
	filters = filters or {}

	columns = [
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Data",
			"width": 0,
			"hidden": 1,
		},
		{
			"label": _("Invoice No"),
			"fieldname": "invoice_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 250,
		},
		{"label": _("Party"), "fieldname": "party", "fieldtype": "Data", "width": 150},
		{
			"label": _("VAT Registration Number"),
			"fieldname": "custom_vat_registration_number",
			"fieldtype": "Data",
			"width": 180,
		},
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 150},
		{"label": _("Bill No"), "fieldname": "bill_no", "fieldtype": "Data", "width": 150},
		{"label": _("Remarks"), "fieldname": "remarks", "fieldtype": "Data", "width": 250},
		{"label": _("Net Amount"), "fieldname": "net_amount", "fieldtype": "Currency", "width": 130},
		{"label": _("Tax Amount"), "fieldname": "tax_amount", "fieldtype": "Currency", "width": 130},
	]

	data = []

	sections = {
		_("Sales Invoices"): {"doctype": "Sales Invoice", "is_return": 0},
		_("Sales Returns"): {"doctype": "Sales Invoice", "is_return": 1},
		_("Purchase Invoices"): {"doctype": "Purchase Invoice", "is_return": 0},
		_("Purchase Returns"): {"doctype": "Purchase Invoice", "is_return": 1},
	}

	total_net = 0
	total_tax = 0

	for section_name, params in sections.items():
		invoices = get_invoices(params["doctype"], filters, params["is_return"])
		section_net = sum(row.get("net_amount", 0) for row in invoices if row.get("indent") == 1)
		section_tax = sum(row.get("tax_amount", 0) for row in invoices if row.get("indent") == 1)

		if (params["doctype"] == "Purchase Invoice" and not params["is_return"]) or (
			params["doctype"] == "Sales Invoice" and params["is_return"]
		):
			section_net = -section_net
			section_tax = -section_tax

		data.append({"invoice_no": section_name, "net_amount": None, "tax_amount": None, "indent": 0})
		data.extend(invoices)
		data.append(
			{
				"invoice_no": f"{section_name} Total",
				"net_amount": abs(section_net),
				"tax_amount": abs(section_tax),
				"indent": 0,
			}
		)
		data.append(_empty_row())

		total_net += section_net
		total_tax += section_tax

	# ── Voucher Entries section ──────────────────────────────────────────────
	if has_voucher_entry_tables():
		voucher_section_name = _("Voucher Entries")
		voucher_rows = get_voucher_entries(filters)
		voucher_net = sum(row.get("net_amount", 0) for row in voucher_rows if row.get("indent") == 1)
		voucher_tax = sum(row.get("tax_amount", 0) for row in voucher_rows if row.get("indent") == 1)

		if voucher_rows:
			data.append({"invoice_no": voucher_section_name, "net_amount": None, "tax_amount": None, "indent": 0})
			data.extend(voucher_rows)
			data.append(
				{
					"invoice_no": f"{voucher_section_name} Total",
					"net_amount": voucher_net,
					"tax_amount": voucher_tax,
					"indent": 0,
				}
			)
			data.append(_empty_row())

			total_net += voucher_net
			total_tax += voucher_tax

	# ── Journal Entries section ──────────────────────────────────────────────
	journal_section_name = _("Journal Entries")
	journal_rows = get_journal_entries(filters)
	journal_net = sum(row.get("net_amount", 0) for row in journal_rows if row.get("indent") == 1)
	journal_tax = sum(row.get("tax_amount", 0) for row in journal_rows if row.get("indent") == 1)

	if journal_rows:
		data.append({"invoice_no": journal_section_name, "net_amount": None, "tax_amount": None, "indent": 0})
		data.extend(journal_rows)
		data.append(
			{
				"invoice_no": f"{journal_section_name} Total",
				"net_amount": journal_net,
				"tax_amount": journal_tax,
				"indent": 0,
			}
		)
		data.append(_empty_row())

		total_net += journal_net
		total_tax += journal_tax

	data.append(
		{"invoice_no": _("Grand Total"), "net_amount": total_net, "tax_amount": total_tax, "indent": 0}
	)

	return columns, data


# ── helpers ──────────────────────────────────────────────────────────────────

def _empty_row():
	return {
		"invoice_no": "",
		"party": "",
		"custom_vat_registration_number": "",
		"posting_date": None,
		"bill_no": "",
		"remarks": "",
		"net_amount": None,
		"tax_amount": None,
		"indent": 0,
	}


def get_tax_accounts(filters):
	tax_accounts = filters.get("tax_account")
	if not tax_accounts:
		return []

	if isinstance(tax_accounts, str):
		try:
			import json
			tax_accounts = json.loads(tax_accounts)
		except Exception:
			tax_accounts = [tax_accounts]

	return tax_accounts


def get_voucher_entries(filters):
	"""
	Pull vouchers from GL Entry (excluding Sales/Purchase Invoice).

	Each child row from `Voucher Entry Account` is returned individually.
	When a tax_account filter is applied, rows whose `account` matches
	the filter contribute their `amount` as tax_amount (net_amount = 0).

	Party VAT number:
	  - party_type == "Customer"  → Customer.custom_vat_registration_number
	  - party_type == "Supplier"  → Supplier.tax_id
	"""
	if not has_voucher_entry_tables():
		return []

	gl = DocType("GL Entry")
	ve = DocType("Vouchers Entry")
	vea = DocType("Voucher Entry Account")

	EXCLUDED_VOUCHER_TYPES = ("Sales Invoice", "Purchase Invoice")

	tax_accounts = get_tax_accounts(filters)

	from pypika import Case

	# ── child rows sub-query: individual rows, no aggregation ────────────
	if tax_accounts:
		amounts_sub = (
			frappe.qb.from_(vea)
			.select(
				vea.parent,
				vea.name.as_("vea_name"),
				vea.user_remark,
				Case()
					.when(vea.taxes.isnotnull() & (vea.taxes != ""), vea.amount)
					.else_(0)
					.as_("net_total"),
				Case()
					.when(vea.account.isin(tax_accounts), vea.amount)
					.when(vea.taxes.isnotnull() & (vea.taxes != ""), vea.tax_amount)
					.else_(0)
					.as_("tax_total"),
			)
			.where(
				(vea.taxes.isnotnull() & (vea.taxes != "")) |
				vea.account.isin(tax_accounts)
			)
		)
	else:
		amounts_sub = (
			frappe.qb.from_(vea)
			.select(
				vea.parent,
				vea.name.as_("vea_name"),
				vea.user_remark,
				vea.amount.as_("net_total"),
				vea.tax_amount.as_("tax_total"),
			)
			.where(vea.taxes.isnotnull())
			.where(vea.taxes != "")
		)

	# ── customer VAT sub-query ────────────────────────────────────────────
	customer = DocType("Customer")
	cust_sub = (
		frappe.qb.from_(customer)
		.select(
			customer.name.as_("cust_name"),
			customer.customer_name,
			customer.custom_vat_registration_number.as_("cust_vat"),
		)
	)

	# ── supplier tax_id sub-query ─────────────────────────────────────────
	supplier = DocType("Supplier")
	supp_sub = (
		frappe.qb.from_(supplier)
		.select(
			supplier.name.as_("supp_name"),
			supplier.supplier_name,
			supplier.tax_id.as_("supp_tax_id"),
		)
	)

	query = (
		frappe.qb.from_(gl)
		.inner_join(ve).on(ve.name == gl.voucher_no)
		.inner_join(amounts_sub).on(amounts_sub.parent == ve.name)
		.left_join(cust_sub).on(
			(gl.party_type == "Customer") & (cust_sub.cust_name == gl.party)
		)
		.left_join(supp_sub).on(
			(gl.party_type == "Supplier") & (supp_sub.supp_name == gl.party)
		)
		.select(
			gl.voucher_no.as_("invoice_no"),
			gl.posting_date,
			gl.party.as_("party"),
			gl.party_type,
			amounts_sub.user_remark,
			amounts_sub.vea_name,
			amounts_sub.net_total.as_("net_amount"),
			amounts_sub.tax_total.as_("tax_amount"),
			cust_sub.cust_vat.as_("cust_vat"),
			cust_sub.customer_name,
			supp_sub.supp_tax_id.as_("supp_tax_id"),
			supp_sub.supplier_name,
			ve.payment_type,
		)
		.where(gl.is_cancelled == 0)
		.where(gl.voucher_type.notin(EXCLUDED_VOUCHER_TYPES))
		.groupby(gl.voucher_no, amounts_sub.vea_name)
	)

	if filters.get("company"):
		query = query.where(gl.company == filters["company"])
	if filters.get("from_date"):
		query = query.where(gl.posting_date >= filters["from_date"])
	if filters.get("to_date"):
		query = query.where(gl.posting_date <= filters["to_date"])
	if filters.get("invoice_no"):
		query = query.where(gl.voucher_no == filters["invoice_no"])

	if tax_accounts:
		gl_tax = DocType("GL Entry")
		tax_doc_query = (
			frappe.qb.from_(gl_tax)
			.select(gl_tax.voucher_no)
			.where(gl_tax.account.isin(tax_accounts))
			.where(gl_tax.is_cancelled == 0)
			.distinct()
		)
		query = query.where(gl.voucher_no.isin(tax_doc_query))

	rows = query.run(as_dict=True)
	results = []

	for row in rows:
		if row.get("party_type") == "Customer":
			vat_number = row.get("cust_vat") or ""
			party_name = row.get("customer_name") or row.get("party")
		elif row.get("party_type") == "Supplier":
			vat_number = row.get("supp_tax_id") or ""
			party_name = row.get("supplier_name") or row.get("party")
		else:
			vat_number = ""
			party_name = row.get("party")

		net_amount = abs(row.get("net_amount") or 0)
		tax_amount = abs(row.get("tax_amount") or 0)

		if row.get("payment_type") == "Pay":
			net_amount = -net_amount
			tax_amount = -tax_amount

		results.append(
			{
				"invoice_no": row["invoice_no"],
				"voucher_type": "Vouchers Entry",
				"posting_date": row["posting_date"],
				"party": party_name or "",
				"custom_vat_registration_number": vat_number,
				"bill_no": "",
				"remarks": row.get("user_remark") or "",
				"net_amount": net_amount,
				"tax_amount": tax_amount,
				"indent": 1,
			}
		)

	return results


def get_invoices(doctype, filters, is_return):
	invoice = DocType(doctype)
	invoice_item = DocType(f"{doctype} Item")

	# Determine party id / name fields
	if doctype == "Sales Invoice":
		party_id_field = invoice.customer
		party_name_field = invoice.customer_name
	else:
		party_id_field = invoice.supplier
		party_name_field = invoice.supplier_name

	query = (
		frappe.qb.from_(invoice)
		.select(
			invoice.name.as_("invoice_no"),
			invoice.posting_date,
			party_id_field.as_("party_id"),
			party_name_field.as_("party"),
			invoice.net_total.as_("net_amount"),
			invoice.total_taxes_and_charges.as_("tax_amount"),
			invoice.remarks,
		)
		.where(invoice.docstatus == 1)
		.where(invoice.is_return == is_return)
	)

	if doctype == "Purchase Invoice":
		query = query.select(invoice.bill_no)

	if filters.get("company"):
		query = query.where(invoice.company == filters["company"])
	if filters.get("from_date"):
		query = query.where(invoice.posting_date >= filters["from_date"])
	if filters.get("to_date"):
		query = query.where(invoice.posting_date <= filters["to_date"])
	if filters.get("party"):
		query = query.where(party_id_field == filters["party"])
	if filters.get("invoice_no"):
		query = query.where(invoice.name == filters["invoice_no"])
	if not filters.get("include_non_taxed"):
		query = query.where(invoice.total_taxes_and_charges != 0)

	tax_accounts = get_tax_accounts(filters)
	if tax_accounts:
		gl_tax = DocType("GL Entry")
		tax_doc_query = (
			frappe.qb.from_(gl_tax)
			.select(gl_tax.voucher_no)
			.where(gl_tax.account.isin(tax_accounts))
			.where(gl_tax.is_cancelled == 0)
			.distinct()
		)
		query = query.where(invoice.name.isin(tax_doc_query))

	# ── VAT number: Customer → custom_vat_registration_number
	#               Supplier → tax_id  ──────────────────────────────────────
	if doctype == "Sales Invoice":
		party_master = DocType("Customer")
		query = (
			query
			.left_join(party_master).on(party_master.name == invoice.customer)
			.select(party_master.custom_vat_registration_number)
		)
	else:
		party_master = DocType("Supplier")
		query = (
			query
			.left_join(party_master).on(party_master.name == invoice.supplier)
			.select(party_master.tax_id.as_("custom_vat_registration_number"))
		)

	rows = query.run(as_dict=True)
	results = []
	last_invoice_no = None

	for row in rows:
		if row["invoice_no"] != last_invoice_no:
			inv_row = {
				"invoice_no": row["invoice_no"],
				"voucher_type": doctype,
				"posting_date": row["posting_date"],
				"party": row.get("party") or "",
				"custom_vat_registration_number": row.get("custom_vat_registration_number") or "",
				"bill_no": row.get("bill_no") or "",
				"remarks": row.get("remarks") or "",
				"net_amount": abs(row.get("net_amount") or 0),
				"tax_amount": abs(row.get("tax_amount") or 0),
				"indent": 1,
			}
			results.append(inv_row)
			last_invoice_no = row["invoice_no"]

	return results


def get_journal_entries(filters):
	"""
	Pull individual tax-account GL rows from Journal Entries.
	Each tax GL entry becomes its own row in the report.
	"""
	gl = DocType("GL Entry")
	account = DocType("Account")

	tax_accounts = get_tax_accounts(filters)

	query = (
		frappe.qb.from_(gl)
		.select(
			gl.voucher_no.as_("invoice_no"),
			gl.posting_date,
			gl.remarks,
			(gl.credit - gl.debit).as_("tax_amount"),
		)
		.where(gl.is_cancelled == 0)
		.where(gl.voucher_type == "Journal Entry")
	)

	if tax_accounts:
		query = query.where(gl.account.isin(tax_accounts))
	else:
		query = (
			query
			.inner_join(account).on(gl.account == account.name)
			.where(account.account_type.isin(["Tax", "Charge", "Duties and Taxes", "Tax / Duty"]))
		)

	if filters.get("company"):
		query = query.where(gl.company == filters["company"])
	if filters.get("from_date"):
		query = query.where(gl.posting_date >= filters["from_date"])
	if filters.get("to_date"):
		query = query.where(gl.posting_date <= filters["to_date"])
	if filters.get("invoice_no"):
		query = query.where(gl.voucher_no == filters["invoice_no"])

	rows = query.run(as_dict=True)

	results = []
	for row in rows:
		tax_amount = row.get("tax_amount") or 0

		results.append(
			{
				"invoice_no": row["invoice_no"],
				"voucher_type": "Journal Entry",
				"posting_date": row["posting_date"],
				"party": "",
				"custom_vat_registration_number": "",
				"bill_no": "",
				"remarks": row.get("remarks") or "",
				"net_amount": 0,
				"tax_amount": tax_amount,
				"indent": 1,
			}
		)

	return results
