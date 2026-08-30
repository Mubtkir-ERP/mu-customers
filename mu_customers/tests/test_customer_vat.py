"""Tax numbers on the customer: this app ships Tax ID and nothing else.

`custom_vat_registration_number` is the ZATCA VAT registration number and the
ZATCA app owns it. This app used to define it too, which meant two apps
claiming one column and two fixtures competing on every migrate. The definition
is gone - but the column and everything typed into it stay, because that data
belongs to whichever app manages the field.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

ZATCA_FIELD = "custom_vat_registration_number"
ZATCA_CF = f"Customer-{ZATCA_FIELD}"


class TestAppDoesNotClaimTheZatcaField(FrappeTestCase):
	def test_the_app_ships_no_definition_for_it(self):
		import json
		import os

		import mu_customers

		fixtures = os.path.join(os.path.dirname(mu_customers.__file__), "fixtures")

		fields = json.load(open(os.path.join(fixtures, "custom_field.json")))
		self.assertFalse(
			[r for r in fields if r.get("fieldname") == ZATCA_FIELD],
			"the app is defining the ZATCA field again",
		)

		setters = json.load(open(os.path.join(fixtures, "property_setter.json")))
		self.assertFalse(
			[r for r in setters if r.get("field_name") == ZATCA_FIELD],
			"the app is still configuring the ZATCA field",
		)

	def test_the_app_no_longer_owns_the_field_record(self):
		owner = frappe.db.get_value("Custom Field", ZATCA_CF, "module")
		self.assertNotEqual(
			owner, "Mu Customers", "the ZATCA field is owned by this app again"
		)

	def test_existing_values_are_preserved(self):
		"""Releasing the definition must never cost anyone their data."""
		if not frappe.db.has_column("Customer", ZATCA_FIELD):
			self.skipTest("no ZATCA column on this site")

		frappe.db.sql(
			f"select count(*) from `tabCustomer` where ifnull(`{ZATCA_FIELD}`, '') != ''"
		)  # must not raise: the column is still queryable


class TestTaxIdIsTheSupportedField(FrappeTestCase):
	def test_tax_id_is_present_and_writable(self):
		field = frappe.get_meta("Customer").get_field("tax_id")
		self.assertIsNotNone(field, "ERPNext's Tax ID field is missing")
		self.assertFalse(field.hidden)
		self.assertFalse(field.read_only)

	def test_tax_id_is_not_mandatory(self):
		self.assertFalse(frappe.get_meta("Customer").get_field("tax_id").reqd)

	def test_commercial_register_is_anchored_to_tax_id(self):
		"""It used to hang off the ZATCA field. A Custom Field whose
		insert_after names a missing field drops to the bottom of the form."""
		self.assertEqual(
			frappe.db.get_value("Custom Field", "Customer-custom_commercial_register_no",
								"insert_after"),
			"tax_id",
		)

	def test_commercial_register_follows_tax_id_on_the_form(self):
		order = [df.fieldname for df in frappe.get_meta("Customer").fields]
		self.assertLess(
			order.index("tax_id"),
			order.index("custom_commercial_register_no"),
			"Commercial Register No drifted above Tax ID",
		)

	def test_the_number_reaches_the_invoice(self):
		for doctype, source in (("Sales Invoice", "customer"), ("Purchase Invoice", "supplier")):
			with self.subTest(doctype=doctype):
				self.assertEqual(
					frappe.get_meta(doctype).get_field("tax_id").fetch_from,
					f"{source}.tax_id",
				)


class TestInvoiceNoteStaysUnderTheTaxNumber(FrappeTestCase):
	"""The migrated note has an agreed position and must hold it."""

	def test_remarks_follows_the_tax_number(self):
		for doctype, anchor in (("Sales Invoice", "company_tax_id"), ("Purchase Invoice", "company")):
			with self.subTest(doctype=doctype):
				order = [df.fieldname for df in frappe.get_meta(doctype).fields]
				self.assertIn("remarks", order)
				self.assertEqual(
					order[order.index(anchor) + 1],
					"remarks",
					f"remarks no longer sits directly under {anchor}",
				)

	def test_remarks_is_visible_and_prints(self):
		for doctype in ("Sales Invoice", "Purchase Invoice"):
			with self.subTest(doctype=doctype):
				field = frappe.get_meta(doctype).get_field("remarks")
				self.assertFalse(field.hidden)
				self.assertFalse(field.print_hide, "remarks would not appear on a printout")


class TestRevertedPropertySetters(FrappeTestCase):
	"""Three overrides the client asked to drop, so ERPNext's own settings win."""

	RETIRED = (
		"Payment Entry-reference_no-reqd",
		"Sales Invoice-more_information-collapsible",
		"Purchase Invoice-additional_info_section-collapsible",
	)

	def test_they_are_gone(self):
		for name in self.RETIRED:
			with self.subTest(property_setter=name):
				self.assertFalse(frappe.db.exists("Property Setter", name))

	def test_the_bank_reference_check_is_still_enforced(self):
		"""reference_no is not a mandatory *field* in ERPNext either - the rule
		lives in PaymentEntry.validate_transaction_reference, which is intact."""
		import inspect

		from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry

		source = inspect.getsource(PaymentEntry.validate_transaction_reference)
		self.assertIn("reference_no", source)
		self.assertIn("throw", source)

	def test_both_sections_are_collapsible_again(self):
		for doctype, section in (("Sales Invoice", "more_information"),
								 ("Purchase Invoice", "additional_info_section")):
			with self.subTest(doctype=doctype):
				self.assertTrue(
					frappe.get_meta(doctype).get_field(section).collapsible,
					f"{section} is not collapsible",
				)
