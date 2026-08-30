// Suggest the next numeric item code on a new Item.
//
// Rewritten: the code is now derived server-side with the same MAX() logic the
// autoname hook uses, instead of reading the most recently created item in the
// browser and hoping its name happened to be numeric.

frappe.ui.form.on("Item", {
	onload(frm) {
		if (!frm.is_new() || frm.doc.item_code) {
			return;
		}

		frappe.db
			.get_single_value("Extra Features Settings", "enable_item_numeric_autoname")
			.then((enabled) => {
				if (!enabled) {
					return;
				}
				return frappe
					.call({ method: "mu_customers.api.get_next_item_code" })
					.then((r) => {
						if (r && r.message && !frm.doc.item_code) {
							frm.set_value("item_code", r.message);
						}
					});
			})
			.catch(() => {
				// A failed suggestion must never block creating an item.
			});
	},
});
