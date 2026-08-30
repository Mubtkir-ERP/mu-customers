"""Fill in the price-option count on rows written before it existed.

`custom_price_options` drives whether the Price Type dropdown shows on a row.
Rows saved before the field was added read back as 0 - an Int column's default,
indistinguishable from "this item has no prices" - so the dropdown stayed
hidden on documents whose items did have several prices.

The form recounts on open, but storing the right number means a document is
correct the moment it renders rather than a round trip later.
"""

import frappe

DIRECTIONS = {
	"Sales Invoice Item": "Selling",
	"Sales Order Item": "Selling",
	"Delivery Note Item": "Selling",
	"Quotation Item": "Selling",
	"Purchase Invoice Item": "Buying",
	"Purchase Order Item": "Buying",
	"Purchase Receipt Item": "Buying",
}


def execute():
	counts = price_counts_by_item()
	if not counts:
		print("mu_customers: no priced items, nothing to backfill")
		return

	total = 0
	for doctype, direction in DIRECTIONS.items():
		total += backfill(doctype, direction, counts.get(direction, {}))

	print(f"mu_customers: set the price-option count on {total} row(s)")


def price_counts_by_item():
	"""How many prices each item has, per direction."""
	rows = frappe.db.sql(
		"""
		SELECT p.type, p.parent AS item_code, COUNT(*) AS count
		FROM `tabItem Prices` p
		INNER JOIN `tabItem` i ON i.name = p.parent
		WHERE p.parenttype = 'Item' AND i.custom_prices_enabled = 1
		GROUP BY p.type, p.parent
		""",
		as_dict=True,
	)

	counts = {}
	for row in rows:
		counts.setdefault(row.type, {})[row.item_code] = row.count
	return counts


def backfill(doctype, direction, item_counts):
	if not item_counts or not frappe.db.table_exists(doctype):
		return 0
	if not frappe.db.has_column(doctype, "custom_price_options"):
		return 0

	updated = 0
	for item_code, count in item_counts.items():
		stale = frappe.db.sql(
			f"""
			SELECT COUNT(*) FROM `tab{doctype}`
			WHERE `item_code` = %(item_code)s
			  AND IFNULL(`custom_price_options`, 0) != %(count)s
			""",
			{"count": count, "item_code": item_code},
		)[0][0]

		if not stale:
			continue

		frappe.db.sql(
			f"""
			UPDATE `tab{doctype}`
			SET `custom_price_options` = %(count)s
			WHERE `item_code` = %(item_code)s
			  AND IFNULL(`custom_price_options`, 0) != %(count)s
			""",
			{"count": count, "item_code": item_code},
		)
		updated += stale

	return updated
