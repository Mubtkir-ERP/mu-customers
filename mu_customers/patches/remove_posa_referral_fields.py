import frappe

# These belong to POS Awesome. They were captured by mistake when the fixtures
# were exported from a development site and have no meaning in this app - and
# would collide outright if POS Awesome were installed alongside it.
POSA_FIELDS = [
	"Customer-posa_referral_section",
	"Customer-posa_referral_code",
	"Customer-posa_referral_company",
]

# Deleting a Custom Field leaves its column behind. Drop the orphans too, but
# only when they are empty - if POS Awesome ever wrote to them, that data is
# not this patch's to destroy.
POSA_COLUMNS = ["posa_referral_code", "posa_referral_company"]


def execute():
	for name in POSA_FIELDS:
		if frappe.db.exists("Custom Field", name):
			frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)

	_drop_empty_columns()

	frappe.clear_cache(doctype="Customer")


def _drop_empty_columns():
	kept = []

	for column in POSA_COLUMNS:
		if not frappe.db.has_column("Customer", column):
			continue

		# Still defined by another app (POS Awesome installed later) - leave it.
		if frappe.db.exists("Custom Field", {"dt": "Customer", "fieldname": column}):
			continue

		rows = frappe.db.sql(
			f"select count(*) from `tabCustomer` where `{column}` is not null and `{column}` != ''"
		)[0][0]

		if rows:
			kept.append(f"{column} ({rows} row(s) with data)")
			continue

		frappe.db.commit()  # DDL implicitly commits; close the open transaction first
		frappe.db.sql_ddl(f"ALTER TABLE `tabCustomer` DROP COLUMN `{column}`")

	if kept:
		frappe.log_error(
			title="mu_customers: posa columns kept",
			message="Not dropped because they still hold data: " + ", ".join(kept),
		)
