"""Move has_variants and is_fixed_asset directly under is_stock_item on Item."""

import frappe
from mu_customers.invoice_note_position import reorder_item_fields


def execute():
	reorder_item_fields()
	frappe.clear_cache(doctype="Item")
