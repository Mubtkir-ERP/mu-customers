# Copyright (c) 2025, Mubtkir and contributors
# For license information, please see license.txt

"""Total stock across an item's default warehouses.

One place decides which warehouses count, so the background sync, the Item
validate hook and the desk form all agree on the number they show.
"""

import frappe
from frappe.utils import flt


def resolve_company(company=None):
	"""The company whose Item Defaults row we should read."""
	if company:
		return company

	company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default(
		"company"
	)
	if company:
		return company

	companies = frappe.get_all("Company", pluck="name", limit=2)
	return companies[0] if len(companies) == 1 else None


def pick_warehouses(rows, company=None):
	"""Default warehouses from Item Defaults rows, preferring one company.

	`rows` is any iterable of objects carrying `company` and `default_warehouse`
	- child rows off a loaded Item, or dicts from a query.

	Scoped to the resolved company; if that company has no default warehouse for
	this item we fall back to every configured default rather than reporting a
	misleading zero.
	"""
	company = resolve_company(company)

	def warehouse_of(row):
		return row.get("default_warehouse") if isinstance(row, dict) else row.default_warehouse

	def company_of(row):
		return row.get("company") if isinstance(row, dict) else row.company

	rows = list(rows or [])
	scoped = [warehouse_of(r) for r in rows if warehouse_of(r) and (not company or company_of(r) == company)]
	if scoped:
		return scoped

	return [warehouse_of(r) for r in rows if warehouse_of(r)]


def qty_in_warehouses(item_code, warehouses):
	if not warehouses:
		return 0.0

	total = frappe.db.get_value(
		"Bin",
		{"item_code": item_code, "warehouse": ["in", warehouses]},
		"sum(actual_qty)",
	)
	return flt(total)


def compute(item_code, company=None):
	"""Look the item's defaults up from the database and total them."""
	rows = frappe.get_all(
		"Item Default",
		filters={"parent": item_code, "parenttype": "Item"},
		fields=["company", "default_warehouse"],
	)
	warehouses = pick_warehouses(rows, company)

	return {
		"qty": qty_in_warehouses(item_code, warehouses),
		"warehouses": warehouses,
		"company": resolve_company(company),
	}


def compute_from_doc(doc, company=None):
	"""Total using the item's in-memory child rows.

	Used from validate, where the Item Default rows on disk are still the old
	ones - reading them back would compute the quantity for the warehouse the
	user just replaced.
	"""
	warehouses = pick_warehouses(doc.get("item_defaults") or [], company)
	return qty_in_warehouses(doc.name, warehouses)
