frappe.ui.form.on("Payment Entry", {
	paid_from_account_type: function (frm) {
		frm.events.set_default_value_for_reference_no(frm);
	},
	paid_to_account_type: function (frm) {
		frm.events.set_default_value_for_reference_no(frm);
	},
	set_default_value_for_reference_no: function (frm) {
		if (
			frm.is_new() &&
			(frm.doc.paid_from_account_type === "Bank" || frm.doc.paid_to_account_type === "Bank")
		) {
			frm.set_value("reference_no", "00");
		}
	},
});
