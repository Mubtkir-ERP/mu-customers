import frappe

# The field held a numeric total in a Data column, so it never formatted,
# sorted or aggregated as a number.
#
# Converted in place rather than by recreating the field: dropping and
# re-adding leaves Frappe trying to MODIFY a varchar full of NULLs into a
# "decimal NOT NULL", which MariaDB rejects outright in strict mode.
FIELD = "custom_default_warehouse_qty"
NAME = f"Item-{FIELD}"
COLUMN_SPEC = "decimal(21,9) NOT NULL DEFAULT 0"


def execute():
	_align_custom_field()

	if not frappe.db.has_column("Item", FIELD):
		# Nothing to convert - the field ships as a Float in fixtures.
		return

	column_type = frappe.db.sql(
		"""
		SELECT column_type FROM information_schema.columns
		WHERE table_schema = DATABASE() AND table_name = 'tabItem' AND column_name = %s
		""",
		FIELD,
	)
	if column_type and column_type[0][0].startswith("decimal"):
		return

	# NULLs and any non-numeric text left over from the Data era become 0;
	# the value is recomputed on the next stock movement anyway.
	frappe.db.sql(
		f"""
		UPDATE `tabItem`
		SET `{FIELD}` = '0'
		WHERE `{FIELD}` IS NULL
		   OR `{FIELD}` = ''
		   OR `{FIELD}` NOT REGEXP '^-?[0-9]+(\\.[0-9]+)?$'
		"""
	)
	frappe.db.commit()

	frappe.db.sql_ddl(f"ALTER TABLE `tabItem` MODIFY `{FIELD}` {COLUMN_SPEC}")
	frappe.db.commit()

	frappe.clear_cache(doctype="Item")


def _align_custom_field():
	"""Set the field definition straight from the DB.

	Custom Field.validate refuses a Data -> Float change, so the row is
	updated directly; the column conversion above is what actually matters.
	"""
	if not frappe.db.exists("Custom Field", NAME):
		return

	frappe.db.set_value(
		"Custom Field",
		NAME,
		{
			"fieldtype": "Float",
			"label": "Default Warehouse Qty",
			"insert_after": "valuation_method",  # inside the Inventory tab
			"read_only": 1,
			"no_copy": 1,
		},
		update_modified=False,
	)
