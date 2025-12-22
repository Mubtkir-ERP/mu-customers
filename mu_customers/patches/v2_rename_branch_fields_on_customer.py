import frappe


def execute():
	if frappe.db.exists("Custom Field", {"name": "Customer-branches"}):
		frappe.db.sql("""
			UPDATE `tabCustom Field`
			SET `name` = "Customer-custom_branches"
			WHERE `name` = "Customer-branches";
		""")
	if frappe.db.exists("Custom Field", {"name": "Customer-has_branches"}):
		frappe.db.sql("""
			UPDATE `tabCustom Field`
			SET `name` = "Customer-custom_has_branches"
			WHERE `name` = "Customer-has_branches";
		""")
