# Copyright (c) 2025, Mubtkir and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType


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
		{"label": _("Item"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 250},
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
	voucher_section_name = _("Voucher Entries")
	voucher_rows = get_voucher_entries(filters)
	voucher_net = sum(row.get("net_amount", 0) for row in voucher_rows if row.get("indent") == 1)
	voucher_tax = sum(row.get("tax_amount", 0) for row in voucher_rows if row.get("indent") == 1)

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
	# ────────────────────────────────────────────────────────────────────────

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
		"item_name": "",
		"description": "",
		"net_amount": None,
		"tax_amount": None,
		"indent": 0,
	}


def get_voucher_entries(filters):
	"""
	Pull vouchers from GL Entry (excluding Sales/Purchase Invoice).

	- net_amount : sum of `amount` from `Voucher Entry Account` child rows where `taxes` IS set
	- tax_amount : sum of `tax_amount` from `Voucher Entry Account` child rows where `taxes` IS set

	Party VAT number:
	  - party_type == "Customer"  → Customer.custom_vat_registration_number
	  - party_type == "Supplier"  → Supplier.tax_id
	"""
	gl  = DocType("GL Entry")
	ve  = DocType("Vouchers Entry")
	vea = DocType("Voucher Entry Account")

	EXCLUDED_VOUCHER_TYPES = ("Sales Invoice", "Purchase Invoice")

	# ── child rows sub-query: only where taxes is set ─────────────────────
	amounts_sub = (
		frappe.qb.from_(vea)
		.select(
			vea.parent,
			frappe.qb.functions("SUM", vea.amount).as_("net_total"),
			frappe.qb.functions("SUM", vea.tax_amount).as_("tax_total"),
		)
		.where(vea.taxes.isnotnull())
		.where(vea.taxes != "")
		.groupby(vea.parent)
	)

	# ── customer VAT sub-query ────────────────────────────────────────────
	customer = DocType("Customer")
	cust_sub = (
		frappe.qb.from_(customer)
		.select(
			customer.name.as_("cust_name"),
			customer.custom_vat_registration_number.as_("cust_vat"),
		)
	)

	# ── supplier tax_id sub-query ─────────────────────────────────────────
	supplier = DocType("Supplier")
	supp_sub = (
		frappe.qb.from_(supplier)
		.select(
			supplier.name.as_("supp_name"),
			supplier.tax_id.as_("supp_tax_id"),
		)
	)

	query = (
		frappe.qb.from_(gl)
		.inner_join(ve).on(ve.name == gl.voucher_no)
		.inner_join(amounts_sub).on(amounts_sub.parent == ve.name)  # inner join: skip vouchers with no tax lines
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
			amounts_sub.net_total.as_("net_amount"),
			amounts_sub.tax_total.as_("tax_amount"),
			cust_sub.cust_vat.as_("cust_vat"),
			supp_sub.supp_tax_id.as_("supp_tax_id"),
		)
		.where(gl.is_cancelled == 0)
		.where(gl.voucher_type.notin(EXCLUDED_VOUCHER_TYPES))
		.groupby(gl.voucher_no)
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
		if row.get("party_type") == "Customer":
			vat_number = row.get("cust_vat") or ""
		elif row.get("party_type") == "Supplier":
			vat_number = row.get("supp_tax_id") or ""
		else:
			vat_number = ""

		results.append(
			{
				"invoice_no": row["invoice_no"],
				"voucher_type": "Vouchers Entry",
				"posting_date": row["posting_date"],
				"party": row.get("party") or "",
				"custom_vat_registration_number": vat_number,
				"item_name": "",
				"description": "",
				"net_amount": abs(row.get("net_amount") or 0),
				"tax_amount": abs(row.get("tax_amount") or 0),
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
		.left_join(invoice_item)
		.on(invoice_item.parent == invoice.name)
		.select(
			invoice.name.as_("invoice_no"),
			invoice.posting_date,
			party_id_field.as_("party_id"),
			party_name_field.as_("party"),
			invoice.net_total.as_("net_amount"),
			invoice.total_taxes_and_charges.as_("tax_amount"),
			invoice_item.item_name,
			invoice_item.description,
		)
		.where(invoice.docstatus == 1)
		.where(invoice.is_return == is_return)
	)

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
				"item_name": "",
				"description": "",
				"net_amount": abs(row.get("net_amount") or 0),
				"tax_amount": abs(row.get("tax_amount") or 0),
				"indent": 1,
			}
			results.append(inv_row)
			last_invoice_no = row["invoice_no"]

		if row.get("item_name"):
			results.append(
				{
					"item_name": row["item_name"],
					"description": row.get("description") or "",
					"indent": 2,
					"net_amount": None,
					"tax_amount": None,
				}
			)

	return results