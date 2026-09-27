import frappe


# Legacy fields that were replaced by custom_* fields.
# We only remove the old Custom Field records.
LEGACY_FIELDS = {
    "Customer": {
        "branches": "custom_branches",
        "has_branches": "custom_has_branches",
    },
    "Sales Invoice": {
        "branch": "custom_branch",
        "has_branches": "custom_has_branches",
    },
    "Sales Order": {
        "branch": "custom_branch",
        "has_branches": "custom_has_branches",
    },
    "Delivery Note": {
        "branch": "custom_branch",
        "has_branches": "custom_has_branches",
    },
}


def execute():
    for doctype, fields in LEGACY_FIELDS.items():
        for old_field, new_field in fields.items():

            old_name = f"{doctype}-{old_field}"
            new_name = f"{doctype}-{new_field}"

            # Safety:
            # Do not delete the old field unless the replacement exists.
            if not frappe.db.exists("Custom Field", new_name):
                continue

            # Delete legacy Custom Field.
            if frappe.db.exists("Custom Field", old_name):
                frappe.delete_doc(
                    "Custom Field",
                    old_name,
                    force=True,
                    ignore_permissions=True,
                )

    frappe.clear_cache()
