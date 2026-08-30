// Serialise this app's popups.
//
// Picking an item on a Sales Invoice can trigger the stock dialog and the
// price dialog at the same moment, and ERPNext may add its own "Please specify
// Customer" alert on top. All three used to render into one screen. Everything
// this app opens now goes through one queue: the next popup waits for the
// previous one to close.

frappe.provide("mu_customers.ui");

if (!mu_customers.ui.enqueue) {
	mu_customers.ui._chain = Promise.resolve();

	// Run `task` once whatever is already queued has finished. `task` returns a
	// promise that settles when its popup closes - or immediately, if it decides
	// not to open one.
	mu_customers.ui.enqueue = function (task) {
		mu_customers.ui._chain = mu_customers.ui._chain
			.then(() => task())
			.catch((error) => {
				// A failing popup must not wedge every popup after it.
				console.error("mu_customers: queued dialog failed", error);
			});
		return mu_customers.ui._chain;
	};

	// Show a dialog and resolve when the user dismisses it.
	mu_customers.ui.show_dialog = function (dialog) {
		return new Promise((resolve) => {
			if (!dialog) {
				resolve();
				return;
			}

			let settled = false;
			const done = () => {
				if (settled) {
					return;
				}
				settled = true;
				resolve();
			};

			dialog.$wrapper.on("hidden.bs.modal", done);
			// Belt and braces: if the modal is torn down without firing the
			// bootstrap event, the queue still moves on.
			dialog.onhide = done;

			dialog.show();
		});
	};

	// True when the transaction has a party, so row-level popups can stay quiet
	// until the document is far enough along to price anything.
	mu_customers.ui.has_party = function (frm) {
		const buying = ["Purchase Invoice", "Purchase Order", "Purchase Receipt", "Supplier Quotation"];
		return buying.includes(frm.doc.doctype) ? !!frm.doc.supplier : !!frm.doc.customer;
	};
}
