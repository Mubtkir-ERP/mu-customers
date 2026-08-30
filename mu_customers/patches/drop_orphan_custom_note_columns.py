import frappe

# migrate_custom_note_to_remarks moved the values into the standard remarks
# field and deleted the Custom Field, but deleting a Custom Field leaves its
# column behind. Drop the orphans - only where every note really did make it
# across, so nothing is destroyed on a site where the migration was skipped.
DOCTYPES = ["Sales Invoice", "Purchase Invoice"]
FIELD = "custom_note"


def execute():
	kept = []

	for doctype in DOCTYPES:
		if not frappe.db.table_exists(doctype):
			continue
		if not frappe.db.has_column(doctype, FIELD):
			continue

		# Still a live field somewhere (migration did not run) - leave it alone.
		if frappe.db.exists("Custom Field", f"{doctype}-{FIELD}"):
			kept.append(f"{doctype}: custom field still defined")
			continue

		if not frappe.db.has_column(doctype, "remarks"):
			kept.append(f"{doctype}: no remarks column to compare against")
			continue

		stranded = frappe.db.sql(
			f"""
			select count(*) from `tab{doctype}`
			where `{FIELD}` is not null and `{FIELD}` != ''
			  and (remarks is null or remarks = '' or remarks not like concat('%%', `{FIELD}`, '%%'))
			"""
		)[0][0]

		if stranded:
			kept.append(f"{doctype}: {stranded} note(s) not found in remarks")
			continue

		frappe.db.commit()  # DDL implicitly commits; close the open transaction first
		frappe.db.sql_ddl(f"ALTER TABLE `tab{doctype}` DROP COLUMN `{FIELD}`")
		frappe.clear_cache(doctype=doctype)

	if kept:
		frappe.log_error(
			title="mu_customers: custom_note columns kept",
			message="Not dropped: " + "; ".join(kept),
		)
