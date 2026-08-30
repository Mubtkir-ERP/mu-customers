// Restrict the Branch field to the branches configured on the selected customer.
//
// Rewritten: the previous version called frappe.dom.freeze() and only released
// it inside .then(), so any failed fetch left the screen frozen with no way
// out; and it registered set_query inside the customer handler, so opening a
// saved document applied no filter at all.

const MU_BRANCH_DOCTYPES = ["Sales Invoice", "Sales Order", "Delivery Note"];

function mu_load_customer_branches(frm) {
	if (!frm.doc.customer) {
		frm.__mu_branches = [];
		frm.__mu_branches_for = null;
		return Promise.resolve([]);
	}

	if (frm.__mu_branches_for === frm.doc.customer) {
		return Promise.resolve(frm.__mu_branches || []);
	}

	return frappe
		.call({
			method: "mu_customers.api.get_customer_branches",
			args: { customer: frm.doc.customer },
		})
		.then((r) => {
			frm.__mu_branches = ((r && r.message) || []).filter(Boolean);
			frm.__mu_branches_for = frm.doc.customer;
			return frm.__mu_branches;
		})
		.catch(() => {
			// Never leave the form in a half-applied state: fall back to "no
			// restriction" and let the user carry on.
			frm.__mu_branches = [];
			frm.__mu_branches_for = null;
			return [];
		});
}

MU_BRANCH_DOCTYPES.forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		setup(frm) {
			// Registered once, reads the cached list at query time - so it
			// applies on saved documents too, not only after changing customer.
			frm.set_query("custom_branch", () => {
				const branches = frm.__mu_branches || [];
				return { filters: { name: ["in", branches.length ? branches : [""]] } };
			});
		},

		refresh(frm) {
			mu_load_customer_branches(frm);
		},

		customer(frm) {
			frm.__mu_branches_for = null;
			if (frm.doc.custom_branch) {
				frm.set_value("custom_branch", "");
			}
			mu_load_customer_branches(frm).then((branches) => {
				frm.set_value("custom_has_branches", branches.length ? 1 : 0);
			});
		},
	});
});
