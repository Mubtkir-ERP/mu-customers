frappe.ui.form.on("Sales Invoice", {
	onload: function (frm) {
		if (frm.is_new()) {
			if (frm.fields_dict && frm.fields_dict.mode_of_payment) {
				frm.set_value("mode_of_payment", __("Cash")); // أو "نقد" حسب ما هو موجود
			}
		}
	},
});
