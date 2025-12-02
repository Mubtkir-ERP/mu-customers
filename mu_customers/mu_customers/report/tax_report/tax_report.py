# Copyright (c) 2025, Mubtkir and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.query_builder.functions import NullIf


def execute(filters=None):
	filters = filters or {}

	columns = [
		{
			"label": _("Invoice No"),
			"fieldname": "invoice_no",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 250,
		},
		{"label": _("Party"), "fieldname": "party", "fieldtype": "Data", "width": 150},
		{"label": _("Tax ID"), "fieldname": "tax_id", "fieldtype": "Data", "width": 180},
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
		# Add an empty row for better readability
		data.append(
			{
				"invoice_no": "",
				"party": "",
				"tax_id": "",
				"posting_date": None,
				"item_name": "",
				"net_amount": None,
				"tax_amount": None,
				"indent": 0,
			}
		)

		total_net += section_net
		total_tax += section_tax

	data.append(
		{"invoice_no": _("Grand Total"), "net_amount": total_net, "tax_amount": total_tax, "indent": 0}
	)

	return columns, data


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
			invoice.tax_id,
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
			results.append(inv_row)
			last_invoice_no = row["invoice_no"]

		if row.get("item_name"):
			results.append(
				{"item_name": row["item_name"], "indent": 2, "net_amount": None, "tax_amount": None}
			)

	return results
