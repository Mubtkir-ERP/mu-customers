"""Stop shipping the VAT field, and drop the form tweaks the client reversed.

The ZATCA app owns `custom_vat_registration_number`; this app defining it too
produced two owners for one column and a fixture that would fight the ZATCA
app on every migrate. The definition goes, but the column and everything typed
into it stay - deleting a Custom Field in Frappe leaves the column alone, and
the data belongs to whichever app manages the field next.

Also removes three Property Setters the client asked to revert, so those
fields fall back to whatever ERPNext ships.
"""

import frappe

VAT_FIELD = "Customer-custom_vat_registration_number"
DEPENDENT = "Customer-custom_commercial_register_no"

RETIRED_SETTERS = (
	# Reverted: the reference number goes back to ERPNext's own configuration.
	"Payment Entry-reference_no-reqd",
	# Reverted: both sections are collapsible again.
	"Sales Invoice-more_information-collapsible",
	"Purchase Invoice-additional_info_section-collapsible",
	f"{VAT_FIELD}-allow_in_quick_entry",
)


def execute():
	repoint_commercial_register()
	dropped_field = release_vat_field()
	dropped = drop_retired_setters()

	if dropped_field or dropped:
		frappe.clear_cache()

	print(
		f"mu_customers: released the VAT field ({dropped_field}), "
		f"removed {dropped} reverted property setter(s)"
	)


def repoint_commercial_register():
	"""It sat under the VAT box; anchor it to Tax ID before that box goes.

	A Custom Field whose insert_after names a field that no longer exists is
	pushed to the bottom of the form, which is how the layout drifted last time.
	"""
	if not frappe.db.exists("Custom Field", DEPENDENT):
		return

	if frappe.db.get_value("Custom Field", DEPENDENT, "insert_after") != "tax_id":
		frappe.db.set_value("Custom Field", DEPENDENT, "insert_after", "tax_id")


def release_vat_field():
	"""Remove our definition only - never the column or its contents.

	Guarded on module so that once the ZATCA app owns the field, re-running this
	cannot delete a definition belonging to that app.
	"""
	if not frappe.db.exists("Custom Field", VAT_FIELD):
		return False

	if frappe.db.get_value("Custom Field", VAT_FIELD, "module") != "Mu Customers":
		print("mu_customers: VAT field is owned by another app now, left untouched")
		return False

	frappe.delete_doc("Custom Field", VAT_FIELD, ignore_permissions=True, force=True)
	return True


def drop_retired_setters():
	dropped = 0
	for name in RETIRED_SETTERS:
		if frappe.db.exists("Property Setter", name):
			frappe.delete_doc("Property Setter", name, ignore_permissions=True, force=True)
			dropped += 1
	return dropped
