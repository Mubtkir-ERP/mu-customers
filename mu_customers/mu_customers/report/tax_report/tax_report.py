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
		"net_amount": None,
		"tax_amount": None,
		"indent": 0,
	}


def get_voucher_entries(filters):
	"""
	Pull vouchers from GL Entry (excluding Sales/Purchase Invoice),
	joined with the custom 'Vouchers Entry' doctype to get:
	  - net_amount : total_allocated_amount  (from Vouchers Entry)
	  - tax_amount : total_taxes_and_charges (from Vouchers Entry)
	"""
	gl = DocType("GL Entry")
	ve = DocType("Vouchers Entry")

	EXCLUDED_VOUCHER_TYPES = ("Sales Invoice", "Purchase Invoice")

	query = (
		frappe.qb.from_(gl)
		.inner_join(ve)
		.on(ve.name == gl.voucher_no)
		.select(
			gl.voucher_no.as_("invoice_no"),
			gl.posting_date,
			gl.party.as_("party"),
			ve.total_allocated_amount.as_("net_amount"),
			ve.total_taxes.as_("tax_amount"),
		)
		.where(gl.is_cancelled == 0)
		.where(gl.voucher_type.notin(EXCLUDED_VOUCHER_TYPES))
		.groupby(gl.voucher_no)
	)

	if filters.get("from_date"):
		query = query.where(gl.posting_date >= filters["from_date"])
	if filters.get("to_date"):
		query = query.where(gl.posting_date <= filters["to_date"])
	if filters.get("invoice_no"):
		query = query.where(gl.voucher_no == filters["invoice_no"])
	if not filters.get("include_non_taxed"):
		query = query.where(ve.total_taxes != 0)

	rows = query.run(as_dict=True)
	results = []

	for row in rows:
		results.append(
			{
				"invoice_no": row["invoice_no"],
				"voucher_type": "Vouchers Entry",
				"posting_date": row["posting_date"],
				"party": row.get("party") or "",
				"custom_vat_registration_number": "",
				"item_name": "",
				"net_amount": abs(row.get("net_amount") or 0),
				"tax_amount": abs(row.get("tax_amount") or 0),
				"indent": 1,
			}
		)

	return results


def get_invoices(doctype, filters, is_return):
	invoice = DocType(doctype)
	invoice_item = DocType(f"{doctype} Item")

	query = (
		frappe.qb.from_(invoice)
		.left_join(invoice_item)
		.on(invoice_item.parent == invoice.name)
		.select(
			invoice.name.as_("invoice_no"),
			invoice.posting_date,
			(invoice.customer if doctype == "Sales Invoice" else invoice.supplier).as_("party"),
			invoice.net_total.as_("net_amount"),
			invoice.total_taxes_and_charges.as_("tax_amount"),
			invoice_item.item_name,
		)
		.where(invoice.docstatus == 1)
		.where(invoice.is_return == is_return)
	)

	if filters.get("from_date"):
		query = query.where(invoice.posting_date >= filters["from_date"])
	if filters.get("to_date"):
		query = query.where(invoice.posting_date <= filters["to_date"])
	if filters.get("party"):
		if doctype == "Sales Invoice":
			query = query.where(invoice.customer == filters["party"])
		else:
			query = query.where(invoice.supplier == filters["party"])
	if doctype == "Sales Invoice":
		customer = DocType("Customer")
		query = (
			query.select(customer.custom_vat_registration_number)
			.left_join(customer)
			.on(customer.name == invoice.customer)
		)
	if filters.get("invoice_no"):
		query = query.where(invoice.name == filters["invoice_no"])
	if not filters.get("include_non_taxed"):
		query = query.where(invoice.total_taxes_and_charges != 0)

	rows = query.run(as_dict=True)
	results = []
	last_invoice_no = None

	for row in rows:
		if row["invoice_no"] != last_invoice_no:
			inv_row = row.copy()
			inv_row["item_name"] = ""
			inv_row["indent"] = 1
			inv_row["net_amount"] = abs(inv_row.get("net_amount") or 0)
			inv_row["tax_amount"] = abs(inv_row.get("tax_amount") or 0)
			inv_row["voucher_type"] = doctype
			results.append(inv_row)
			last_invoice_no = row["invoice_no"]

		if row.get("item_name"):
			results.append(
				{"item_name": row["item_name"], "indent": 2, "net_amount": None, "tax_amount": None}
			)

	return results