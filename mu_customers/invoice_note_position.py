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

# Where the note sits on each invoice/transaction.
NOTE_ANCHOR = {
	"Sales Invoice": "tax_id",
	"Purchase Invoice": "company",
	"Sales Order": "tax_id",
	"Delivery Note": "tax_id",
	"Quotation": "tax_id",
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

	# 3. Payments table full width under items table across all documents
	if "payments" in order and "items" in order:
		order.remove("payments")
		order.insert(order.index("items") + 1, "payments")

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


def setup_sales_customizations():
	"""Configure tax_id fetch_from and company_tax_id hidden on selling documents only."""
	selling_doctypes = ("Sales Invoice", "Sales Order", "Delivery Note", "Quotation")
	for dt in selling_doctypes:
		if not frappe.db.exists("DocType", dt):
			continue

		meta = frappe.get_meta(dt)

		# 1. tax_id fetch_from customer.custom_vat_registration_number
		if meta.has_field("tax_id"):
			ps_name = f"{dt}-tax_id-fetch_from"
			if not frappe.db.exists("Property Setter", ps_name):
				frappe.make_property_setter(
					{
						"doctype": dt,
						"doctype_or_field": "DocField",
						"fieldname": "tax_id",
						"property": "fetch_from",
						"value": "customer.custom_vat_registration_number",
						"property_type": "Small Text",
					},
					is_system_generated=False,
				)
				frappe.db.set_value("Property Setter", ps_name, "module", "Mu Customers")
			else:
				frappe.db.set_value(
					"Property Setter",
					ps_name,
					{"value": "customer.custom_vat_registration_number", "module": "Mu Customers"},
				)

		# 2. company_tax_id hidden = 1
		if meta.has_field("company_tax_id"):
			ps_name = f"{dt}-company_tax_id-hidden"
			if not frappe.db.exists("Property Setter", ps_name):
				frappe.make_property_setter(
					{
						"doctype": dt,
						"doctype_or_field": "DocField",
						"fieldname": "company_tax_id",
						"property": "hidden",
						"value": "1",
						"property_type": "Check",
					},
					is_system_generated=False,
				)
				frappe.db.set_value("Property Setter", ps_name, "module", "Mu Customers")
			else:
				frappe.db.set_value(
					"Property Setter",
					ps_name,
					{"value": "1", "module": "Mu Customers"},
				)


def reorder_customer_fields():
	"""Place custom_vat_registration_number under customer_group, and custom_commercial_register_no under custom_vat_registration_number."""
	if not frappe.db.exists("DocType", "Customer"):
		return

	# Update insert_after on Custom Fields if they exist
	if frappe.db.exists("Custom Field", "Customer-custom_vat_registration_number"):
		frappe.db.set_value("Custom Field", "Customer-custom_vat_registration_number", "insert_after", "customer_group")

	if frappe.db.exists("Custom Field", "Customer-custom_commercial_register_no"):
		frappe.db.set_value("Custom Field", "Customer-custom_commercial_register_no", "insert_after", "custom_vat_registration_number")

	meta = frappe.get_meta("Customer")
	order = [df.fieldname for df in meta.fields]
	if not order or "customer_group" not in order:
		return

	changed = False
	if "custom_vat_registration_number" in order:
		order.remove("custom_vat_registration_number")
		order.insert(order.index("customer_group") + 1, "custom_vat_registration_number")
		changed = True

	if "custom_commercial_register_no" in order:
		order.remove("custom_commercial_register_no")
		anchor = "custom_vat_registration_number" if "custom_vat_registration_number" in order else "customer_group"
		order.insert(order.index(anchor) + 1, "custom_commercial_register_no")
		changed = True

	if changed:
		frappe.make_property_setter(
			{
				"doctype": "Customer",
				"doctype_or_field": "DocType",
				"property": "field_order",
				"value": json.dumps(order),
				"property_type": "Text",
			},
			is_system_generated=False,
		)
		frappe.db.set_value("Property Setter", "Customer-main-field_order", "module", "Mu Customers")


def setup_customer_collapsible_sections():
	"""Make Defaults and Customer IDs sections collapsible in Customer doctype."""
	if not frappe.db.exists("DocType", "Customer"):
		return

	meta = frappe.get_meta("Customer")

	# 1. Defaults section (defaults_tab)
	if meta.has_field("defaults_tab") or frappe.db.exists("Custom Field", "Customer-defaults_tab"):
		ps_name = "Customer-defaults_tab-collapsible"
		if not frappe.db.exists("Property Setter", ps_name):
			frappe.make_property_setter(
				{
					"doctype": "Customer",
					"doctype_or_field": "DocField",
					"fieldname": "defaults_tab",
					"property": "collapsible",
					"value": "1",
					"property_type": "Check",
				},
				is_system_generated=False,
			)
			frappe.db.set_value("Property Setter", ps_name, "module", "Mu Customers")
		else:
			frappe.db.set_value("Property Setter", ps_name, "value", "1")

	# 2. Customer IDs section (custom_section_break_nxdgf or matching label)
	target_sec = "custom_section_break_nxdgf"
	if not (meta.has_field(target_sec) or frappe.db.exists("Custom Field", f"Customer-{target_sec}")):
		for df in meta.fields:
			if df.fieldtype == "Section Break" and (df.label or "").strip().lower() in ("customer ids", "customer id"):
				target_sec = df.fieldname
				break

	if meta.has_field(target_sec) or frappe.db.exists("Custom Field", f"Customer-{target_sec}"):
		ps_name = f"Customer-{target_sec}-collapsible"
		if not frappe.db.exists("Property Setter", ps_name):
			frappe.make_property_setter(
				{
					"doctype": "Customer",
					"doctype_or_field": "DocField",
					"fieldname": target_sec,
					"property": "collapsible",
					"value": "1",
					"property_type": "Check",
				},
				is_system_generated=False,
			)
			frappe.db.set_value("Property Setter", ps_name, "module", "Mu Customers")
		else:
			frappe.db.set_value("Property Setter", ps_name, "value", "1")


def apply(doctype=None):
	"""Write the field_order property setter for target doctypes and hide custom_notes."""
	hide_custom_notes()
	setup_sales_customizations()
	reorder_customer_fields()
	setup_customer_collapsible_sections()
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
