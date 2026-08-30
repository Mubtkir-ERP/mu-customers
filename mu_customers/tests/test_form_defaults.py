"""Tests for the invoice and quick-entry defaults the client asked for.

Three separate one-click-save failures are covered here: an Item refusing to
save without a code, a Customer refusing to save because the default customer
group was a group node, and Update Stock needing to default on while staying
clearable unless it is explicitly locked.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

STOCK_DOCTYPES = ("Sales Invoice", "Purchase Invoice")


def leaf_item_group():
	return frappe.db.get_value("Item Group", {"is_group": 0}, "name")


def drop(doctype, name):
	if frappe.db.exists(doctype, name):
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)


class TestUpdateStockDefault(FrappeTestCase):
	def test_new_invoice_opens_with_update_stock_ticked(self):
		for doctype in STOCK_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertEqual(frappe.new_doc(doctype).update_stock, 1)

	def test_update_stock_is_not_read_only_on_the_doctype(self):
		"""The lock is applied in the form from the setting, never baked in."""
		for doctype in STOCK_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertFalse(frappe.get_meta(doctype).get_field("update_stock").read_only)

	def test_update_stock_can_still_be_cleared(self):
		for doctype in STOCK_DOCTYPES:
			with self.subTest(doctype=doctype):
				doc = frappe.new_doc(doctype)
				doc.update_stock = 0
				self.assertEqual(doc.update_stock, 0)

	def test_force_update_stock_setting_exists(self):
		field = frappe.get_meta("Extra Features Settings").get_field("force_update_stock")
		self.assertIsNotNone(field, "force_update_stock is missing from the settings")
		self.assertEqual(field.fieldtype, "Check")
		# The default is a business choice, so it is not asserted here. What
		# matters is that the switch exists and that both positions work, which
		# TestForceUpdateStockServerSide covers.
		self.assertIn(field.default, ("0", "1"))


class TestForceUpdateStockServerSide(FrappeTestCase):
	"""The form lock is a UI state; an import or API call can still write 0.

	These cover the server-side hook that closes that gap.
	"""

	def setUp(self):
		self.original = frappe.db.get_single_value("Extra Features Settings", "force_update_stock")
		self.addCleanup(self.set_force, self.original)

	def set_force(self, value):
		settings = frappe.get_single("Extra Features Settings")
		settings.force_update_stock = value
		settings.save(ignore_permissions=True)

	def invoice(self, doctype, update_stock, linked_field=None):
		doc = frappe.new_doc(doctype)
		doc.update_stock = update_stock
		row = doc.append("items", {})
		if linked_field:
			row.set(linked_field, "SOME-LINKED-ROW")
		return doc

	def force(self, doc):
		from mu_customers.events.invoice import force_update_stock

		force_update_stock(doc)
		return doc.update_stock

	def test_setting_on_forces_a_cleared_flag_back_on(self):
		self.set_force(1)
		for doctype in STOCK_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertEqual(self.force(self.invoice(doctype, 0)), 1)

	def test_setting_off_leaves_a_cleared_flag_alone(self):
		self.set_force(0)
		for doctype in STOCK_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertEqual(self.force(self.invoice(doctype, 0)), 0)

	def test_an_already_ticked_flag_is_untouched(self):
		self.set_force(1)
		for doctype in STOCK_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertEqual(self.force(self.invoice(doctype, 1)), 1)

	def test_invoices_drawn_from_a_stock_document_are_skipped(self):
		"""Those already moved the stock - forcing it on would post it twice."""
		self.set_force(1)
		for doctype, linked in (("Sales Invoice", "dn_detail"), ("Purchase Invoice", "pr_detail")):
			with self.subTest(doctype=doctype):
				self.assertEqual(self.force(self.invoice(doctype, 0, linked_field=linked)), 0)


class TestCustomerGroupDefault(FrappeTestCase):
	"""ERPNext refuses a group-type Customer Group, which is what blocked
	quick entry: the default pointed at the root group.

	These exercise the repair itself rather than the site's ambient default,
	because ERPNext's own before_tests hook resets that default to the root
	group on every test run - so asserting on it here would test the harness.
	"""

	def setUp(self):
		self.original = frappe.db.get_default("customer_group")
		self.addCleanup(self.restore)

	def restore(self):
		if self.original:
			settings = frappe.get_doc("Selling Settings")
			settings.customer_group = self.original
			settings.save(ignore_permissions=True)

	def set_default(self, value):
		settings = frappe.get_doc("Selling Settings")
		settings.customer_group = value
		settings.save(ignore_permissions=True)
		# frappe.db.get_default reads through a cache that saving Selling
		# Settings does not always invalidate in the same request, so the repair
		# under test could otherwise still see the previous default.
		from frappe.cache_manager import clear_defaults_cache

		clear_defaults_cache()

	def test_repair_replaces_a_group_node_default(self):
		from mu_customers.patches.v6_restore_standard_customer_form import (
			repair_customer_group_default,
		)

		group_node = frappe.db.get_value("Customer Group", {"is_group": 1}, "name")
		if not group_node:
			self.skipTest("no group-type Customer Group on this site")

		self.set_default(group_node)
		chosen = repair_customer_group_default()

		self.assertIsNotNone(chosen, "repair gave up on a group-node default")
		self.assertFalse(frappe.db.get_value("Customer Group", chosen, "is_group"))
		self.assertEqual(frappe.db.get_default("customer_group"), chosen)

	def test_repair_leaves_a_valid_default_alone(self):
		from mu_customers.patches.v6_restore_standard_customer_form import (
			repair_customer_group_default,
		)

		leaf = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
		if not leaf:
			self.skipTest("no non-group Customer Group on this site")

		self.set_default(leaf)
		self.assertEqual(repair_customer_group_default(), leaf)
		self.assertEqual(frappe.db.get_default("customer_group"), leaf)

	def test_customer_saves_without_choosing_a_group(self):
		from mu_customers.patches.v6_restore_standard_customer_form import (
			repair_customer_group_default,
		)

		repair_customer_group_default()

		name = "_MU Quick Customer"
		drop("Customer", name)
		self.addCleanup(drop, "Customer", name)

		customer = frappe.new_doc("Customer")
		customer.customer_name = name
		customer.insert(ignore_permissions=True)

		self.assertTrue(customer.customer_group)
		self.assertFalse(frappe.db.get_value("Customer Group", customer.customer_group, "is_group"))

	def test_customer_group_is_offered_in_quick_entry(self):
		field = frappe.get_meta("Customer").get_field("customer_group")
		self.assertTrue(field.allow_in_quick_entry, "customer_group is not offered in quick entry")

	def test_customer_group_is_not_mandatory(self):
		"""It has to accept a blank so the default can fill it in on save."""
		self.assertFalse(frappe.get_meta("Customer").get_field("customer_group").reqd)

	def test_a_blank_group_is_left_blank(self):
		"""No hook fills it any more - the system default applies only to a
		*missing* value, which is ERPNext's own behaviour."""
		name = "_MU Blank Group Customer"
		drop("Customer", name)
		self.addCleanup(drop, "Customer", name)

		customer = frappe.new_doc("Customer")
		customer.customer_name = name
		customer.customer_group = ""
		customer.insert(ignore_permissions=True)

		self.assertEqual(customer.customer_group, "", "something is still filling a blank group in")

	def test_the_app_no_longer_hooks_customer(self):
		from mu_customers import hooks

		self.assertNotIn(
			"Customer", hooks.doc_events, "the app is hooking Customer again"
		)


