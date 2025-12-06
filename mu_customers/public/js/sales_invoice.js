frappe.ui.form.on("Sales Invoice", {
	onload: function (frm) {
		if (frm.is_new()) {
			if (frm.fields_dict && frm.fields_dict.mode_of_payment) {
				frm.set_value("mode_of_payment", __("Cash")); // أو "نقد" حسب ما هو موجود
			}
		}
	},
});

frappe.ui.form.on("Sales Invoice Item", {
	item_code: function (frm, cdt, cdn) {
		const item = frappe.get_doc(cdt, cdn);
		if (item.item_code) {
			// Fetch the "enable_item_qty_popup_si" setting from "Extra Features Settings"
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Extra Features Settings",
				},
				callback: function (settings) {
					// Check if the popup is enabled
					if (settings.message && settings.message.enable_item_qty_popup_si == 1) {
						// Fetch warehouse and quantity details
						frappe.call({
							method: "frappe.client.get_list",
							args: {
								doctype: "Bin",
								fields: ["warehouse", "actual_qty"],
								filters: {
									item_code: item.item_code,
								},
							},
							callback: function (r) {
								if (r.message && r.message.length > 0) {
									let total_qty = 0;
									let warehouse_details = `<table class="table table-bordered">
                                        <thead>
                                            <tr>
                                                <th>Warehouse</th>
                                                <th>Quantity</th>
                                            </tr>
                                        </thead>
                                        <tbody>`;

									r.message.forEach((bin) => {
										warehouse_details += `<tr>
                                            <td>${bin.warehouse}</td>
                                            <td>${bin.actual_qty}</td>
                                        </tr>`;
										total_qty += bin.actual_qty;
									});

									warehouse_details += `</tbody></table>`;
									warehouse_details += `<p><strong>Total Quantity:</strong> ${total_qty}</p>`;

									// Show popup with warehouse details
									frappe.msgprint({
										title: __("Warehouse Details"),
										indicator: "blue",
										message: warehouse_details,
									});
								} else {
									frappe.msgprint(__("No stock found for the selected item."));
								}
							},
						});
					}
				},
			});
		}
	},
});
