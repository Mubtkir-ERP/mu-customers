"""Hand the Customer form back to ERPNext.

Two things this app had changed are reverted:

* the address and contact sections had their collapsible flag overridden;
* the Selling Settings default for customer_group may point at a group node.

The second is the reason a quick entry save failed. ERPNext rejects a
group-type Customer Group ("Cannot select a Group type Customer Group"), so with
the default set to one, every customer saved without an explicit group was
refused. It is only rewritten when it is actually pointing at a group; a valid
default is left alone.
"""

import frappe

RETIRED_PROPERTY_SETTERS = (
	"Customer-address_contacts-collapsible",
	"Customer-primary_address_and_contact_detail-collapsible",
)


def execute():
	for name in RETIRED_PROPERTY_SETTERS:
		if frappe.db.exists("Property Setter", name):
			frappe.delete_doc("Property Setter", name, ignore_permissions=True, force=True)

	repair_customer_group_default()
	frappe.clear_cache(doctype="Customer")


def repair_customer_group_default():
	"""Point the customer_group default at a group that can actually be saved.

	Returns the value it settled on, or None when it could not help.

	Note ERPNext's own test bootstrap (erpnext.setup.utils.set_defaults_for_tests,
	run by before_tests on every `bench run-tests`) resets this to the root
	Customer Group, which is a group node. Running the test suite on a live site
	therefore re-breaks customer creation until this patch runs again.
	"""
	current = frappe.db.get_default("customer_group")

	if current and not frappe.db.get_value("Customer Group", current, "is_group"):
		# Already a selectable leaf group.
		return current

	replacement = pick_leaf_group()
	if not replacement:
		print("mu_customers: no non-group Customer Group exists; default left as is")
		return None

	# Save through the document rather than writing tabSingles directly:
	# SellingSettings.validate() is what pushes customer_group into the global
	# defaults, so going around it leaves the two able to drift apart.
	settings = frappe.get_doc("Selling Settings")
	settings.customer_group = replacement
	settings.save(ignore_permissions=True)

	print(f"mu_customers: customer_group default {current!r} is a group node -> {replacement!r}")
	return replacement


def pick_leaf_group():
	"""Prefer whatever existing customers already use, so nothing shifts."""
	in_use = frappe.db.sql(
		"""
		SELECT c.customer_group, COUNT(*) AS total
		FROM `tabCustomer` c
		INNER JOIN `tabCustomer Group` g ON g.name = c.customer_group
		WHERE g.is_group = 0
		GROUP BY c.customer_group
		ORDER BY total DESC, c.customer_group ASC
		""",
		as_dict=True,
	)
	if in_use:
		return in_use[0].customer_group

	return frappe.db.get_value("Customer Group", {"is_group": 0}, "name", order_by="lft asc")
