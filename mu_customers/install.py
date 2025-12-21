import frappe


def delete_default_warehouse_from_invoices():
	frappe.delete_doc_if_exists("Property Setter", "Sales Order-set_warehouse-default")
	frappe.delete_doc_if_exists("Property Setter", "Sales Invoice-set_warehouse-default")
	frappe.delete_doc_if_exists("Property Setter", "Purchase Invoice-set_warehouse-default")
	frappe.delete_doc_if_exists("Property Setter", "Delivery Note-set_warehouse-default")
	frappe.delete_doc_if_exists("Property Setter", "Purchase Receipt-set_warehouse-default")
	frappe.delete_doc_if_exists("Property Setter", "Purchase Order-set_warehouse-default")
