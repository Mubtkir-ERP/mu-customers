frappe.ui.form.on("Item", {
	onload: function (frm) {
		// frappe.db.get_single_value('Feature Settings', 'site_json').then(site_json => {
		//     if (site_json) {
		//         console.log("ok");
		//         var site_json_object = JSON.parse(site_json);
		//         if (site_json_object.enable_item_series === 1 && !frm.doc.item_code) {
		frappe.db
			.get_list("Item", {
				fields: ["name"],
				order_by: "creation desc",
				limit: 1,
			})
			.then((records) => {
				if (records.length > 0) {
					let last_item_code = records[0].name;
					if (!isNaN(last_item_code)) {
						frm.set_value("item_code", (parseInt(last_item_code) + 1).toString());
					}
				}
			});
	},
	// }
	//     })
	// }
});
