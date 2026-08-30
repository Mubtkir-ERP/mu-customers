import frappe

# Empty Data fields that existed only to push columns around in the form
# layout. Each one was a real column in the table and showed up in exports,
# imports and field pickers.
#
# The third element is the field the filler itself followed: anything anchored
# to the filler is repointed there, otherwise removing it would drop those
# section and column breaks to the bottom of the form.
FILLERS = [
	("Sales Order", "custom_blank", "column_break_38"),
	("Purchase Order", "custom_blank", "column_break_53"),
	("Purchase Invoice", "custom_blank", "column_break_58"),
	("Purchase Invoice", "custom_blanck_2", "section_break_51"),
]


def execute():
	for dt, fieldname, fallback in FILLERS:
		_repoint_dependents(dt, fieldname, fallback)

		name = f"{dt}-{fieldname}"
		if frappe.db.exists("Custom Field", name):
			frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)

		frappe.clear_cache(doctype=dt)


def _repoint_dependents(dt, fieldname, fallback):
	frappe.db.set_value(
		"Custom Field",
		{"dt": dt, "insert_after": fieldname},
		"insert_after",
		fallback,
		update_modified=False,
	)
