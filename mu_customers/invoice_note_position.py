"""Put the invoice note back directly under the tax number.

Version 0.2.2 carried a `custom_note` Data field on Sales Invoice and Purchase
Invoice, sitting immediately after the tax number, and that is where staff read
and wrote it. The note was later migrated into ERPNext's standard `remarks`
field and `custom_note` was dropped - which kept the data but moved the box to
the very end of the form, inside Additional Info.

`remarks` is a standard field, so `insert_after` cannot move it; only a
DocType-level `field_order` can. That order is computed here from the live meta
rather than shipped as a fixture, so it matches whatever ERPNext version the
site runs instead of pinning someone else's snapshot.

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


def order_with_note_after_anchor(doctype, anchor):
	"""The doctype's current field order with `remarks` moved after `anchor`."""
	order = [df.fieldname for df in frappe.get_meta(doctype).fields]

	if FIELD not in order or anchor not in order:
		return None

	order.remove(FIELD)
	order.insert(order.index(anchor) + 1, FIELD)
	return order


def apply(doctype=None):
	"""Write the field_order property setter for one or both invoices."""
	moved = []

	for dt, anchor in NOTE_ANCHOR.items():
		if doctype and dt != doctype:
			continue

		order = order_with_note_after_anchor(dt, anchor)
		if not order:
			continue

		frappe.make_property_setter(
			{
				"doctype": dt,
				"doctype_or_field": "DocType",
				"property": "field_order",
				"value": json.dumps(order),
				"property_type": "Text",
			},
			is_system_generated=False,
		)
		frappe.db.set_value("Property Setter", f"{dt}-main-field_order", "module", "Mu Customers")
		moved.append(dt)

	if moved:
		frappe.clear_cache()

	return moved
