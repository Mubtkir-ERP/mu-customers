"""Hide legacy invoice custom_note fields without deleting their data."""

import frappe

DOCTYPES = ("Sales Invoice", "Purchase Invoice")
FIELD = "custom_note"


def execute():
	for doctype in DOCTYPES:
		custom_field_name = f"{doctype}-{FIELD}"

		# If the legacy Custom Field still exists, hide it from Desk only.
		# We deliberately do not delete the Custom Field and never touch the
		# underlying column/value, so old invoice notes remain stored.
		if frappe.db.exists("Custom Field", custom_field_name):
			frappe.db.set_value(
				"Custom Field",
				custom_field_name,
				"hidden",
				1,
				update_modified=False,
			)
			frappe.clear_cache(doctype=doctype)
