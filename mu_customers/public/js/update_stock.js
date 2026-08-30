// Update Stock on Sales and Purchase Invoices.
//
// A new invoice always opens with the box ticked (a Property Setter supplies
// the default). Extra Features Settings decides whether it can then be cleared:
//
//   force_update_stock = 1  ->  read-only, so every invoice moves stock
//   force_update_stock = 0  ->  editable, so a service invoice can untick it
//
// Note this locks the field in the form. It is not a server-side constraint:
// an import or an API call can still write update_stock = 0.

const MU_UPDATE_STOCK_DOCTYPES = ["Sales Invoice", "Purchase Invoice"];

let mu_force_update_stock = null;

function mu_is_update_stock_forced() {
	if (mu_force_update_stock !== null) {
		return Promise.resolve(mu_force_update_stock);
	}
	return frappe.db
		.get_single_value("Extra Features Settings", "force_update_stock")
		.then((value) => {
			mu_force_update_stock = !!value;
			return mu_force_update_stock;
		})
		.catch(() => false);
}

function mu_apply_update_stock_lock(frm) {
	return mu_is_update_stock_forced().then((forced) => {
		frm.set_df_property("update_stock", "read_only", forced ? 1 : 0);

		// Only ever tick it on a document that has not been saved: silently
		// flipping the flag on someone's existing draft would change what that
		// invoice does to stock without them touching it.
		if (forced && frm.is_new() && !frm.doc.update_stock) {
			frm.set_value("update_stock", 1);
		}
	});
}

MU_UPDATE_STOCK_DOCTYPES.forEach((doctype) => {
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			mu_apply_update_stock_lock(frm);
		},
	});
});
