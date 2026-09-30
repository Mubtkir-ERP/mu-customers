import frappe

# `custom_note` was used historically on Sales Invoice and Purchase Invoice.
# ERPNext already has the standard `remarks` field, so `custom_note` is now the
# authoritative source during migration: whenever it contains a value, that
# value replaces the current Remarks value, even when Remarks already contains
# different text.
#
# IMPORTANT: the legacy custom_note value itself is NOT deleted. The field is
# hidden from Desk by v17_hide_invoice_custom_note_preserve_data, but its stored
# value stays available as a historical backup.
CANDIDATES = ("Sales Invoice", "Purchase Invoice")


def overwrite_remarks_from_custom_note(doctype):
	"""Make non-empty custom_note the authoritative Remarks value.

	Returns the number of rows whose Remarks value needed to be replaced.
	Empty custom_note values are ignored so an existing Remarks value is never
	blanked merely because the legacy field has no content.
	"""
	if not frappe.db.table_exists(doctype):
		return 0
	if not frappe.db.has_column(doctype, "custom_note"):
		return 0
	if not frappe.db.has_column(doctype, "remarks"):
		return 0

	changed = frappe.db.sql(
		f"""
		SELECT COUNT(*)
		FROM `tab{doctype}`
		WHERE custom_note IS NOT NULL
		  AND custom_note != ''
		  AND (remarks IS NULL OR remarks != custom_note)
		"""
	)[0][0]

	frappe.db.sql(
		f"""
		UPDATE `tab{doctype}`
		SET remarks = custom_note
		WHERE custom_note IS NOT NULL
		  AND custom_note != ''
		"""
	)

	return changed


def execute():
	for doctype in CANDIDATES:
		overwrite_remarks_from_custom_note(doctype)
