import frappe

# field_order property setters pin the complete field list of a core doctype to
# whatever it looked like when the fixtures were exported. After an ERPNext
# upgrade the frozen list keeps winning and every newly shipped field silently
# disappears from the form.


def execute():
	stale = frappe.get_all(
		"Property Setter",
		filters={"property": "field_order", "module": "Mu Customers"},
		pluck="name",
	)

	for name in stale:
		frappe.delete_doc("Property Setter", name, ignore_permissions=True, force=True)

	frappe.clear_cache()
