// Show the next item code in the Item quick entry dialog.
//
// With the numeric series on, the code was only assigned during autoname - so
// the employee typed the whole item blind and only saw the number after saving.
// The next free number is fetched as the dialog opens instead.
//
// Item has no quick entry controller of its own in Frappe or ERPNext, so this
// defines one rather than replacing anything.

frappe.provide("frappe.ui.form");

frappe.ui.form.ItemQuickEntryForm = class MuItemQuickEntryForm extends frappe.ui.form
	.QuickEntryForm {
	render_dialog() {
		super.render_dialog();
		this.prefill_numeric_item_code();
	}

	prefill_numeric_item_code() {
		if (!this.dialog || !this.dialog.fields_dict.item_code) {
			return;
		}

		// Never overwrite something the employee already typed.
		if (this.dialog.get_value("item_code")) {
			return;
		}

		return frappe.db
			.get_single_value("Extra Features Settings", "enable_item_numeric_autoname")
			.then((enabled) => {
				if (!enabled) {
					return;
				}
				return frappe.call({ method: "mu_customers.api.get_next_item_code" });
			})
			.then((r) => {
				const code = r && r.message;
				// Re-check: the fetch is async, so the employee may have typed
				// a code of their own while it was in flight.
				if (code && this.dialog && !this.dialog.get_value("item_code")) {
					this.dialog.set_value("item_code", code);
				}
			})
			.catch((error) => {
				// A missing suggestion must not stop the dialog being usable.
				console.error("mu_customers: could not suggest an item code", error);
			});
	}
};
