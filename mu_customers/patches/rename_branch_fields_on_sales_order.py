import frappe


def execute():
	if frappe.db.exists("Custom Field", {"name": "Sales Order-custom_branch"}):
		frappe.db.sql("""
			UPDATE `tabCustom Field`
			SET `name` = 'Sales Order-branch'
			WHERE `name` = 'Sales Order-custom_branch';
		""")
	if frappe.db.exists("Custom Field", {"name": "Sales Order-custom_has_branches"}):
		frappe.db.sql("""
			UPDATE `tabCustom Field`
			SET `name` = 'Sales Order-has_branches'
			WHERE `name` = 'Sales Order-custom_has_branches';
		""")
