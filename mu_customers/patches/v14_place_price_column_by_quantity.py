"""Sit the Price Type column between Quantity and Rate.

It was anchored to `uom`, which is not shown in the grid, so the column landed
next to Rate rather than beside the quantity it prices. Anchoring it to `qty`
puts it where it reads naturally, in the grid and in the expanded row alike.

Width is pinned to a single unit here. The grid has a fixed budget of column
units and drops any column that overruns it, so a wide custom column costs the
document a standard one - `columns` is not cosmetic in a Frappe grid.
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

FIELD = "custom_item_price_type"


def execute():
	moved = 0

	for doctype in ITEM_DOCTYPES:
		name = f"{doctype}-{FIELD}"
		if not frappe.db.exists("Custom Field", name):
			continue

		current = frappe.db.get_value("Custom Field", name, ["insert_after", "columns"], as_dict=True)
		if current.insert_after == "qty" and current.columns == 1:
			continue

		if frappe.db.has_column(doctype, "qty"):
			frappe.db.set_value("Custom Field", name, {"insert_after": "qty", "columns": 1})
			moved += 1

	if moved:
		frappe.clear_cache()

	print(f"mu_customers: repositioned the price column on {moved} doctype(s)")