class TestCustomerFormLeftStandard(FrappeTestCase):
	"""The Customer form and its quick entry stay as ERPNext ships them."""

	RETIRED = (
		"Customer-address_contacts-collapsible",
		"Customer-primary_address_and_contact_detail-collapsible",
	)

	def test_section_overrides_are_gone(self):
		for name in self.RETIRED:
			with self.subTest(property_setter=name):
				self.assertFalse(frappe.db.exists("Property Setter", name))

	def test_no_quick_entry_override_is_shipped(self):
		"""The Customer dialog is ERPNext's, untouched."""
		import os

		import mu_customers

		path = os.path.join(
			os.path.dirname(mu_customers.__file__), "public", "js", "customer_quick_entry.js"
		)
		self.assertFalse(os.path.exists(path), "a Customer quick entry override is back")

		from mu_customers import hooks

		self.assertNotIn(
			"customer_quick_entry.js",
			" ".join(hooks.app_include_js),
			"the override is still wired into app_include_js",
		)

	def test_erpnext_keeps_its_own_contact_and_address_blocks(self):
		"""Those blocks come from ContactAddressQuickEntryForm, which is the
		same class object as the Supplier dialog. Nothing this app ships may
		reassign or patch it."""
		import os

		import mu_customers

		js_dir = os.path.join(os.path.dirname(mu_customers.__file__), "public", "js")
		for filename in sorted(os.listdir(js_dir)):
			if not filename.endswith(".js"):
				continue
			source = open(os.path.join(js_dir, filename)).read()
			with self.subTest(script=filename):
				self.assertNotIn("CustomerQuickEntryForm", source)
				self.assertNotIn("SupplierQuickEntryForm", source)
				self.assertNotIn("ContactAddressQuickEntryForm", source)


