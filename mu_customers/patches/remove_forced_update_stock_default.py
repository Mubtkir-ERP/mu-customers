import frappe

# Forcing update_stock = 1 on every sales and purchase invoice makes each
# invoice post stock and inventory entries, which blocks plain service
# invoicing. Whether to update stock belongs to the business, not the app.


def execute():
	for doctype in ("Sales Invoice", "Purchase Invoice"):
		name = f"{doctype}-update_stock-default"
		if frappe.db.exists("Property Setter", name):
			frappe.delete_doc("Property Setter", name, ignore_permissions=True, force=True)
		frappe.clear_cache(doctype=doctype)
