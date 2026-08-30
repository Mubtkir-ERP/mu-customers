# Copyright (c) 2025, Mubtkir and contributors
# For license information, please see license.txt

import frappe

from mu_customers.default_warehouse_qty import compute


def update_item_qty_on_bin_change(doc, method=None):
	"""Queue a refresh of the item's default-warehouse quantity.

	Runs in the background and de-duplicates per item, so a bulk stock entry
	or a repost queues one job per item instead of one per ledger row.
	"""
	if not doc.item_code:
		return

	frappe.enqueue(
		"mu_customers.events.stock_ledger_entry.sync_default_warehouse_qty",
		queue="short",
		enqueue_after_commit=True,
		job_id=f"mu_customers::default_warehouse_qty::{doc.item_code}",
		deduplicate=True,
		item_code=doc.item_code,
	)


def sync_default_warehouse_qty(item_code):
	"""Total actual qty across the item's default warehouses.

	Read straight from Bin - which ERPNext has already updated by the time this
	runs - rather than re-adding the ledger row on top of it.
	"""
	if not frappe.db.exists("Item", item_code):
		return

	frappe.db.set_value(
		"Item",
		item_code,
		"custom_default_warehouse_qty",
		compute(item_code)["qty"],
		update_modified=False,
	)
