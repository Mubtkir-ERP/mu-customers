"""Retire the Select Price button now that price selection is a dropdown.

Fixtures only create and update records; they never delete the ones an earlier
version installed. The button stays on every item grid until it is removed
here.
"""

import frappe

ITEM_DOCTYPES = (
	"Sales Invoice Item",
	"Sales Order Item",
	"Delivery Note Item",
	"Quotation Item",
	"Purchase Invoice Item",
	"Purchase Order Item",
	"Purchase Receipt Item",
)


def execute():
	removed = []

	for doctype in ITEM_DOCTYPES:
		name = f"{doctype}-custom_select_price"
		if frappe.db.exists("Custom Field", name):
			frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)
			removed.append(name)

	if removed:
		frappe.clear_cache()
		print(f"mu_customers: removed {len(removed)} Select Price button(s)")
