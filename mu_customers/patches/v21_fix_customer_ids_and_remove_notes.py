"""Keep custom_additional_ids inside Customer IDs section and remove any extra notes custom fields."""

import frappe
from mu_customers.invoice_note_position import (
	apply,
	remove_extra_notes_fields,
	reorder_customer_fields,
	setup_customer_collapsible_sections,
)


def execute():
	remove_extra_notes_fields()
	reorder_customer_fields()
	setup_customer_collapsible_sections()
	apply()
	frappe.clear_cache()
