/* global erpnext */
frappe.provide("erpnext.TransactionController");

if (erpnext.TransactionController) {
	erpnext.TransactionController.prototype.change_form_labels = function (company_currency) {
		console.log("TransactionController");
		let me = this;

		this.frm.set_currency_labels(
			[
				"base_total",
				"base_net_total",
				"base_total_taxes_and_charges",
				"base_discount_amount",
				"base_grand_total",
				"base_rounded_total",
				"base_in_words",
				"base_taxes_and_charges_added",
				"base_taxes_and_charges_deducted",
				"total_amount_to_pay",
				"base_paid_amount",
				"base_write_off_amount",
				"base_change_amount",
				"base_operating_cost",
				"base_raw_material_cost",
				"base_total_cost",
				"base_scrap_material_cost",
				"base_rounding_adjustment",
			],
			company_currency
		);

		this.frm.set_currency_labels(
			[
				"total",
				"net_total",
				"total_taxes_and_charges",
				"discount_amount",
				"grand_total",
				"taxes_and_charges_added",
				"taxes_and_charges_deducted",
				"tax_withholding_net_total",
				"rounded_total",
				"in_words",
				"paid_amount",
				"write_off_amount",
				"operating_cost",
				"scrap_material_cost",
				"rounding_adjustment",
				"raw_material_cost",
				"total_cost",
			],
			this.frm.doc.currency
		);

		this.frm.set_currency_labels(
			["outstanding_amount", "total_advance"],
			this.frm.doc.party_account_currency
		);

		this.frm.set_df_property(
			"conversion_rate",
			"description",
			"1 " + this.frm.doc.currency + " = [?] " + company_currency
		);

		if (
			this.frm.doc.price_list_currency &&
			this.frm.doc.price_list_currency != company_currency
		) {
			this.frm.set_df_property(
				"plc_conversion_rate",
				"description",
				"1 " + this.frm.doc.price_list_currency + " = [?] " + company_currency
			);
		}

		// toggle fields
		this.frm.toggle_display(
			[
				"conversion_rate",
				"base_total",
				"base_net_total",
				"base_tax_withholding_net_total",
				"base_total_taxes_and_charges",
				"base_taxes_and_charges_added",
				"base_taxes_and_charges_deducted",
				"base_grand_total",
				"base_rounded_total",
				"base_in_words",
				"base_discount_amount",
				"base_paid_amount",
				"base_write_off_amount",
				"base_operating_cost",
				"base_raw_material_cost",
				"base_total_cost",
				"base_scrap_material_cost",
				"base_rounding_adjustment",
			],
			this.frm.doc.currency != company_currency
		);

		this.frm.toggle_display(
			["plc_conversion_rate", "price_list_currency"],
			this.frm.doc.price_list_currency != company_currency
		);

		let show =
			cint(this.frm.doc.discount_amount) ||
			(this.frm.doc.taxes || []).filter(function (d) {
				return d.included_in_print_rate === 1;
			}).length;

		if (this.frm.doc.doctype && frappe.meta.get_docfield(this.frm.doc.doctype, "net_total")) {
			this.frm.toggle_display("net_total", true);
		}

		if (
			this.frm.doc.doctype &&
			frappe.meta.get_docfield(this.frm.doc.doctype, "base_net_total")
		) {
			this.frm.toggle_display(
				"base_net_total",
				true && me.frm.doc.currency != company_currency
			);
		}
	};
}
