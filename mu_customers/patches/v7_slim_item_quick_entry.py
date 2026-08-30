"""Get the Item quick entry dialog back under Frappe's field limit.

Frappe abandons the quick entry dialog and opens the full form once more than
seven fields qualify (reqd or allow_in_quick_entry - see
QuickEntryForm.too_many_mandatory_fields). Item had nine, so the dialog never
appeared at all.

Dropping standard_rate and valuation_rate - both pushed in by this app - brings
it to seven, which is what lets Item Code join the dialog and the dialog itself
come back.
"""

import frappe

RETIRED_PROPERTY_SETTERS = (
	"Item-standard_rate-allow_in_quick_entry",
	"Item-valuation_rate-allow_in_quick_entry",
)


def execute():
	removed = []

	for name in RETIRED_PROPERTY_SETTERS:
		if frappe.db.exists("Property Setter", name):
			frappe.delete_doc("Property Setter", name, ignore_permissions=True, force=True)
			removed.append(name)

	if removed:
		frappe.clear_cache(doctype="Item")
		print(f"mu_customers: removed {len(removed)} Item quick entry field(s): {removed}")
