"""Apply sales document tax customizations, customer layout reordering, collapsible sections, and database remarks cleanup."""

import frappe
from mu_customers.invoice_note_position import (
	apply,
	hide_custom_notes,
	reorder_customer_fields,
	setup_customer_collapsible_sections,
	setup_sales_customizations,
)

TRANSACTION_DOCTYPES = (
	"Sales Invoice",
	"Purchase Invoice",
	"Sales Order",
	"Purchase Order",
	"Delivery Note",
	"Purchase Receipt",
	"Quotation",
	"Supplier Quotation",
)


def clear_default_remarks_in_db():
	"""Clear legacy default remarks ('No Remarks', 'لا ملاحظات') from database."""
	for dt in TRANSACTION_DOCTYPES:
		if not frappe.db.table_exists(dt) or not frappe.db.has_column(dt, "remarks"):
			continue
		frappe.db.sql(
			f"""
			UPDATE `tab{dt}`
			SET remarks = NULL
			WHERE TRIM(LOWER(REPLACE(REPLACE(remarks, '.', ''), ':', ''))) IN ('no remarks', 'لا ملاحظات', 'لا توجد ملاحظات')
			"""
		)


def execute():
	clear_default_remarks_in_db()
	setup_sales_customizations()
	reorder_customer_fields()
	setup_customer_collapsible_sections()
	hide_custom_notes()
	apply()
	frappe.clear_cache()
