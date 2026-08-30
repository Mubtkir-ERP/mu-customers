import frappe

# Account.custom_counter was read as sibling.get("custom_counter", 1) from a
# frappe.get_all() that never selected the column, so the default 1 was used
# every time and the field did nothing. The rewritten naming logic numbers
# children from the parent directly and has no use for a counter.
#
# Removed only when every row still holds the same single value - if anyone
# actually populated it, the field stays and a note is logged instead.
NAME = "Account-custom_counter"
FIELD = "custom_counter"


def execute():
	if not frappe.db.has_column("Account", FIELD):
		_delete_custom_field()
		return

	distinct = frappe.db.sql(
		f"select distinct `{FIELD}` from `tabAccount` where `{FIELD}` is not null and `{FIELD}` != ''"
	)

	if len(distinct) > 1:
		frappe.log_error(
			title="mu_customers: Account.custom_counter kept",
			message=(
				f"The field holds {len(distinct)} distinct values, so it was not removed. "
				"It is no longer read by the account naming logic - review and drop it manually "
				"once you have confirmed the values are not needed."
			),
		)
		return

	_delete_custom_field()

	frappe.db.commit()  # DDL implicitly commits; close the open transaction first
	frappe.db.sql_ddl(f"ALTER TABLE `tabAccount` DROP COLUMN `{FIELD}`")
	frappe.clear_cache(doctype="Account")


def _delete_custom_field():
	if frappe.db.exists("Custom Field", NAME):
		frappe.delete_doc("Custom Field", NAME, ignore_permissions=True, force=True)
