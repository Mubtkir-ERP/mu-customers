import frappe


def before_install():
	"""Nothing destructive runs here any more.

	The previous version deleted seven Property Setters the app does not own,
	including Purchase Invoice-bill_no-unique - the control that stops the same
	supplier invoice being entered and paid twice. Layout preferences now ship
	as fixtures instead of being enforced by deletion.
	"""
	pass


def after_install():
	enable_supplier_invoice_uniqueness()
	ensure_update_stock_defaults()


def enable_supplier_invoice_uniqueness():
	"""Turn on ERPNext's standard duplicate supplier-invoice guard.

	This is the framework's own control (Accounts Settings ->
	check_supplier_invoice_uniqueness): it blocks the same bill_no for the same
	supplier within a fiscal year, without the cross-supplier false positives a
	blanket unique index on bill_no would cause.
	"""
	if not frappe.db.exists("DocType", "Accounts Settings"):
		return

	if not frappe.db.get_single_value("Accounts Settings", "check_supplier_invoice_uniqueness"):
		frappe.db.set_single_value("Accounts Settings", "check_supplier_invoice_uniqueness", 1)


UPDATE_STOCK_DOCTYPES = ("Sales Invoice", "Purchase Invoice")


def ensure_update_stock_defaults():
	"""Set Update Stock to 1 only when the site has no preference yet.

	The Property Setter is deliberately *not* shipped as a fixture. That makes
	the default a site-level choice: administrators can change it to 0 or back
	to 1 from Customize Form and future app updates will not overwrite it.
	"""
	created = []

	for doctype in UPDATE_STOCK_DOCTYPES:
		name = f"{doctype}-update_stock-default"

		# Existing means the site has already chosen its default (0 or 1).
		if frappe.db.exists("Property Setter", name):
			continue

		frappe.make_property_setter(
			{
				"doctype": doctype,
				"doctype_or_field": "DocField",
				"fieldname": "update_stock",
				"property": "default",
				"value": "1",
				"property_type": "Check",
			},
			is_system_generated=False,
		)
		frappe.db.set_value("Property Setter", name, "module", "Mu Customers")
		frappe.clear_cache(doctype=doctype)
		created.append(doctype)

	return created

