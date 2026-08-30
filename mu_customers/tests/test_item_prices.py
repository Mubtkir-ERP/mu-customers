"""Tests for the item price dropdown that replaced the price popup.

The dropdown is a Link filtered per row by a server query, so the query and the
price lookup behind it carry the correctness that used to live in the dialog:
each row must offer only its own item's types for the right direction, and both
endpoints are reachable over HTTP so both must check permissions.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from mu_customers.mu_customers.doctype.item_prices.item_prices import (
	get_price_for_type,
	price_type_query,
)

ITEM_ROW_DOCTYPES = (
	"Sales Invoice Item",
	"Sales Order Item",
	"Delivery Note Item",
	"Quotation Item",
	"Purchase Invoice Item",
	"Purchase Order Item",
	"Purchase Receipt Item",
)

PRICED_ITEM = "_MU Dropdown Item"
PLAIN_ITEM = "_MU Plain Item"
RETAIL = "_MU Retail"
WHOLESALE = "_MU Wholesale"


def options(item_code, invoice_type, txt=""):
	return [
		row[0]
		for row in price_type_query(
			"Item Price Type",
			txt,
			"name",
			0,
			20,
			{"item_code": item_code, "invoice_type": invoice_type},
		)
	]


def drop(doctype, name):
	if frappe.db.exists(doctype, name):
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)


def make_items():
	"""One item with prices in both directions, one with none at all."""
	for name in (PRICED_ITEM, PLAIN_ITEM):
		drop("Item", name)

	group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")

	for price_type in (RETAIL, WHOLESALE):
		if not frappe.db.exists("Item Price Type", price_type):
			frappe.get_doc({"doctype": "Item Price Type", "price_type": price_type}).insert()

	priced = frappe.get_doc({
		"doctype": "Item",
		"item_code": PRICED_ITEM,
		"item_name": PRICED_ITEM,
		"item_group": group,
		"stock_uom": "Nos",
		"is_stock_item": 0,
		"custom_prices_enabled": 1,
	})
	for row in (
		{"type": "Selling", "price_type": RETAIL, "uom": "Nos", "price": 10},
		{"type": "Selling", "price_type": RETAIL, "uom": "Box", "price": 90},
		{"type": "Selling", "price_type": WHOLESALE, "uom": "Box", "price": 80},
		{"type": "Buying", "price_type": WHOLESALE, "uom": "Box", "price": 60},
	):
		priced.append("custom_item_prices", row)
	priced.insert()

	frappe.get_doc({
		"doctype": "Item",
		"item_code": PLAIN_ITEM,
		"item_name": PLAIN_ITEM,
		"item_group": group,
		"stock_uom": "Nos",
		"is_stock_item": 0,
	}).insert()


class TestPriceDropdownFields(FrappeTestCase):
	"""The dropdown replaces the button, on every transaction row doctype."""

	def test_dropdown_exists_on_every_transaction_row(self):
		"""Present everywhere. Whether it also gets a grid column depends on
		whether that grid has a column unit to spare - see
		TestGridColumnBudget in test_price_options."""
		for doctype in ITEM_ROW_DOCTYPES:
			with self.subTest(doctype=doctype):
				field = frappe.get_meta(doctype).get_field("custom_item_price_type")
				self.assertIsNotNone(field, f"{doctype} has no price dropdown")
				self.assertEqual(field.fieldtype, "Link")
				self.assertEqual(field.options, "Item Price Type")
				self.assertFalse(field.hidden, "the dropdown is hidden outright")

	def test_retired_price_button_is_gone(self):
		for doctype in ITEM_ROW_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertFalse(
					frappe.db.exists("Custom Field", f"{doctype}-custom_select_price"),
					f"{doctype} still carries the old Select Price button",
				)

	def test_dropdown_hides_itself_unless_there_is_a_choice(self):
		"""One price or none is not a choice, so the row stays uncluttered.

		The count lives on the row because depends_on is evaluated per row
		against that row's own document.
		"""
		for doctype in ITEM_ROW_DOCTYPES:
			with self.subTest(doctype=doctype):
				meta = frappe.get_meta(doctype)
				self.assertEqual(meta.get_field("custom_price_options").fieldtype, "Int")
				self.assertEqual(
					meta.get_field("custom_item_price_type").depends_on,
					"eval:doc.custom_price_options > 1",
				)


class TestPriceDropdown(FrappeTestCase):
	"""Options offered, and the price each option resolves to."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_items()

	@classmethod
	def tearDownClass(cls):
		for name in (PRICED_ITEM, PLAIN_ITEM):
			drop("Item", name)
		super().tearDownClass()

	# ---- options -----------------------------------------------------------

	def test_options_are_scoped_to_the_selling_or_buying_direction(self):
		self.assertEqual(sorted(options(PRICED_ITEM, "Selling")), sorted([RETAIL, WHOLESALE]))
		self.assertEqual(options(PRICED_ITEM, "Buying"), [WHOLESALE])

	def test_options_are_deduplicated_across_uoms(self):
		# Retail is configured twice, in Nos and in Box; the dropdown lists it once.
		self.assertEqual(options(PRICED_ITEM, "Selling").count(RETAIL), 1)

	def test_options_are_empty_for_an_item_without_prices(self):
		self.assertEqual(options(PLAIN_ITEM, "Selling"), [])

	def test_options_honour_the_search_text(self):
		self.assertEqual(options(PRICED_ITEM, "Selling", "Retail"), [RETAIL])

	def test_unknown_direction_yields_nothing(self):
		self.assertEqual(options(PRICED_ITEM, "Nonsense"), [])

	def test_missing_item_yields_nothing(self):
		self.assertEqual(options("", "Selling"), [])

	# ---- price lookup ------------------------------------------------------

	def test_lookup_returns_the_configured_price(self):
		self.assertEqual(get_price_for_type(PRICED_ITEM, "Selling", WHOLESALE).price, 80)

	def test_same_type_prices_differ_by_direction(self):
		self.assertEqual(get_price_for_type(PRICED_ITEM, "Buying", WHOLESALE).price, 60)

	def test_lookup_prefers_a_row_in_the_current_uom(self):
		self.assertEqual(get_price_for_type(PRICED_ITEM, "Selling", RETAIL, uom="Box").price, 90)
		self.assertEqual(get_price_for_type(PRICED_ITEM, "Selling", RETAIL, uom="Nos").price, 10)

	def test_lookup_falls_back_when_the_uom_has_no_row(self):
		self.assertEqual(get_price_for_type(PRICED_ITEM, "Selling", RETAIL, uom="Kg").price, 10)

	def test_unknown_type_returns_nothing_rather_than_a_wrong_price(self):
		self.assertIsNone(get_price_for_type(PRICED_ITEM, "Selling", "_MU Nonexistent"))

	def test_item_without_prices_returns_nothing(self):
		self.assertIsNone(get_price_for_type(PLAIN_ITEM, "Selling", RETAIL))

	def test_invalid_direction_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			get_price_for_type(PRICED_ITEM, "Sideways", RETAIL)


