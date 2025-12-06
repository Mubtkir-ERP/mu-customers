import frappe


def clear_auto_description(doc, method=None):
	if not doc.description:
		return
	desc = doc.description.strip()
	if desc == (doc.item_name or "").strip() or desc == (doc.item_code or "").strip():
		doc.description = ""


def custom_autoname(doc, method):
	# site_json = frappe.db.get_single_value("Feature Settings", "site_json")
	# if site_json:
	#     site_json_dict = json.loads(site_json)
	#     if site_json_dict.get("enable_item_series") == 0:
	if not doc.item_code:
		last_item = frappe.db.get_value("Item", filters={}, fieldname="name", order_by="creation desc")
		if last_item and last_item.isdigit():
			new_name = str(int(last_item) + 1)
		else:
			new_name = "1"
	else:
		starting_number = int(doc.item_code)
		last_item = frappe.db.get_value(
			"Item", filters={"name": starting_number}, fieldname="name", order_by="creation desc"
		)
		if last_item and last_item.isdigit():
			new_name = str(int(last_item) + 1)
		else:
			new_name = str(starting_number)
	while frappe.db.exists("Item", new_name):
		new_name = str(int(new_name) + 1)
		# frappe.msgprint(new_name)
	doc.name = new_name