class TestItemCodeFallback(FrappeTestCase):
	def setUp(self):
		self.settings = frappe.get_single("Extra Features Settings")
		self.original = self.settings.enable_item_numeric_autoname
		self.addCleanup(self.restore)

	def restore(self):
		settings = frappe.get_single("Extra Features Settings")
		settings.enable_item_numeric_autoname = self.original
		settings.save(ignore_permissions=True)

	def set_numeric(self, value):
		settings = frappe.get_single("Extra Features Settings")
		settings.enable_item_numeric_autoname = value
		settings.save(ignore_permissions=True)

	def make(self, item_name, item_code=None):
		item = frappe.new_doc("Item")
		if item_code:
			item.item_code = item_code
		item.item_name = item_name
		item.item_group = leaf_item_group()
		item.stock_uom = "Nos"
		item.is_stock_item = 0
		item.insert(ignore_permissions=True)
		self.addCleanup(drop, "Item", item.name)
		return item

	def test_blank_code_falls_back_to_the_item_name(self):
		self.set_numeric(0)
		item = self.make("_MU Fallback Item")
		self.assertEqual(item.item_code, "_MU Fallback Item")
		self.assertEqual(item.name, "_MU Fallback Item")

	def test_typed_code_is_kept(self):
		self.set_numeric(0)
		item = self.make("_MU Typed Item", item_code="_MU-CODE-9")
		self.assertEqual(item.item_code, "_MU-CODE-9")

	def test_numeric_series_still_wins_when_enabled(self):
		self.set_numeric(1)
		item = self.make("_MU Numeric Item")
		self.assertTrue(item.item_code.isdigit(), f"expected a numeric code, got {item.item_code!r}")

	def test_item_code_is_offered_in_quick_entry_and_not_mandatory(self):
		field = frappe.get_meta("Item").get_field("item_code")
		self.assertTrue(field.allow_in_quick_entry, "item_code is not offered in quick entry")
		self.assertFalse(field.reqd, "item_code is still mandatory")


class TestItemQuickEntryFits(FrappeTestCase):
	"""Frappe abandons the dialog for the full form above seven fields."""

	LIMIT = 7

	def quick_entry_fields(self, doctype):
		return [
			df.fieldname
			for df in frappe.get_meta(doctype).fields
			if (df.reqd or df.allow_in_quick_entry) and not df.read_only and df.fieldtype != "Tab Break"
		]

	def test_item_dialog_is_within_the_limit(self):
		fields = self.quick_entry_fields("Item")
		self.assertLessEqual(
			len(fields),
			self.LIMIT,
			f"Item quick entry would fall back to the full form: {fields}",
		)

	def test_the_two_retired_fields_are_gone(self):
		for name in ("Item-standard_rate-allow_in_quick_entry",
					 "Item-valuation_rate-allow_in_quick_entry"):
			with self.subTest(property_setter=name):
				self.assertFalse(frappe.db.exists("Property Setter", name))

	def test_customer_dialog_is_within_the_limit(self):
		fields = self.quick_entry_fields("Customer")
		self.assertLessEqual(len(fields), self.LIMIT, f"Customer quick entry too wide: {fields}")


class TestTaxReportsRemoved(FrappeTestCase):
	"""The three reports moved to mu_reports and must not linger here."""

	MOVED = ("Tax Report", "All Tax Report", "Tax Statement Report")

	def test_no_report_is_still_owned_by_this_app(self):
		for report in self.MOVED:
			with self.subTest(report=report):
				self.assertNotEqual(
					frappe.db.get_value("Report", report, "module"),
					"Mu Customers",
					f"{report} is still registered under Mu Customers",
				)

	def test_module_ships_no_reports(self):
		self.assertEqual(frappe.db.get_all("Report", {"module": "Mu Customers"}, pluck="name"), [])