class TestPriceEndpointPermissions(FrappeTestCase):
	"""Both endpoints are whitelisted, so both must check Item read access."""

	PROBE = "_mu_price_probe@example.com"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_items()
		if not frappe.db.exists("User", cls.PROBE):
			user = frappe.get_doc({
				"doctype": "User",
				"email": cls.PROBE,
				"first_name": "Probe",
				"send_welcome_email": 0,
			}).insert(ignore_permissions=True)
			user.set("roles", [])
			user.save(ignore_permissions=True)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		drop("User", cls.PROBE)
		for name in (PRICED_ITEM, PLAIN_ITEM):
			drop("Item", name)
		super().tearDownClass()

	def setUp(self):
		self.addCleanup(frappe.set_user, "Administrator")

	def test_dropdown_query_refuses_a_user_without_item_access(self):
		frappe.set_user(self.PROBE)
		with self.assertRaises(frappe.PermissionError):
			price_type_query(
				"Item Price Type", "", "name", 0, 20,
				{"item_code": PRICED_ITEM, "invoice_type": "Selling"},
			)

	def test_price_lookup_refuses_a_user_without_item_access(self):
		frappe.set_user(self.PROBE)
		with self.assertRaises(frappe.PermissionError):
			get_price_for_type(PRICED_ITEM, "Selling", RETAIL)
