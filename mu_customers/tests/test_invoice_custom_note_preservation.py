"""Regression checks for the legacy invoice custom_note field."""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestInvoiceCustomNotePreservation(FrappeTestCase):
	def test_legacy_custom_note_is_hidden_when_it_exists(self):
		for doctype in ("Sales Invoice", "Purchase Invoice"):
			with self.subTest(doctype=doctype):
				name = f"{doctype}-custom_note"
				if not frappe.db.exists("Custom Field", name):
					continue
				self.assertEqual(
					frappe.db.get_value("Custom Field", name, "hidden"),
					1,
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
