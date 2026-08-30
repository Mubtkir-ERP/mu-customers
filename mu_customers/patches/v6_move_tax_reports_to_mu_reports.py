"""Drop the three tax reports; they live in the mu_reports app now.

Their files are gone from this app, but the Report records they created stay in
the database and would keep showing up in the report list - and, worse, would
shadow the mu_reports versions of the same three names.

Only records this app owns are touched: a Report is deleted just while it still
claims module "Mu Customers". Once mu_reports has re-created it under its own
module, this leaves it alone.
"""

import frappe

MOVED_REPORTS = ("Tax Report", "All Tax Report", "Tax Statement Report")


def execute():
	removed = []

	for report in MOVED_REPORTS:
		module = frappe.db.get_value("Report", report, "module")
		if module != "Mu Customers":
			# Either already gone, or now owned by mu_reports.
			continue

		frappe.delete_doc("Report", report, ignore_permissions=True, force=True, delete_permanently=True)
		removed.append(report)

	if removed:
		print(f"mu_customers: removed {len(removed)} report(s) now owned by mu_reports: {removed}")
