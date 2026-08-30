"""Regression tests for the two naming hooks.

Every case here reproduces a crash or a wrong result that shipped in 0.2.2.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from mu_customers.events.account_naming import _numeric_base
from mu_customers.events.item import _next_numeric_code


def _settings(**values):
	doc = frappe.get_single("Extra Features Settings")
	doc.update(values)
	doc.flags.ignore_permissions = True
	doc.save()


class TestAccountNumericBase(FrappeTestCase):
	def test_plain_number(self):
		self.assertEqual(_numeric_base("1000"), 1000)

	def test_ranged_number_from_standard_chart(self):
		# "1100-1600 - Current Assets" ships with ERPNext's standard chart and
		# used to raise ValueError from int().
		self.assertEqual(_numeric_base("1100-1600"), 1100)

	def test_missing_number(self):
		self.assertIsNone(_numeric_base(None))
		self.assertIsNone(_numeric_base(""))

	def test_non_numeric(self):
		self.assertIsNone(_numeric_base("Current Assets"))


class TestAccountNaming(FrappeTestCase):
	def setUp(self):
		_settings(enable_account_numeric_autoname=1)
		self.company = frappe.db.get_value("Company", {}, "name")
		self.abbr = frappe.db.get_value("Company", self.company, "abbr")

	def _group(self, account_number):
		# "parent_account in (NULL, '')" never matches in SQL - use "is not set".
		root = frappe.db.get_value(
			"Account",
			{"company": self.company, "is_group": 1, "root_type": "Asset", "parent_account": ["is", "not set"]},
			"name",
		)
		self.assertTrue(root, "no root Asset account for this company")
		doc = frappe.new_doc("Account")
		doc.update(
			{
				"account_name": frappe.generate_hash(length=8),
				"company": self.company,
				"is_group": 1,
				"root_type": "Asset",
				"parent_account": root,
				"account_number": account_number,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def _child(self, parent):
		doc = frappe.new_doc("Account")
		doc.update(
			{
				"account_name": frappe.generate_hash(length=8),
				"company": self.company,
				"root_type": "Asset",
				"parent_account": parent,
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def test_children_are_numbered_from_the_parent(self):
		parent = self._group("7100")
		first = self._child(parent.name)
		second = self._child(parent.name)

		# Same digit width as the parent, incrementing by one - not the old
		# "parent number + zero-padded counter" concatenation that produced
		# 710001 and broke past 99 siblings.
		self.assertEqual(len(first.account_number), len(parent.account_number))
		self.assertEqual(int(second.account_number), int(first.account_number) + 1)
		self.assertEqual(first.name, f"{first.account_number} - {first.account_name} - {self.abbr}")

	def test_parent_without_a_number_does_not_raise(self):
		parent = self._group("7200")
		frappe.db.set_value("Account", parent.name, "account_number", "", update_modified=False)

		child = self._child(parent.name)

		# Falls back to ERPNext's own naming instead of UnboundLocalError.
		self.assertTrue(child.name)
		self.assertNotIn("None", child.name)

	def test_disabled_setting_leaves_naming_alone(self):
		_settings(enable_account_numeric_autoname=0)
		parent = self._group("7300")
		child = self._child(parent.name)
		self.assertFalse(child.account_number)


class TestItemNumericAutoname(FrappeTestCase):
	def setUp(self):
		_settings(enable_item_numeric_autoname=1)
		self.item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")

	def _item(self, item_code):
		doc = frappe.new_doc("Item")
		doc.update(
			{
				"item_code": item_code,
				"item_name": "Test " + frappe.generate_hash(length=6),
				"item_group": self.item_group,
				"stock_uom": "Nos",
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def test_text_item_code_is_accepted(self):
		# int("WIDGET-ABC") used to raise ValueError and block the save.
		doc = self._item("WIDGET-" + frappe.generate_hash(length=6).upper())
		self.assertEqual(doc.name, doc.item_code)

	def test_blank_item_code_gets_the_next_number(self):
		expected = _next_numeric_code()
		doc = self._item(None)
		self.assertTrue(doc.name.isdigit())
		self.assertGreaterEqual(int(doc.name), expected)

	def test_next_code_ignores_non_numeric_names(self):
		self._item("ZZZ-NON-NUMERIC-" + frappe.generate_hash(length=6).upper())
		# The old version read the most recently created item and gave up when
		# its name was not a number.
		self.assertIsInstance(_next_numeric_code(), int)

	def test_disabled_setting_leaves_naming_alone(self):
		_settings(enable_item_numeric_autoname=0)
		code = "MANUAL-" + frappe.generate_hash(length=6).upper()
		self.assertEqual(self._item(code).name, code)
