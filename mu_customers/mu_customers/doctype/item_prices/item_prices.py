# Copyright (c) 2025, Mubtkir and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

PRICE_TYPES = ("Selling", "Buying")


class ItemPrices(Document):
	pass


@frappe.whitelist()
def get_item_prices(item_code, invoice_type):
	"""Prices configured on an item, for the price-picker dialog.

	Reachable over HTTP, so it enforces read permission on the item itself and
	returns only the columns the dialog needs.
	"""
	if invoice_type not in PRICE_TYPES:
		frappe.throw(_("Invalid price type: {0}").format(invoice_type))

	frappe.has_permission("Item", "read", doc=item_code, throw=True)

	if not frappe.db.get_value("Item", item_code, "custom_prices_enabled"):
		return {"prices": [], "enabled": False}

	prices = frappe.get_all(
		"Item Prices",
		filters={"parent": item_code, "parenttype": "Item", "type": invoice_type},
		fields=["name", "price_type", "uom", "price"],
		order_by="idx asc",
	)

	return {"prices": prices, "enabled": True}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def price_type_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query behind the Price Type dropdown on transaction rows.

	Each row offers only the types that its own item actually has for that
	direction, so the filtering is per row rather than per form.
	"""
	filters = filters or {}
	item_code = filters.get("item_code")
	invoice_type = filters.get("invoice_type")

	if not item_code or invoice_type not in PRICE_TYPES:
		return []

	frappe.has_permission("Item", "read", doc=item_code, throw=True)

	return frappe.db.sql(
		"""
		SELECT DISTINCT price_type
		FROM `tabItem Prices`
		WHERE parenttype = 'Item'
			AND parent = %(item_code)s
			AND type = %(invoice_type)s
			AND IFNULL(price_type, '') != ''
			AND price_type LIKE %(txt)s
		ORDER BY price_type ASC
		LIMIT %(start)s, %(page_len)s
		""",
		{
			"item_code": item_code,
			"invoice_type": invoice_type,
			"txt": f"%{txt or ''}%",
			"start": start,
			"page_len": page_len,
		},
	)


@frappe.whitelist()
def get_price_for_type(item_code, invoice_type, price_type, uom=None):
	"""The configured price for one type, preferring a row in the current UOM.

	Returns None when the item has no such price, so the caller can leave the
	rate exactly as ERPNext calculated it.
	"""
	if invoice_type not in PRICE_TYPES:
		frappe.throw(_("Invalid price type: {0}").format(invoice_type))

	frappe.has_permission("Item", "read", doc=item_code, throw=True)

	if not frappe.db.get_value("Item", item_code, "custom_prices_enabled"):
		return None

	rows = frappe.get_all(
		"Item Prices",
		filters={
			"parent": item_code,
			"parenttype": "Item",
			"type": invoice_type,
			"price_type": price_type,
		},
		fields=["price_type", "uom", "price"],
		order_by="idx asc",
	)

	if not rows:
		return None

	if uom:
		for row in rows:
			if row.uom == uom:
				return row

	return rows[0]


@frappe.whitelist()
def get_price_options(item_codes, invoice_type):
	"""How many price choices each item offers, and the single one if there is
	only one.

	Drives whether the Price Type dropdown appears on a row at all: a row whose
	item has one price or none has nothing to choose between, so the field is
	hidden and the single price applied on its own. Takes a list so reopening a
	saved document costs one round trip rather than one per line.
	"""
	if invoice_type not in PRICE_TYPES:
		frappe.throw(_("Invalid price type: {0}").format(invoice_type))

	if isinstance(item_codes, str):
		item_codes = frappe.parse_json(item_codes)

	item_codes = [code for code in dict.fromkeys(item_codes or []) if code]
	if not item_codes:
		return {}

	frappe.has_permission("Item", "read", throw=True)

	rows = frappe.get_all(
		"Item Prices",
		filters={"parent": ["in", item_codes], "parenttype": "Item", "type": invoice_type},
		fields=["parent", "price_type", "uom", "price"],
		order_by="parent asc, idx asc",
	)

	enabled = set(
		frappe.get_all(
			"Item",
			filters={"name": ["in", item_codes], "custom_prices_enabled": 1},
			pluck="name",
		)
	)

	options = {code: {"count": 0, "only": None} for code in item_codes}
	for row in rows:
		if row.parent not in enabled:
			continue
		entry = options[row.parent]
		entry["count"] += 1
		entry["only"] = row if entry["count"] == 1 else None

	return options
