import frappe


def execute():
	if frappe.db.exists("Custom Field", {"name": "Customer-branches"}):
		frappe.db.sql("""
			UPDATE `tabCustom Field`
			SET `name` = 'Customer-branches'
			WHERE `name` = 'Customer-custom_branches';
		""")
	if frappe.db.exists("Custom Field", {"name": "Customer-has_branches"}):
		frappe.db.sql("""
			UPDATE `tabCustom Field`
			SET `name` = 'Customer-has_branches'
			WHERE `name` = 'Customer-custom_has_branches';
		""")
