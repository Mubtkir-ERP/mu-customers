"""Tests for the invoice and quick-entry defaults the client asked for.

Three separate one-click-save failures are covered here: an Item refusing to
save without a code, a Customer refusing to save because the default customer
group was a group node, and Update Stock needing to default on while remaining
a site-level Customize Form choice.
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
	"""Update Stock starts at 1 but remains a site-level Customize Form choice."""

	def setUp(self):
		self.original = {}
		for doctype in STOCK_DOCTYPES:
			name = f"{doctype}-update_stock-default"
			self.original[doctype] = frappe.db.get_value(
				"Property Setter", name, ["name", "value", "module"], as_dict=True
			)
		self.addCleanup(self.restore_defaults)

	def restore_defaults(self):
		for doctype in STOCK_DOCTYPES:
			name = f"{doctype}-update_stock-default"
			if frappe.db.exists("Property Setter", name):
				frappe.delete_doc("Property Setter", name, force=True, ignore_permissions=True)

			original = self.original[doctype]
			if original:
				frappe.make_property_setter(
					{
						"doctype": doctype,
						"doctype_or_field": "DocField",
						"fieldname": "update_stock",
						"property": "default",
						"value": original.value,
						"property_type": "Check",
					},
					is_system_generated=False,
				)
				frappe.db.set_value("Property Setter", name, "module", original.module)
			frappe.clear_cache(doctype=doctype)

	def set_default(self, doctype, value):
		frappe.make_property_setter(
			{
				"doctype": doctype,
				"doctype_or_field": "DocField",
				"fieldname": "update_stock",
				"property": "default",
				"value": str(int(value)),
				"property_type": "Check",
			},
			is_system_generated=False,
		)
		frappe.clear_cache(doctype=doctype)

	def test_initializer_creates_one_only_when_missing(self):
		from mu_customers.install import ensure_update_stock_defaults

		for doctype in STOCK_DOCTYPES:
			name = f"{doctype}-update_stock-default"
			if frappe.db.exists("Property Setter", name):
				frappe.delete_doc("Property Setter", name, force=True, ignore_permissions=True)
			frappe.clear_cache(doctype=doctype)

		ensure_update_stock_defaults()

		for doctype in STOCK_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertEqual(
					frappe.db.get_value(
						"Property Setter", f"{doctype}-update_stock-default", "value"
					),
					"1",
				)
				self.assertEqual(frappe.new_doc(doctype).update_stock, 1)

	def test_customize_form_zero_is_preserved(self):
		from mu_customers.install import ensure_update_stock_defaults

		for doctype in STOCK_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.set_default(doctype, 0)
				ensure_update_stock_defaults()
				self.assertEqual(
					frappe.db.get_value(
						"Property Setter", f"{doctype}-update_stock-default", "value"
					),
					"0",
				)
				self.assertEqual(frappe.new_doc(doctype).update_stock, 0)

	def test_update_stock_is_editable(self):
		for doctype in STOCK_DOCTYPES:
			with self.subTest(doctype=doctype):
				field = frappe.get_meta(doctype).get_field("update_stock")
				self.assertFalse(field.read_only)

				doc = frappe.new_doc(doctype)
				doc.update_stock = 0 if doc.update_stock else 1
				self.assertIn(doc.update_stock, (0, 1))

	def test_app_no_longer_forces_update_stock(self):
		from mu_customers import hooks

		self.assertIsNone(frappe.get_meta("Extra Features Settings").get_field("force_update_stock"))
		self.assertNotIn("update_stock.js", str(hooks.doctype_js))

		for doctype in STOCK_DOCTYPES:
			with self.subTest(doctype=doctype):
				events = hooks.doc_events.get(doctype, {})
				self.assertNotIn("validate", events)

	def test_update_stock_defaults_are_not_fixture_owned(self):
		import json
		import os

		import mu_customers

		path = os.path.join(os.path.dirname(mu_customers.__file__), "fixtures", "property_setter.json")
		with open(path) as handle:
			setters = json.load(handle)

		names = {row.get("name") for row in setters}
		for doctype in STOCK_DOCTYPES:
			self.assertNotIn(f"{doctype}-update_stock-default", names)


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
