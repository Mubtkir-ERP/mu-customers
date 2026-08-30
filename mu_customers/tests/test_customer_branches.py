"""Tests for the customer branch list behind the Branch field filter.

This lookup shipped as a client-side child-table query and threw
`DatabaseQuery.execute() got an unexpected keyword argument 'parent'` on every
customer selection, because frappe.db.get_list posts to
frappe.desk.reportview.get_list, which forwards its arguments straight into
DatabaseQuery.execute(). Nothing in the suite could catch that while the query
lived in JavaScript, so it now runs through a server endpoint that these tests
exercise directly.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from mu_customers.api import get_customer_branches

CUSTOMER = "_MU Branch Customer"
BARE_CUSTOMER = "_MU Bare Customer"
BRANCHES = ("_MU Branch North", "_MU Branch South")
OTHER_BRANCH = "_MU Branch Elsewhere"
PROBE = "_mu_branch_probe@example.com"


def drop(doctype, name):
	if frappe.db.exists(doctype, name):
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)


def make_branch(name):
	if not frappe.db.exists("Branch", name):
		frappe.get_doc({"doctype": "Branch", "branch": name}).insert()


class TestCustomerBranches(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for name in (CUSTOMER, BARE_CUSTOMER):
			drop("Customer", name)

		for branch in (*BRANCHES, OTHER_BRANCH):
			make_branch(branch)

		group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
		territory = frappe.db.get_value("Territory", {"is_group": 0}, "name")

		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": CUSTOMER,
			"customer_group": group,
			"territory": territory,
			"custom_has_branches": 1,
		})
		for branch in BRANCHES:
			customer.append("custom_branches", {"branch": branch})
		customer.insert()
		cls.customer = customer.name

		bare = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": BARE_CUSTOMER,
			"customer_group": group,
			"territory": territory,
		}).insert()
		cls.bare = bare.name

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		for name in (cls.customer, cls.bare):
			drop("Customer", name)
		super().tearDownClass()

	def test_lookup_does_not_raise(self):
		"""The exact failure the user hit: a TypeError on customer selection."""
		try:
			get_customer_branches(self.customer)
		except TypeError as error:
			self.fail(f"branch lookup raised TypeError: {error}")

	def test_returns_the_customers_own_branches(self):
		self.assertEqual(sorted(get_customer_branches(self.customer)), sorted(BRANCHES))

	def test_excludes_branches_belonging_to_nobody(self):
		self.assertNotIn(OTHER_BRANCH, get_customer_branches(self.customer))

	def test_customer_without_branches_returns_empty(self):
		self.assertEqual(get_customer_branches(self.bare), [])

	def test_blank_customer_returns_empty(self):
		self.assertEqual(get_customer_branches(""), [])
		self.assertEqual(get_customer_branches(None), [])

	def test_returns_plain_branch_names(self):
		"""The form filters on `name in [...]`, so this must be a flat list."""
		branches = get_customer_branches(self.customer)
		self.assertTrue(all(isinstance(b, str) for b in branches), branches)


class TestCustomerBranchPermissions(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("User", PROBE):
			user = frappe.get_doc({
				"doctype": "User",
				"email": PROBE,
				"first_name": "Probe",
				"send_welcome_email": 0,
			}).insert(ignore_permissions=True)
			user.set("roles", [])
			user.save(ignore_permissions=True)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		drop("User", PROBE)
		super().tearDownClass()

	def setUp(self):
		self.addCleanup(frappe.set_user, "Administrator")

	def test_refuses_a_user_without_customer_access(self):
		customer = frappe.db.get_value("Customer", {}, "name")
		if not customer:
			self.skipTest("no customer on this site")
		frappe.set_user(PROBE)
		with self.assertRaises(frappe.PermissionError):
			get_customer_branches(customer)
