"""The Price Type dropdown only appears when there is a choice to make.

A row whose item has one price or none has nothing to pick between, so the
field hides itself and the single price is applied on its own. These cover the
endpoint that feeds that decision, and the wiring that acts on it.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from mu_customers.mu_customers.doctype.item_prices.item_prices import get_price_options

# Grids with no spare column unit: the field lives in the expanded row only.
FULL_GRIDS = ("Delivery Note Item", "Purchase Order Item")

ITEM_ROW_DOCTYPES = (
	"Sales Invoice Item",
	"Sales Order Item",
	"Delivery Note Item",
	"Quotation Item",
	"Purchase Invoice Item",
	"Purchase Order Item",
	"Purchase Receipt Item",
)

MANY = "_MU Many Prices"
ONE = "_MU One Price"
NONE_ = "_MU No Prices"
DISABLED = "_MU Prices Off"
RETAIL = "_MU Retail"
WHOLESALE = "_MU Wholesale"


def drop(doctype, name):
	if frappe.db.exists(doctype, name):
		frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)


def make_item(name, rows, enabled=1):
	drop("Item", name)
	item = frappe.get_doc({
		"doctype": "Item",
		"item_code": name,
		"item_name": name,
		"item_group": frappe.db.get_value("Item Group", {"is_group": 0}, "name"),
		"stock_uom": "Nos",
		"is_stock_item": 0,
		"custom_prices_enabled": enabled,
	})
	for row in rows:
		item.append("custom_item_prices", row)
	return item.insert()


class TestPriceOptionCounts(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for price_type in (RETAIL, WHOLESALE):
			if not frappe.db.exists("Item Price Type", price_type):
				frappe.get_doc({"doctype": "Item Price Type", "price_type": price_type}).insert()

		make_item(MANY, [
			{"type": "Selling", "price_type": RETAIL, "uom": "Nos", "price": 10},
			{"type": "Selling", "price_type": WHOLESALE, "uom": "Box", "price": 80},
		])
		make_item(ONE, [{"type": "Selling", "price_type": RETAIL, "uom": "Nos", "price": 25}])
		make_item(NONE_, [])
		make_item(DISABLED, [
			{"type": "Selling", "price_type": RETAIL, "uom": "Nos", "price": 10},
			{"type": "Selling", "price_type": WHOLESALE, "uom": "Box", "price": 80},
		], enabled=0)

	@classmethod
	def tearDownClass(cls):
		for name in (MANY, ONE, NONE_, DISABLED):
			drop("Item", name)
		super().tearDownClass()

	def options(self, *item_codes, direction="Selling"):
		return get_price_options(list(item_codes), direction)

	def test_two_prices_offer_a_choice(self):
		self.assertEqual(self.options(MANY)[MANY]["count"], 2)

	def test_a_single_price_is_not_a_choice(self):
		entry = self.options(ONE)[ONE]
		self.assertEqual(entry["count"], 1)
		self.assertIsNotNone(entry["only"], "the single price must come back so it can be applied")
		self.assertEqual(entry["only"]["price"], 25)

	def test_no_prices_offers_nothing(self):
		entry = self.options(NONE_)[NONE_]
		self.assertEqual(entry["count"], 0)
		self.assertIsNone(entry["only"])

	def test_an_item_with_prices_switched_off_offers_nothing(self):
		self.assertEqual(self.options(DISABLED)[DISABLED]["count"], 0)

	def test_the_choice_is_counted_per_direction(self):
		"""Two selling prices is a choice; the same item may have no buying ones."""
		self.assertEqual(self.options(MANY, direction="Selling")[MANY]["count"], 2)
		self.assertEqual(self.options(MANY, direction="Buying")[MANY]["count"], 0)

	def test_many_items_come_back_in_one_call(self):
		"""Reopening a saved document must not cost a round trip per line."""
		result = self.options(MANY, ONE, NONE_)
		self.assertEqual(
			{code: entry["count"] for code, entry in result.items()},
			{MANY: 2, ONE: 1, NONE_: 0},
		)

	def test_an_unknown_item_is_reported_as_empty(self):
		self.assertEqual(self.options("_MU Does Not Exist")["_MU Does Not Exist"]["count"], 0)

	def test_no_items_is_not_an_error(self):
		self.assertEqual(get_price_options([], "Selling"), {})

	def test_an_invalid_direction_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			get_price_options([MANY], "Sideways")


class TestDropdownVisibilityWiring(FrappeTestCase):
	def test_every_row_carries_the_count_field(self):
		for doctype in ITEM_ROW_DOCTYPES:
			with self.subTest(doctype=doctype):
				field = frappe.get_meta(doctype).get_field("custom_price_options")
				self.assertIsNotNone(field, f"{doctype} has no price option count")
				self.assertEqual(field.fieldtype, "Int")
				self.assertTrue(field.hidden, "the count is bookkeeping, not for the user")

	def test_the_dropdown_depends_on_having_more_than_one(self):
		for doctype in ITEM_ROW_DOCTYPES:
			with self.subTest(doctype=doctype):
				depends_on = frappe.get_meta(doctype).get_field("custom_item_price_type").depends_on
				self.assertEqual(depends_on, "eval:doc.custom_price_options > 1")

	def test_the_retired_row_flag_is_gone(self):
		for doctype in ITEM_ROW_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertFalse(
					frappe.db.exists("Custom Field", f"{doctype}-custom_prices_enabled"),
					f"{doctype} still carries the old prices flag",
				)

	def test_the_item_level_flag_survives(self):
		"""It still gates the feature on the Item itself - only the row copy went."""
		self.assertIsNotNone(frappe.get_meta("Item").get_field("custom_prices_enabled"))

	def test_the_column_is_in_the_grid_where_the_grid_can_afford_it(self):
		"""Two grids are full: showing the column there would cost a standard
		column, so on those it lives in the expanded row only."""
		for doctype in ITEM_ROW_DOCTYPES:
			with self.subTest(doctype=doctype):
				field = frappe.get_meta(doctype).get_field("custom_item_price_type")
				expected = 0 if doctype in FULL_GRIDS else 1
				self.assertEqual(field.in_list_view, expected)

	def test_the_field_is_reachable_on_every_doctype(self):
		"""Even where the grid cannot show it, the expanded row must."""
		for doctype in ITEM_ROW_DOCTYPES:
			with self.subTest(doctype=doctype):
				field = frappe.get_meta(doctype).get_field("custom_item_price_type")
				self.assertIsNotNone(field)
				self.assertFalse(field.hidden, "the field is hidden outright")

	def script_source(self):
		import os

		import mu_customers

		path = os.path.join(
			os.path.dirname(mu_customers.__file__), "public", "js", "item_prices_select.js"
		)
		return [line.split("//")[0] for line in open(path).read().splitlines()]

	def test_the_script_leaves_the_layout_to_the_fixtures(self):
		"""Width and placement are declared. An earlier version rewrote the
		shared docfield in the browser, which only worked where the script
		arrived intact and left the field hidden where it did not."""
		code = "\n".join(self.script_source())
		for symbol in ("set_column_disp", "in_list_view =", "columns =", "setup_visible_columns"):
			with self.subTest(symbol=symbol):
				self.assertNotIn(symbol, code, f"the script is still adjusting {symbol}")

	def test_the_script_recounts_every_row_on_open(self):
		"""An Int column reads back as 0, which cannot be told apart from 'no
		prices', so skipping rows that already have a value left saved
		documents stuck with the dropdown hidden."""
		code = "\n".join(self.script_source())
		self.assertIn("filter((row) => row.item_code)", code)


class TestPriceOptionPermissions(FrappeTestCase):
	PROBE = "_mu_options_probe@example.com"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
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
		super().tearDownClass()

	def test_it_refuses_a_user_without_item_access(self):
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(self.PROBE)
		with self.assertRaises(frappe.PermissionError):
			get_price_options(["anything"], "Selling")


class TestGridColumnBudget(FrappeTestCase):
	"""A Frappe grid has a fixed budget of column units.

	setup_visible_columns adds up colsize and stops at the first column that
	takes the running total past 11 - it drops that column and every one after
	it rather than shrinking anything. So an extra custom column does not make
	the grid tighter, it costs the document a standard column. Adding Price
	Type cost the Sales Invoice its Amount column until the script started
	borrowing a unit from Item.
	"""

	BUDGET = 11
	START = 1  # setup_visible_columns seeds total_colsize at 1
	DEFAULT_SIZE = 2  # update_default_colsize, for a field with no columns set

	def visible(self, doctype):
		"""Replay the layout rule and report what survives."""
		kept, dropped = [], []
		total, stopped = self.START, False

		for field in frappe.get_meta(doctype).fields:
			if not field.in_list_view or field.hidden:
				continue

			size = field.columns or self.DEFAULT_SIZE

			if stopped:
				dropped.append(field.fieldname)
				continue

			total += size
			if total > self.BUDGET:
				dropped.append(field.fieldname)
				stopped = True
				continue
			kept.append(field.fieldname)

		return kept, dropped

	def test_the_price_column_costs_one_unit_at_most(self):
		for doctype in ITEM_ROW_DOCTYPES:
			with self.subTest(doctype=doctype):
				columns = frappe.get_meta(doctype).get_field("custom_item_price_type").columns
				self.assertEqual(columns, 1, "the price column is wider than one unit")

	def test_it_sits_between_quantity_and_rate(self):
		for doctype in ITEM_ROW_DOCTYPES:
			if doctype in FULL_GRIDS:
				continue
			with self.subTest(doctype=doctype):
				grid = [
					f.fieldname
					for f in frappe.get_meta(doctype).fields
					if f.in_list_view and not f.hidden
				]
				self.assertLess(grid.index("qty"), grid.index("custom_item_price_type"))
				self.assertLess(grid.index("custom_item_price_type"), grid.index("rate"))

	def test_no_grid_loses_a_column_it_used_to_show(self):
		"""The regression this guards: adding Price Type to a full grid pushed
		Amount off the Sales Invoice entirely."""
		for doctype in ITEM_ROW_DOCTYPES:
			with self.subTest(doctype=doctype):
				kept, _ = self.visible(doctype)
				for fieldname in ("item_code", "qty", "rate", "amount"):
					self.assertIn(
						fieldname,
						kept,
						f"{doctype} lost its {fieldname} column",
					)

	def test_the_full_grids_keep_the_column_out(self):
		"""Delivery Note and Purchase Order cannot spare a unit, so the column
		must not be declared for their grids."""
		for doctype in FULL_GRIDS:
			with self.subTest(doctype=doctype):
				self.assertFalse(
					frappe.get_meta(doctype).get_field("custom_item_price_type").in_list_view
				)
