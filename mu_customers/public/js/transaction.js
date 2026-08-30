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

MU_TXN_DOCTYPES.forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		refresh: mu_show_net_total,
		currency: mu_show_net_total,
		company: mu_show_net_total,
	});
});
