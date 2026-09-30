import frappe


def execute():
    fieldname = "custom_vat_registration_number"

    custom_field_name = frappe.db.get_value(
        "Custom Field",
        {
            "dt": "Customer",
            "fieldname": fieldname
        },
        "name"
    )

    if not custom_field_name:
        return

    frappe.db.set_value(
        "Custom Field",
        custom_field_name,
        "allow_in_quick_entry",
        1,
        update_modified=False
    )

    frappe.clear_cache(doctype="Customer")
