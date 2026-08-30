"""Drop the column a regression test left behind on Sales Invoice.

One test created a throwaway Custom Field called `_mu_probe_field` to prove the
form was still customisable. Its cleanup removed the Custom Field, but deleting
a Custom Field in Frappe leaves the underlying column in place, so an empty
`_mu_probe_field` column stayed on `tabSales Invoice`. The test is gone; this
removes what it left.

The app never shipped this field, so the patch is written to be a no-op
everywhere except a site where those tests actually ran.
"""

import frappe

PROBE_COLUMNS = (
	("Sales Invoice", "_mu_probe_field"),
)


def execute():
	dropped = []

	for doctype, column in PROBE_COLUMNS:
		if drop_if_orphaned(doctype, column):
			dropped.append(f"{doctype}.{column}")

	if dropped:
		frappe.clear_cache()
		print(f"mu_customers: dropped {len(dropped)} leftover test column(s): {dropped}")


def drop_if_orphaned(doctype, column):
	"""Refuse to touch anything that is still a real field or holds data."""
	if not frappe.db.table_exists(doctype) or not frappe.db.has_column(doctype, column):
		return False

	# A field someone genuinely uses must survive, however it got here.
	if frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": column}):
		return False

	if frappe.get_meta(doctype).get_field(column):
		return False

	rows = frappe.db.sql(
		f"select count(*) from `tab{doctype}` where ifnull(`{column}`, '') != ''"
	)[0][0]
	if rows:
		print(f"mu_customers: {doctype}.{column} holds {rows} value(s), left in place")
		return False

	frappe.db.sql_ddl(f"alter table `tab{doctype}` drop column `{column}`")
	return True
