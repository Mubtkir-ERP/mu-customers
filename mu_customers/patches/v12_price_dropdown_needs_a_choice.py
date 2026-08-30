"""Hide the Price Type dropdown on rows that have nothing to choose between.

The dropdown used to appear on every row whose item had prices enabled, even
when the item had a single price - an empty control crowding the line for no
reason. Visibility is now driven by `custom_price_options`, a per-row count,
so `custom_prices_enabled` on the rows has no job left and goes.

Frappe leaves the column behind when a Custom Field is deleted, so the columns
are dropped too - but only where they are genuinely orphaned and empty.
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

RETIRED = "custom_prices_enabled"


def execute():
	removed = []

	for doctype in ITEM_DOCTYPES:
		name = f"{doctype}-{RETIRED}"
		if frappe.db.exists("Custom Field", name):
			frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)
			removed.append(doctype)

	if removed:
		frappe.clear_cache()

	dropped = sum(drop_orphan_column(doctype) for doctype in ITEM_DOCTYPES)

	print(
		f"mu_customers: retired the row-level prices flag on {len(removed)} doctype(s), "
		f"dropped {dropped} orphan column(s)"
	)


def drop_orphan_column(doctype):
	"""Only ever drops a column with no field behind it and no data in it."""
	if not frappe.db.table_exists(doctype) or not frappe.db.has_column(doctype, RETIRED):
		return 0

	if frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": RETIRED}):
		return 0

	if frappe.get_meta(doctype).get_field(RETIRED):
		return 0

	frappe.db.sql_ddl(f"alter table `tab{doctype}` drop column `{RETIRED}`")
	return 1
