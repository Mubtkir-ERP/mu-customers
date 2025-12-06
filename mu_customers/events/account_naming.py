import json

import frappe


def custom_autoname(doc, method):
	company_abr = frappe.db.get_value("Company", {"name": doc.company}, ["abbr"])
	# site_json = frappe.db.get_single_value("Feature Settings", "site_json")
	# if site_json:
	#         site_json_dict = json.loads(site_json)
	#         if site_json_dict.get("enable_account_serires") == 1:
	if not doc.parent_account:
		if doc.account_number:
			last_account_number = frappe.db.get_value(
				"Account", {"parent_account": None}, "account_number", order_by="creation desc"
			)
		doc.name = f"{doc.account_number} - {doc.account_name} - {company_abr}"
	else:
		parent_account_number = frappe.db.get_value("Account", doc.parent_account, "account_number") or 0
		if parent_account_number:
			base_number = int(parent_account_number)
		sibling_accounts = frappe.get_all(
			"Account",
			filters={"parent_account": doc.parent_account},
			fields=["account_number", "name"],
			order_by="creation desc",
		)
		Total_custom_counter = sum(int(sibling.get("custom_counter", 1)) for sibling in sibling_accounts)
		all_len = str(Total_custom_counter + 1).zfill(2)
		last_account_number = base_number
		new_account_number = str(last_account_number) + all_len
		doc.account_number = new_account_number
		doc.name = f"{doc.account_number} - {doc.account_name} - {company_abr}"
