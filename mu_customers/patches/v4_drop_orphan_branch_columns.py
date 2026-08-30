import frappe

# v3_prefix_branch_fields moved the branch fields to the custom_ prefix, but on
# installs where both the old and new columns briefly coexisted the unprefixed
# column survived the rename with no DocField left pointing at it. It is dead
# weight that still shows up in exports and raw queries.
#
# Dropping a column is irreversible, so only ever drop one that (a) has no
# DocField, and (b) holds no data.

LEGACY_COLUMNS = {
	"Customer": ["has_branches"],
	"Sales Invoice": ["has_branches", "branch"],
	"Sales Order": ["has_branches", "branch"],
	"Delivery Note": ["has_branches", "branch"],
}


def execute():
	dropped = []
	kept = []

	for doctype, columns in LEGACY_COLUMNS.items():
		if not frappe.db.table_exists(doctype):
			continue

		meta = frappe.get_meta(doctype)

		for column in columns:
			if not frappe.db.has_column(doctype, column):
				continue

			if meta.get_field(column):
				kept.append(f"{doctype}.{column} (still a DocField)")
				continue

			rows = frappe.db.sql(
				f"""SELECT COUNT(*) FROM `tab{doctype}`
				    WHERE `{column}` IS NOT NULL AND `{column}` != '' AND `{column}` != 0"""
			)[0][0]

			if rows:
				kept.append(f"{doctype}.{column} ({rows} row(s) still carry a value)")
				continue

			frappe.db.commit()  # DDL implicitly commits; close the open transaction first
			frappe.db.sql_ddl(f"ALTER TABLE `tab{doctype}` DROP COLUMN `{column}`")
			dropped.append(f"{doctype}.{column}")

	for entry in kept:
		print(f"mu_customers: kept orphan column {entry}")
	print(f"mu_customers: dropped {len(dropped)} orphan branch column(s): {dropped or 'none'}")
