import frappe


def update_item_qty_on_bin_change(doc, method=None):
	bin = doc
	item_code = doc.item_code

	# Fetch default warehouses from Item Default child table
	item_doc = frappe.get_doc("Item", item_code)
	default_warehouses = [row.default_warehouse for row in item_doc.item_defaults]

	if not default_warehouses:
		return

	# Fetch the latest quantity from Bin records for default warehouses
	bins = frappe.get_all(
		"Bin",
		filters={"item_code": item_code, "warehouse": ["in", default_warehouses]},
		fields=["actual_qty", "warehouse", "creation"],
		order_by="creation desc",
	)

	latest_qty_per_warehouse = {}
	for bin in bins:
		if bin.warehouse not in latest_qty_per_warehouse:
			latest_qty_per_warehouse[bin.warehouse] = bin.actual_qty
		if bin.warehouse == doc.warehouse:
			latest_qty_per_warehouse[bin.warehouse] = latest_qty_per_warehouse[bin.warehouse] + float(
				doc.actual_qty
			)

	# Calculate the total quantity in default warehouses
	total_qty = sum(latest_qty_per_warehouse.values())

	# Update the Item record with the total quantity (if needed)
	item_doc.db_set("custom_default_warehouse_qty", total_qty)
