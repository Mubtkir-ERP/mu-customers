// Show warehouse-level stock for an item as it is added to a Sales Invoice.
//
// Rewritten: one server call instead of two chained frappe.client calls per
// row, the setting is read once per session, and the result opens in a plain
// dismissible dialog instead of a nested msgprint.

let mu_qty_popup_enabled = null;

function mu_is_qty_popup_enabled() {
	if (mu_qty_popup_enabled !== null) {
		return Promise.resolve(mu_qty_popup_enabled);
	}
	return frappe.db
		.get_single_value("Extra Features Settings", "enable_item_qty_popup_si")
		.then((value) => {
			mu_qty_popup_enabled = !!value;
			return mu_qty_popup_enabled;
		})
		.catch(() => false);
}

function mu_show_stock_dialog(item_code, data) {
	const rows = data.rows || [];
	const body = rows.length
		? `<table class="table table-bordered" style="margin:0">
				<thead><tr>
					<th>${__("Warehouse")}</th>
					<th style="text-align:right">${__("Quantity")}</th>
				</tr></thead>
				<tbody>
					${rows
						.map(
							(r) => `<tr>
								<td>${frappe.utils.escape_html(r.warehouse || "")}</td>
								<td style="text-align:right">${format_number(r.actual_qty)}</td>
							</tr>`
						)
						.join("")}
				</tbody>
				<tfoot><tr>
					<th>${__("Total")}</th>
					<th style="text-align:right">${format_number(data.total || 0)}</th>
				</tr></tfoot>
			</table>`
		: `<p class="text-muted">${__("No stock found for this item.")}</p>`;

	const d = new frappe.ui.Dialog({
		title: __("Stock for {0}", [item_code]),
		fields: [{ fieldtype: "HTML", fieldname: "stock", options: body }],
		primary_action_label: __("Close"),
		primary_action: () => d.hide(),
	});
	return mu_customers.ui.show_dialog(d);
}

frappe.ui.form.on("Sales Invoice Item", {
	item_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row || !row.item_code) {
			return;
		}

		// Nothing pops up before there is a customer: ERPNext raises its own
		// "Please specify Customer" at that point, and stacking this dialog
		// under that alert is what made the screen unreadable.
		if (!mu_customers.ui.has_party(frm)) {
			return;
		}

		mu_customers.ui.enqueue(() =>
			mu_is_qty_popup_enabled().then((enabled) => {
				if (!enabled) {
					return;
				}
				return frappe
					.call({
						method: "mu_customers.api.get_item_stock_levels",
						args: { item_code: row.item_code },
					})
					.then((r) => {
						if (r && r.message) {
							return mu_show_stock_dialog(row.item_code, r.message);
						}
					});
			})
		);
	},
});
