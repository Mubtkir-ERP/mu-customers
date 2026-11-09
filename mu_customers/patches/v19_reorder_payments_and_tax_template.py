"""Reorder payments, tax templates, ensure custom_note is migrated, hidden, and updated in Print Formats."""

import frappe
from mu_customers.invoice_note_position import apply, hide_custom_notes
from mu_customers.patches.migrate_custom_note_to_remarks import (
	CANDIDATES,
	overwrite_remarks_from_custom_note,
)


def update_print_formats():
	"""Replace custom_note with remarks in Print Formats for migrated doctypes."""
	if not frappe.db.table_exists("Print Format"):
		return []

	# Update all migrated doctypes, keeping Quotation untouched
	print_formats = frappe.get_all(
		"Print Format",
		filters={"doc_type": ["in", list(CANDIDATES)]},
		fields=["name", "html", "format_data", "raw_commands"],
	)

	updated = []
	for pf in print_formats:
		changed = False
		values = {}

		# 1. Custom Jinja / HTML templates
		if pf.html and "custom_note" in pf.html:
			new_html = (
				pf.html.replace("doc.custom_note", "doc.remarks")
				.replace('doc.get("custom_note")', 'doc.get("remarks")')
				.replace("doc.get('custom_note')", "doc.get('remarks')")
				.replace('doc.get_formatted("custom_note")', 'doc.get_formatted("remarks")')
				.replace("doc.get_formatted('custom_note')", "doc.get_formatted('remarks')")
				.replace("custom_note", "remarks")
			)
			if new_html != pf.html:
				values["html"] = new_html
				changed = True

		# 2. Print Format Builder JSON format_data
		if pf.format_data and "custom_note" in pf.format_data:
			new_format_data = (
				pf.format_data.replace('"fieldname": "custom_note"', '"fieldname": "remarks"')
				.replace('"fieldname":"custom_note"', '"fieldname":"remarks"')
				.replace('"custom_note"', '"remarks"')
			)
			if new_format_data != pf.format_data:
				values["format_data"] = new_format_data
				changed = True

		# 3. Raw printer commands
		if pf.raw_commands and "custom_note" in pf.raw_commands:
			new_raw = pf.raw_commands.replace("custom_note", "remarks")
			if new_raw != pf.raw_commands:
				values["raw_commands"] = new_raw
				changed = True

		if changed:
			frappe.db.set_value("Print Format", pf.name, values, update_modified=False)
			updated.append(pf.name)

	if updated:
		frappe.clear_cache(doctype="Print Format")

	return updated


def execute():
	for dt in CANDIDATES:
		overwrite_remarks_from_custom_note(dt)

	updated_pfs = update_print_formats()
	if updated_pfs:
		print(f"mu_customers: updated {len(updated_pfs)} Print Format(s) to use remarks")

	hide_custom_notes()
	moved = apply()
	if moved:
		print(f"mu_customers: layout reordered for {', '.join(moved)}")
