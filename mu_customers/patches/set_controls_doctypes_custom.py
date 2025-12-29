import frappe


def execute():
	controls_module = "Controls"

	controls_doctypes = frappe.get_all(
		"DocType", filters={"module": controls_module, "custom": 0}, fields=["name"]
	)

	for dt in controls_doctypes:
		frappe.db.set_value("DocType", dt.name, "custom", 1)
