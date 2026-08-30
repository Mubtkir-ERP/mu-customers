// Keep Default Warehouse Qty honest on the Item form.
//
// The field is only written by a background job that runs on stock movement,
// so an item whose default warehouse was just changed - or one that already
// held stock before this app was installed - showed a stale zero until
// something moved. Read the live total on refresh instead of trusting it.

// Default warehouses currently entered on the form, preferring the session's
// company and falling back to every row - the same rule the server applies.
function mu_form_default_warehouses(frm) {
	const rows = (frm.doc.item_defaults || []).filter((d) => d.default_warehouse);
	const company = frappe.defaults.get_user_default("Company");
	const scoped = rows.filter((d) => !company || d.company === company);
	return (scoped.length ? scoped : rows).map((d) => d.default_warehouse);
}

function mu_refresh_default_warehouse_qty(frm, { use_form_rows = false } = {}) {
	if (frm.is_new() || !frm.doc.name) {
		return;
	}

	const args = { item_code: frm.doc.name };
	if (use_form_rows) {
		// The rows on disk are still the old ones while the user is editing,
		// so total what is on screen instead.
		args.warehouses = JSON.stringify(mu_form_default_warehouses(frm));
	}

	frappe
		.call({ method: "mu_customers.api.get_default_warehouse_qty", args })
		.then((r) => {
			if (!r || !r.message) {
				return;
			}

			const qty = r.message.qty || 0;
			const warehouses = r.message.warehouses || [];

			frm.set_df_property(
				"custom_default_warehouse_qty",
				"description",
				warehouses.length
					? __("Across: {0}", [warehouses.join(", ")])
					: __("No default warehouse is set for this item.")
			);

			if (frm.doc.custom_default_warehouse_qty === qty) {
				return;
			}

			// Assign directly rather than via set_value: this is a derived,
			// read-only figure and must not mark the form dirty.
			frm.doc.custom_default_warehouse_qty = qty;
			frm.refresh_field("custom_default_warehouse_qty");
		})
		.catch(() => {
			// A stale figure is better than a broken Item form.
		});
}

frappe.ui.form.on("Item", {
	refresh(frm) {
		mu_refresh_default_warehouse_qty(frm);
	},

	item_defaults_remove(frm) {
		mu_refresh_default_warehouse_qty(frm, { use_form_rows: true });
	},
});

frappe.ui.form.on("Item Default", {
	default_warehouse(frm) {
		mu_refresh_default_warehouse_qty(frm, { use_form_rows: true });
	},

	company(frm) {
		mu_refresh_default_warehouse_qty(frm, { use_form_rows: true });
	},
});
