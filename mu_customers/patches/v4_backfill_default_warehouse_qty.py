import frappe

from mu_customers.default_warehouse_qty import compute

# Default Warehouse Qty is written by a hook that only fires on stock movement,
# so every item that already held stock when this app was installed still reads
# zero. Total them once here so the field is right from the first time anyone
# opens the Item form.


def execute():
	item_codes = frappe.get_all(
		"Item Default",
		filters={"parenttype": "Item", "default_warehouse": ["is", "set"]},
		pluck="parent",
		distinct=True,
	)

	updated = 0
	for item_code in item_codes:
		if not frappe.db.exists("Item", item_code):
			continue

		qty = compute(item_code)["qty"]
		if frappe.db.get_value("Item", item_code, "custom_default_warehouse_qty") == qty:
			continue

		frappe.db.set_value(
			"Item", item_code, "custom_default_warehouse_qty", qty, update_modified=False
		)
		updated += 1

	frappe.db.commit()
	print(f"mu_customers: backfilled default warehouse qty on {updated} item(s)")
