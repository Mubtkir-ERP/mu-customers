import frappe

# custom_note duplicated ERPNext's own remarks field. Where a standard remarks
# field exists, move the historical values across and retire the custom one so
# nothing is stranded in a field the rest of the system ignores.
#
# Sales Order, Purchase Order and Quotation have no standard remarks field in
# ERPNext v15, so custom_note stays in place for those.
CANDIDATES = ["Sales Invoice", "Purchase Invoice", "Sales Order", "Purchase Order", "Quotation"]


def execute():
	for doctype in CANDIDATES:
		if not frappe.db.table_exists(doctype):
			continue
		if not frappe.db.has_column(doctype, "custom_note"):
			continue
		if not frappe.db.has_column(doctype, "remarks"):
			# No standard target - leave the custom field alone.
			continue

		moved = frappe.db.sql(
			f"""
			UPDATE `tab{doctype}`
			SET remarks = custom_note
			WHERE custom_note IS NOT NULL
			  AND custom_note != ''
			  AND (remarks IS NULL OR remarks = '')
			"""
		)

		leftover = frappe.db.sql(
			f"""
			SELECT COUNT(*) FROM `tab{doctype}`
			WHERE custom_note IS NOT NULL AND custom_note != ''
			  AND remarks IS NOT NULL AND remarks != ''
			  AND remarks != custom_note
			"""
		)[0][0]

		if leftover:
			# Both fields carry different text - keep the custom field so no
			# note is destroyed, and let a human reconcile them.
			frappe.log_error(
				title="mu_customers: custom_note not retired",
				message=(
					f"{doctype}: {leftover} document(s) have both remarks and a different "
					"custom_note. The custom field was kept so nothing is lost."
				),
			)
			continue

		name = f"{doctype}-custom_note"
		if frappe.db.exists("Custom Field", name):
			frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)

		frappe.clear_cache(doctype=doctype)
