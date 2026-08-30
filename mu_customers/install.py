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
