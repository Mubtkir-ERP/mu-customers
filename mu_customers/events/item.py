# Copyright (c) 2025, Mubtkir and contributors
# For license information, please see license.txt

import frappe


def clear_auto_description(doc, method=None):
	"""Drop the description ERPNext auto-fills from the item name.

	Only clears descriptions the system generated: on an existing item, text the
	user just typed is left alone even when it happens to match the item name.
	The old version wiped it unconditionally and silently.
	"""
	if not doc.description:
		return

	if not doc.is_new():
		previous = doc.get_doc_before_save()
		if previous and (previous.description or "") != doc.description:
			# Edited in this save - keep what the user wrote.
			return

	desc = doc.description.strip()
	if desc == (doc.item_name or "").strip() or desc == (doc.item_code or "").strip():
		doc.description = ""


def sync_default_warehouse_qty(doc, method=None):
	"""Keep Default Warehouse Qty in step with the item's own defaults.

	The stock ledger hook only fires on stock movement, so an item whose default
	warehouse was changed - or one that already had stock before this app was
	installed - kept showing a stale zero until something moved. Recomputing on
	save closes that gap; the value is read from the child rows being saved, not
	from the ones still on disk.
	"""
	if doc.is_new():
		return

	from mu_customers.default_warehouse_qty import compute_from_doc

	doc.custom_default_warehouse_qty = compute_from_doc(doc)


def default_item_code_from_name(doc, method=None):
	"""Fall back to the item name when no code was typed.

	ERPNext's own autoname copies item_code into name, so an item saved without
	a code fails validation with "Item Code is required". That makes the code
	field effectively mandatory even with reqd = 0, which is what stopped the
	quick entry dialog from saving in one click.

	Runs on before_insert, which is before set_new_name, so ERPNext still does
	the naming itself. Skipped when the numeric series is on - that path assigns
	the code in custom_autoname below.
	"""
	if doc.item_code:
		return

	if frappe.db.get_single_value("Extra Features Settings", "enable_item_numeric_autoname"):
		return

	name = (doc.item_name or "").strip()
	if name:
		doc.item_code = name


def _next_numeric_code():
	"""Highest purely numeric Item name in use, plus one.

	MAX() over the numeric names, rather than the old "read the most recently
	created item and give up if its name is not a number" approach - which
	restarted the series at 1 as soon as anyone added a coded item.
	"""
	row = frappe.db.sql(
		"""
		select max(cast(`name` as unsigned))
		from `tabItem`
		where `name` regexp '^[0-9]+$'
		"""
	)
	last = int(row[0][0]) if row and row[0][0] else 0
	return last + 1


def custom_autoname(doc, method=None):
	if not frappe.db.get_single_value("Extra Features Settings", "enable_item_numeric_autoname"):
		return

	if doc.item_code:
		code = str(doc.item_code).strip()
		if not code.isdigit():
			# A deliberate alphanumeric code wins over the numeric series.
			# int() on this used to raise ValueError and block the save.
			return
		candidate = int(code)
	else:
		candidate = _next_numeric_code()

	name = str(candidate)
	while frappe.db.exists("Item", name):
		candidate += 1
		name = str(candidate)

	doc.item_code = name
	doc.name = name
