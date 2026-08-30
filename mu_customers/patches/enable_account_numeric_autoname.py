import frappe

# Account naming is now behind a switch in Extra Features Settings rather than
# hijacking every Account unconditionally. Sites that already relied on it keep
# the behaviour; the switch simply makes it visible and reversible.


def execute():
	if not frappe.db.exists("DocType", "Extra Features Settings"):
		return

	settings = frappe.get_single("Extra Features Settings")
	if settings.get("enable_account_numeric_autoname") is None:
		return

	settings.enable_account_numeric_autoname = 1
	settings.flags.ignore_permissions = True
	settings.save()
