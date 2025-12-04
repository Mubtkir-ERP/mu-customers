frappe.ui.form.on(cur_frm.doc.doctype + " Item", {
	item_code: function (frm, cdt, cdn) {
		frm.trigger("item_prices", cdt, cdn);
	},
	select_rate: function (frm, cdt, cdn) {
		frm.trigger("item_prices", cdt, cdn);
	},
	item_prices: function (frm, cdt, cdn) {
		var doc = locals[cdt][cdn];
		if (!doc.item_code) {
			return;
		}
		var invoice_type = ["Purchase Invoice", "Purchase Order", "Purchase Receipt"].includes(
			cur_frm.doc.doctype
		)
			? "Buying"
			: "Selling";
		frappe.call({
			method: "mu_customers.mu_customers.doctype.item_prices.item_prices.get_item_prices",
			args: {
				item_code: doc.item_code,
				invoice_type: invoice_type,
			},
			callback: function (r) {
				var prices = [];
				$.each(r.message.prices || [], function (i, v) {
					prices.push({ price_type: v.price_type, uom: v.uom, price: v.price });
				});
				let d = new frappe.ui.Dialog({
					title: __("Select Item Price"),
					fields: [
						{
							fieldname: "item_prices",
							fieldtype: "Table",
							label: "Prices",
							cannot_add_rows: true,
							cannot_delete_rows: true,
							data: prices,
							get_data: function () {
								return [];
							},
							fields: [
								{
									fieldname: "price_type",
									fieldtype: "Data",
									label: __("Price Type"),
									in_list_view: 1,
									read_only: 1,
								},
								{
									fieldname: "uom",
									fieldtype: "Link",
									label: __("UOM"),
									options: "UOM",
									in_list_view: 1,
									read_only: 1,
								},
								{
									fieldname: "price",
									fieldtype: "Currency",
									label: __("Price"),
									in_list_view: 1,
									read_only: 1,
								},
							],
						},
					],
					primary_action_label: __("Select"),
					primary_action: function (data) {
						var selected = d.fields_dict.item_prices.grid.get_selected_children();
						if (selected) {
							if (selected.length > 1) {
								frappe.throw(__("Select Only 1 Row"));
							}
							if (selected.length == 0) {
								frappe.throw(__("Select a Row"));
							}
							frappe.model.set_value(cdt, cdn, "rate", selected[0].price);
							if (selected[0].uom) {
								frappe.model.set_value(cdt, cdn, "uom", selected[0].uom);
							}
							d.hide();
						}
					},
				});
				if (r.message.enabled) {
					d.show();
				}
			},
		});
	},
});
