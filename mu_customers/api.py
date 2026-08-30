import frappe


@frappe.whitelist()
def get_item_stock_levels(item_code):
	"""Warehouse-by-warehouse stock for one item, in a single round trip.

	The Sales Invoice popup used to chain two frappe.client calls per item row
	(read the settings Single, then list every Bin) before it could draw
	anything, which is what made it feel like the form had locked up.
	"""
	frappe.has_permission("Item", "read", doc=item_code, throw=True)

	rows = frappe.get_all(
		"Bin",
		filters={"item_code": item_code, "actual_qty": ["!=", 0]},
		fields=["warehouse", "actual_qty", "stock_uom"],
		order_by="warehouse asc",
	)

	return {
		"rows": rows,
		"total": sum(r.actual_qty or 0 for r in rows),
	}


@frappe.whitelist()
def get_default_warehouse_qty(item_code, company=None, warehouses=None):
	"""Live total across the item's default warehouses, for the Item form.

	The form shows this on every refresh instead of trusting the stored value,
	which can lag behind a stock movement whose background job has not run yet.

	`warehouses` lets the form total a default warehouse the user has just
	picked but not saved; without it the item's stored defaults are used.
	"""
	frappe.has_permission("Item", "read", doc=item_code, throw=True)

	from mu_customers.default_warehouse_qty import compute, qty_in_warehouses, resolve_company

	if warehouses:
		if isinstance(warehouses, str):
			warehouses = frappe.parse_json(warehouses)
		warehouses = [w for w in (warehouses or []) if w]
		return {
			"qty": qty_in_warehouses(item_code, warehouses),
			"warehouses": warehouses,
			"company": resolve_company(company),
		}

	return compute(item_code, company)


@frappe.whitelist()
def get_customer_branches(customer):
	"""Branch names configured on one customer, for the Branch field filter.

	Deliberately a server endpoint rather than a client-side child-table query:
	frappe.db.get_list posts to frappe.desk.reportview.get_list, which forwards
	every argument straight into DatabaseQuery.execute(), so the `parent`
	argument that frappe.client.get_list accepts is a TypeError there. Reading
	the rows here keeps the permission check explicit and the behaviour
	testable.
	"""
	if not customer:
		return []

	frappe.has_permission("Customer", "read", doc=customer, throw=True)

	return frappe.get_all(
		"Customer Branches",
		filters={
			"parenttype": "Customer",
			"parentfield": "custom_branches",
			"parent": customer,
		},
		pluck="branch",
		order_by="idx asc",
	)


@frappe.whitelist()
def get_next_item_code():
	"""Next free numeric item code, matching the autoname hook exactly."""
	from mu_customers.events.item import _next_numeric_code

	frappe.has_permission("Item", "create", throw=True)

	candidate = _next_numeric_code()
	while frappe.db.exists("Item", str(candidate)):
		candidate += 1
	return str(candidate)
