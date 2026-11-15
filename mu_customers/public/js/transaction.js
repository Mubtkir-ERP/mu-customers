// Keep Net Total visible on transaction forms.
//
// Rewritten: the previous version replaced
// erpnext.TransactionController.prototype.change_form_labels wholesale from
// app_include_js - a full copy of an ERPNext core method, loaded on every desk
// page, that would silently revert any upstream change to it. The only actual
// behaviour it added was forcing net_total to display, which is all this does.

const MU_TXN_DOCTYPES = [
	"Sales Invoice",
	"Sales Order",
	"Delivery Note",
	"Quotation",
	"Purchase Invoice",
	"Purchase Order",
	"Purchase Receipt",
	"Supplier Quotation",
];

function mu_show_net_total(frm) {
	if (frappe.meta.get_docfield(frm.doc.doctype, "net_total")) {
		frm.toggle_display("net_total", true);
	}

	const company_currency = frappe.get_doc(":Company", frm.doc.company)?.default_currency;
	if (frappe.meta.get_docfield(frm.doc.doctype, "base_net_total")) {
		frm.toggle_display(
			"base_net_total",
			Boolean(company_currency) && frm.doc.currency !== company_currency
		);
	}
}

function mu_clear_default_remarks(frm) {
	if (!frm || !frm.doc) return;

	const raw = frm.doc.remarks;
	if (!raw) return;

	const val = String(raw).trim().replace(/[.:]$/, "");
	const is_default = (
		val.toLowerCase() === "no remarks" ||
		val === "لا ملاحظات" ||
		val === "لا توجد ملاحظات" ||
		val === __("No Remarks") ||
		val === __("No remarks")
	);

	if (is_default) {
		frm.doc.remarks = "";
		if (frm.is_new() && frm.doc.docstatus === 0) {
			frm.refresh_field("remarks");
		} else if (frm.fields_dict.remarks && frm.fields_dict.remarks.set_input) {
			// Clears the input in the DOM without triggering frm.dirty() or CannotChangeAfterSubmit
			frm.fields_dict.remarks.set_input("");
		}
	}
}

function mu_fetch_vat_from_customer(frm) {
	if (frm.doc.customer && frm.fields_dict.tax_id) {
		frappe.db.get_value("Customer", frm.doc.customer, "custom_vat_registration_number", function (r) {
			if (r && r.custom_vat_registration_number) {
				frm.set_value("tax_id", r.custom_vat_registration_number);
			}
		});
	}
}

const SELLING_DOCTYPES = [
	"Sales Invoice",
	"Sales Order",
	"Delivery Note",
	"Quotation",
];

MU_TXN_DOCTYPES.forEach((doctype) => {
	const handlers = {
		onload: mu_clear_default_remarks,
		refresh(frm) {
			mu_show_net_total(frm);
			mu_clear_default_remarks(frm);
		},
		currency: mu_show_net_total,
		company: mu_show_net_total,
	};

	if (SELLING_DOCTYPES.includes(doctype)) {
		handlers.customer = mu_fetch_vat_from_customer;
	}

	frappe.ui.form.on(doctype, handlers);
});
