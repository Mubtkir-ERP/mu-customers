# Copyright (c) 2025, Mubtkir and contributors
# For license information, please see license.txt

import frappe

# Rows that mean the stock movement already happened on another document.
# ERPNext hides Update Stock in exactly these cases (see its depends_on), and
# turning it on anyway would post the movement a second time.
LINKED_ROW_FIELD = {
	"Sales Invoice": "dn_detail",
	"Purchase Invoice": "pr_detail",
}


def force_update_stock(doc, method=None):
	"""Hold Update Stock on when the setting says it is not negotiable.

	The form already makes the checkbox read-only, but read-only is a UI state:
	a Data Import, an API call or a server script can still write 0. Forcing it
	here means the setting has the same effect whatever the entry point.

	Invoices drawing their items from a Delivery Note or a Purchase Receipt are
	left alone - those already moved the stock, and ERPNext itself hides the
	option for them.
	"""
	if doc.update_stock:
		return

	if not frappe.db.get_single_value("Extra Features Settings", "force_update_stock"):
		return

	if is_linked_to_stock_document(doc):
		return

	doc.update_stock = 1


def is_linked_to_stock_document(doc):
	field = LINKED_ROW_FIELD.get(doc.doctype)
	if not field:
		return False

	return any(row.get(field) for row in (doc.get("items") or []))


def is_default_remarks(val):
	"""Check if the remarks value is ERPNext's default placeholder."""
	if not val:
		return False
	val_str = str(val).strip()
	val_clean = val_str.rstrip(".: ").lower()
	return (
		val_clean in ("no remarks", "لا ملاحظات", "لا توجد ملاحظات")
		or val_str in (frappe._("No Remarks"), frappe._("No remarks"))
	)


def clear_default_remarks(doc, method=None):
	"""Clear ERPNext's automatic 'No Remarks' filler so remarks stays empty unless user entered text."""
	if doc.docstatus != 0:
		return

	if is_default_remarks(doc.get("remarks")):
		doc.remarks = ""


def clean_remarks_onload(doc, method=None):
	"""Ensure default placeholder remarks are empty when loading document in Desk without dirtying form."""
	if is_default_remarks(doc.get("remarks")):
		doc.remarks = ""
		if doc.name and not doc.is_new():
			frappe.db.set_value(doc.doctype, doc.name, "remarks", None, update_modified=False)
