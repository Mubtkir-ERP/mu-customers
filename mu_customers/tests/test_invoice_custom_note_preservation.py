"""Regression checks for the legacy invoice custom_note field."""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestInvoiceCustomNotePreservation(FrappeTestCase):
	def test_legacy_custom_note_is_hidden_when_it_exists(self):
		for doctype in (
			"Sales Invoice",
			"Purchase Invoice",
			"Sales Order",
			"Purchase Order",
		):
			with self.subTest(doctype=doctype):
				name = f"{doctype}-custom_note"
				if not frappe.db.exists("Custom Field", name):
					continue
				self.assertEqual(
					frappe.db.get_value("Custom Field", name, "hidden"),
					1,
				)

		# Quotation note must remain visible
		if frappe.db.exists("Custom Field", "Quotation-custom_note"):
			self.assertEqual(
				frappe.db.get_value("Custom Field", "Quotation-custom_note", "hidden"),
				0,
			)

	def test_fixtures_have_all_custom_notes_hidden_except_quotation(self):
		import json
		import os

		import mu_customers

		fixtures_path = os.path.join(
			os.path.dirname(mu_customers.__file__), "fixtures", "custom_field.json"
		)
		with open(fixtures_path, encoding="utf-8") as f:
			fields = json.load(f)

		custom_notes = [f for f in fields if f.get("fieldname") == "custom_note"]
		self.assertTrue(custom_notes, "No custom_note found in fixtures/custom_field.json")
		for field in custom_notes:
			expected = 0 if field.get("dt") == "Quotation" else 1
			self.assertEqual(
				field.get("hidden"),
				expected,
				f"{field.get('name')} hidden state mismatch in fixtures/custom_field.json",
			)

	def test_legacy_column_is_not_required_to_be_removed(self):
		# The app must be safe whether an older release already removed the
		# column or whether historical data is still present in it.
		for doctype in ("Sales Invoice", "Purchase Invoice"):
			with self.subTest(doctype=doctype):
				frappe.db.table_exists(doctype)  # must not raise


class TestCustomNoteMigrationContract(FrappeTestCase):
	def test_custom_note_migration_helper_is_available(self):
		from mu_customers.patches.migrate_custom_note_to_remarks import (
			overwrite_remarks_from_custom_note,
		)

		self.assertTrue(callable(overwrite_remarks_from_custom_note))
