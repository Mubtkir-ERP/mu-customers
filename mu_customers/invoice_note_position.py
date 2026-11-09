"""Put the invoice note back directly under the tax number and manage layout ordering.

Version 0.2.2 carried a `custom_note` Data field on Sales Invoice and Purchase
Invoice, sitting immediately after the tax number, and that is where staff read
and wrote it. The note was later migrated into ERPNext's standard `remarks`
field. The legacy `custom_note` field is now hidden rather than deleted so its
historical values remain recoverable, while staff use `remarks` on the form.

`remarks`, `payments`, `paid_amount`, and `taxes_and_charges` are standard fields,
so `insert_after` cannot move them; only a DocType-level `field_order` can.
That order is computed here from the live meta rather than shipped as a fixture,
so it matches whatever ERPNext version the site runs instead of pinning someone else's snapshot.

Frappe reinserts anything missing from a stored `field_order`
(Meta.sort_fields: unknown names are filtered out, and fields absent from the
list are placed after their preceding field), so this stays correct across
ERPNext upgrades.
"""

import json

import frappe

# Where 0.2.2 put the note on each invoice.
NOTE_ANCHOR = {
	"Sales Invoice": "company_tax_id",
	"Purchase Invoice": "company",
}

FIELD = "remarks"

ALL_TARGET_DOCTYPES = (
	"Sales Invoice",
	"Purchase Invoice",
	"Sales Order",
	"Purchase Order",
	"Quotation",
	"Supplier Quotation",
	"Delivery Note",
	"Purchase Receipt",
)


def reorder_fields(order, doctype, anchor=None):
	"""Apply layout reordering rules to a list of fieldnames."""
	if not order:
		return order

	# 1. Remarks under tax anchor
	if anchor is None:
		anchor = NOTE_ANCHOR.get(doctype)
	if anchor and FIELD in order and anchor in order:
		order.remove(FIELD)
		order.insert(order.index(anchor) + 1, FIELD)

	# 2. Taxes and Charges template above base_total (in column_break_32 under section_break_30)
	if "taxes_and_charges" in order and "base_total" in order:
		order.remove("taxes_and_charges")
		order.insert(order.index("base_total"), "taxes_and_charges")

	# 3. Payments table full width under section_break_42 (Sales Invoice and Purchase Invoice)
	if doctype in ("Sales Invoice", "Purchase Invoice"):
		if "payments" in order and "section_break_42" in order:
			order.remove("payments")
			order.insert(order.index("section_break_42") + 1, "payments")

		# 4. Paid Amount under grand_total
		if "paid_amount" in order and "grand_total" in order:
			order.remove("paid_amount")
			order.insert(order.index("grand_total") + 1, "paid_amount")

	return order


def order_with_note_after_anchor(doctype, anchor):
	"""The doctype's current field order with all custom order rules applied."""
	order = [df.fieldname for df in frappe.get_meta(doctype).fields]

	if FIELD not in order or anchor not in order:
		return None

	return reorder_fields(order, doctype, anchor)


def hide_custom_notes():
	"""Ensure legacy custom_note fields are hidden, except on Quotation where it stays visible."""
	frappe.db.sql(
		"""UPDATE `tabCustom Field` SET `hidden` = 1 WHERE `fieldname` = 'custom_note' AND `dt` != 'Quotation' AND `hidden` = 0"""
	)
	frappe.db.sql(
		"""UPDATE `tabCustom Field` SET `hidden` = 0 WHERE `fieldname` = 'custom_note' AND `dt` = 'Quotation' AND `hidden` = 1"""
	)


def apply(doctype=None):
	"""Write the field_order property setter for target doctypes and hide custom_notes."""
	hide_custom_notes()
	moved = []

	targets = [doctype] if doctype else ALL_TARGET_DOCTYPES

	for dt in targets:
		if not frappe.db.exists("DocType", dt):
			continue

		original_order = [df.fieldname for df in frappe.get_meta(dt).fields]
		if not original_order:
			continue

		new_order = reorder_fields(list(original_order), dt)
		if new_order == original_order:
			continue

		frappe.make_property_setter(
			{
				"doctype": dt,
				"doctype_or_field": "DocType",
				"property": "field_order",
				"value": json.dumps(new_order),
				"property_type": "Text",
			},
			is_system_generated=False,
		)
		frappe.db.set_value("Property Setter", f"{dt}-main-field_order", "module", "Mu Customers")
		moved.append(dt)

	if moved:
		frappe.clear_cache()

	return moved
