frappe.ui.form.on(cur_frm.doc.doctype, {
	customer: function (frm) {
		frm.set_value("branch", "");
		if (frm.doc.customer) {
			frappe.dom.freeze();
			frappe.db.get_doc("Customer", frm.doc.customer).then((doc) => {
				var bq = [];
				$.each(doc.branches || [], function (i, v) {
					if (v.branch) {
						bq.push(v.branch);
					}
				});
				frm.set_query("branch", function () {
					return {
						filters: {
							name: ["in", bq],
						},
					};
				});
				frappe.dom.unfreeze();
			});
		}
	},
});
