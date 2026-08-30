import frappe

# The branch fields shipped without the custom_ prefix Frappe reserves for
# app-added fields on core doctypes, so a future ERPNext release adding its own
# `branch` to Sales Invoice would have collided at the column level.
RENAMES = [
	("Customer", "branches", "custom_branches"),
	("Customer", "has_branches", "custom_has_branches"),
	("Sales Invoice", "branch", "custom_branch"),
	("Sales Invoice", "has_branches", "custom_has_branches"),
	("Sales Order", "branch", "custom_branch"),
	("Sales Order", "has_branches", "custom_has_branches"),
	("Delivery Note", "branch", "custom_branch"),
	("Delivery Note", "has_branches", "custom_has_branches"),
]


def execute():
	for dt, old, new in RENAMES:
		fieldtype = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": old}, "fieldtype")
		_migrate_data(dt, old, new, fieldtype)
		_rename_custom_field(dt, old, new)

	frappe.db.commit()
	frappe.clear_cache()


def _rename_custom_field(dt, old, new):
	old_name = f"{dt}-{old}"
	new_name = f"{dt}-{new}"

	if not frappe.db.exists("Custom Field", old_name):
		return

	if frappe.db.exists("Custom Field", new_name):
		# Both present: the prefixed one wins, drop the legacy definition.
		frappe.db.sql("DELETE FROM `tabCustom Field` WHERE name = %s", old_name)
	else:
		frappe.db.sql(
			"UPDATE `tabCustom Field` SET name = %s, fieldname = %s WHERE name = %s",
			(new_name, new, old_name),
		)

	frappe.db.sql(
		"UPDATE `tabCustom Field` SET insert_after = %s WHERE dt = %s AND insert_after = %s",
		(new, dt, old),
	)


def _migrate_data(dt, old, new, fieldtype):
	if fieldtype == "Table":
		# Table fields have no column on the parent; the link is parentfield
		# on every child row.
		child_dt = frappe.db.get_value("Custom Field", {"dt": dt, "fieldname": old}, "options")
		if child_dt and frappe.db.table_exists(child_dt):
			frappe.db.sql(
				f"UPDATE `tab{child_dt}` SET parentfield = %s WHERE parenttype = %s AND parentfield = %s",
				(new, dt, old),
			)
		return

	if not frappe.db.table_exists(dt):
		return

	table = f"tab{dt}"
	columns = [c[0] for c in frappe.db.sql(f"SHOW COLUMNS FROM `{table}`")]

	if old not in columns:
		return

	if new in columns:
		# Carry values over, then drop the unprefixed column.
		frappe.db.sql(
			f"UPDATE `{table}` SET `{new}` = `{old}` "
			f"WHERE `{old}` IS NOT NULL AND (`{new}` IS NULL OR `{new}` = '' OR `{new}` = 0)"
		)
		# DDL implicitly commits, so close the open transaction first.
		frappe.db.commit()
		frappe.db.sql_ddl(f"ALTER TABLE `{table}` DROP COLUMN `{old}`")
		return

	definition = frappe.db.sql(
		"""
		SELECT column_type, is_nullable, column_default
		FROM information_schema.columns
		WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s
		""",
		(table, old),
		as_dict=True,
	)
	if not definition:
		return

	col = definition[0]
	spec = col.column_type
	spec += " NULL" if col.is_nullable == "YES" else " NOT NULL"
	if col.column_default is not None:
		spec += f" DEFAULT {frappe.db.escape(col.column_default)}"

	frappe.db.commit()
	frappe.db.sql_ddl(f"ALTER TABLE `{table}` CHANGE COLUMN `{old}` `{new}` {spec}")
