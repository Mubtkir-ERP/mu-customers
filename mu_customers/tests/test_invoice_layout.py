"""The invoice note has to stay directly under the tax number.

Staff read and write it there. It drifted to the end of the form once already,
when custom_note was migrated into the standard `remarks` field. The legacy
custom_note value is preserved separately but hidden from the invoice form.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from mu_customers.invoice_note_position import NOTE_ANCHOR, order_with_note_after_anchor


class TestInvoiceNotePosition(FrappeTestCase):
	def order(self, doctype):
		return [df.fieldname for df in frappe.get_meta(doctype).fields]

	def test_note_sits_directly_under_the_tax_number(self):
		for doctype, anchor in NOTE_ANCHOR.items():
			with self.subTest(doctype=doctype):
				order = self.order(doctype)
				self.assertIn(anchor, order)
				self.assertEqual(
					order[order.index(anchor) + 1],
					"remarks",
					f"{doctype}: the note is no longer under {anchor}",
				)

	def test_note_is_visible_and_writable(self):
		for doctype in NOTE_ANCHOR:
			with self.subTest(doctype=doctype):
				field = frappe.get_meta(doctype).get_field("remarks")
				self.assertFalse(field.hidden, "the note box is hidden")
				self.assertFalse(field.read_only, "the note box is read-only")
				self.assertFalse(field.print_hide, "the note is hidden from print")

	def test_helper_moves_the_field_without_losing_any(self):
		for doctype, anchor in NOTE_ANCHOR.items():
			with self.subTest(doctype=doctype):
				before = set(self.order(doctype))
				after = order_with_note_after_anchor(doctype, anchor)
				self.assertEqual(before, set(after), "the reorder dropped or added a field")
				self.assertEqual(len(after), len(set(after)), "the reorder duplicated a field")

	def test_taxes_and_charges_sits_above_base_total(self):
		from mu_customers.invoice_note_position import ALL_TARGET_DOCTYPES, reorder_fields

		for doctype in ALL_TARGET_DOCTYPES:
			if not frappe.db.exists("DocType", doctype):
				continue
			order = self.order(doctype)
			if "taxes_and_charges" in order and "base_total" in order:
				with self.subTest(doctype=doctype):
					reordered = reorder_fields(list(order), doctype)
					self.assertEqual(
						reordered[reordered.index("base_total") - 1],
						"taxes_and_charges",
						f"{doctype}: taxes_and_charges must sit directly above base_total",
					)
					if "column_break_32" in reordered:
						self.assertLess(
							reordered.index("column_break_32"),
							reordered.index("taxes_and_charges"),
						)

	def test_payments_and_paid_amount_positions(self):
		from mu_customers.invoice_note_position import ALL_TARGET_DOCTYPES, reorder_fields

		for doctype in ALL_TARGET_DOCTYPES:
			if not frappe.db.exists("DocType", doctype):
				continue
			order = self.order(doctype)
			reordered = reorder_fields(list(order), doctype)
			if "payments" in order and "items" in order:
				with self.subTest(doctype=doctype, field="payments"):
					self.assertEqual(
						reordered[reordered.index("items") + 1],
						"payments",
						f"{doctype}: payments table must sit directly under items table",
					)
			if "paid_amount" in order and "grand_total" in order:
				with self.subTest(doctype=doctype, field="paid_amount"):
					self.assertEqual(
						reordered[reordered.index("grand_total") + 1],
						"paid_amount",
						f"{doctype}: paid_amount must sit directly under grand_total",
					)


class TestBranchFieldsSurviveTheReorder(FrappeTestCase):
	"""The reorder must not disturb what earlier rounds put on these forms."""

	def test_branch_fields_are_still_present(self):
		for doctype in ("Sales Invoice", "Sales Order", "Delivery Note"):
			with self.subTest(doctype=doctype):
				meta = frappe.get_meta(doctype)
				self.assertIsNotNone(meta.get_field("custom_branch"))
				self.assertIsNotNone(meta.get_field("custom_has_branches"))

	def test_branch_still_sits_beside_the_customer(self):
		order = [df.fieldname for df in frappe.get_meta("Sales Invoice").fields]
		self.assertLess(
			order.index("custom_branch"),
			order.index("posting_date"),
			"the branch field slid past the posting date",
		)

	def test_price_dropdown_survived_on_the_item_rows(self):
		field = frappe.get_meta("Sales Invoice Item").get_field("custom_item_price_type")
		self.assertIsNotNone(field)
		self.assertTrue(field.in_list_view)

	def test_tax_number_is_still_in_place(self):
		for doctype in ("Sales Invoice", "Purchase Invoice"):
			with self.subTest(doctype=doctype):
				field = frappe.get_meta(doctype).get_field("tax_id")
				self.assertIsNotNone(field, "the tax number field is gone")
				self.assertFalse(field.hidden, "the tax number field is hidden")
