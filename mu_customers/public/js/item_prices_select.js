// Multi-price selection on transaction item rows.
//
// Replaces the old popup: picking a price is a dropdown on the row itself (and
// in the row detail view), so switching between جملة and تجزئة is one click
// from wherever the user already is. Nothing opens on its own.
//
// The dropdown only appears on rows that have something to choose between. An
// item with a single price has that price applied automatically and the field
// stays hidden, so lines are not crowded by an empty control. That is driven by
// custom_price_options, a per-row count fed from the server: depends_on is
// evaluated per row against that row's own document, which is why the count
// lives on the row rather than on the field.
//
// The dropdown is a Link to Item Price Type filtered per row by a server-side
// query, so each row lists only the types its own item has for that direction -
// which a shared Select field cannot do, because Select options live on the
// docfield and are identical for every row in the grid.

const MU_PRICE_PARENTS = {
	"Sales Invoice": "Selling",
	"Sales Order": "Selling",
	"Delivery Note": "Selling",
	Quotation: "Selling",
	"Purchase Invoice": "Buying",
	"Purchase Order": "Buying",
	"Purchase Receipt": "Buying",
};

const MU_PRICE_METHOD = "mu_customers.mu_customers.doctype.item_prices.item_prices";

function mu_price_direction(frm) {
	return MU_PRICE_PARENTS[frm.doc.doctype] || "Selling";
}

function mu_set_rate(cdt, cdn, price) {
	return frappe.model.set_value(cdt, cdn, "rate", price);
}

// The Price Type column's width and placement are declared in the fixtures,
// not adjusted here.
//
// A Frappe grid has a fixed budget of column units: setup_visible_columns adds
// up colsize and drops the first column that takes the total past 11, along
// with every column after it. Adding a column therefore costs a standard one
// unless room is made in advance, which is why the fixtures narrow item_code
// on the doctypes that can spare a unit, and leave the column out of the grid
// entirely on Delivery Note and Purchase Order, whose grids are already full.
//
// An earlier version worked this out in the browser and rewrote the shared
// docfield at runtime. It depended on the script reaching every session
// intact, and left the field hidden when it did not. Declaring it is the same
// result without the moving parts.

// Record how many choices this row has, so depends_on can hide the dropdown
// when there is nothing to pick.
function mu_set_option_count(cdt, cdn, count) {
	const row = locals[cdt][cdn];
	if (!row || row.custom_price_options === count) {
		return;
	}
	frappe.model.set_value(cdt, cdn, "custom_price_options", count);
}

// Apply the price configured for the row's selected type.
//
// `keep_uom` is set when the user changed the UOM themselves: re-price into
// that unit rather than pulling the row back to the price's own unit.
function mu_apply_selected_price(frm, cdt, cdn, { keep_uom = false } = {}) {
	const row = locals[cdt][cdn];
	if (!row || !row.item_code || !row.custom_item_price_type) {
		return Promise.resolve();
	}

	if (row.__mu_pricing) {
		return Promise.resolve();
	}
	row.__mu_pricing = true;

	const release = () => {
		row.__mu_pricing = false;
	};

	return frappe
		.call({
			method: `${MU_PRICE_METHOD}.get_price_for_type`,
			args: {
				item_code: row.item_code,
				invoice_type: mu_price_direction(frm),
				price_type: row.custom_item_price_type,
				uom: row.uom || null,
			},
		})
		.then((r) => {
			const match = r && r.message;
			if (!match) {
				return;
			}
			return mu_apply_match(cdt, cdn, match, { keep_uom });
		})
		.then(release)
		.catch((error) => {
			release();
			console.error("mu_customers: could not apply item price", error);
		});
}

// UOM first: changing it makes ERPNext recalculate the rate, so setting the
// rate before it would simply be overwritten.
function mu_apply_match(cdt, cdn, match, { keep_uom = false } = {}) {
	const row = locals[cdt][cdn];
	const needs_uom = !keep_uom && match.uom && match.uom !== row.uom;

	return Promise.resolve(
		needs_uom ? frappe.model.set_value(cdt, cdn, "uom", match.uom) : null
	).then(() => mu_set_rate(cdt, cdn, match.price));
}

// Decide what a row should show, and price it if there is no decision to make.
function mu_refresh_row_options(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row || !row.item_code) {
		mu_set_option_count(cdt, cdn, 0);
		return Promise.resolve();
	}

	return frappe
		.call({
			method: `${MU_PRICE_METHOD}.get_price_options`,
			args: {
				item_codes: [row.item_code],
				invoice_type: mu_price_direction(frm),
			},
		})
		.then((r) => {
			const options = (r && r.message && r.message[row.item_code]) || { count: 0, only: null };
			mu_set_option_count(cdt, cdn, options.count);

			// One price is not a choice - apply it and leave the row uncluttered.
			if (options.count === 1 && options.only) {
				row.__mu_pricing = true;
				return mu_apply_match(cdt, cdn, options.only).then(() => {
					row.__mu_pricing = false;
				});
			}
		})
		.catch((error) => {
			console.error("mu_customers: could not read item price options", error);
		});
}

// Recount every line whenever the form opens.
//
// Deliberately not limited to rows with no count: an Int column reads back as
// 0, which is indistinguishable from "no prices", so skipping those left every
// row saved before this existed stuck at 0 and the dropdown hidden. Recounting
// also picks up prices added to an item since the document was written.
function mu_backfill_option_counts(frm) {
	const rows = (frm.doc.items || []).filter((row) => row.item_code);
	if (!rows.length) {
		return;
	}

	frappe
		.call({
			method: `${MU_PRICE_METHOD}.get_price_options`,
			args: {
				item_codes: rows.map((row) => row.item_code),
				invoice_type: mu_price_direction(frm),
			},
		})
		.then((r) => {
			const options = (r && r.message) || {};
			rows.forEach((row) => {
				const entry = options[row.item_code];
				if (entry) {
					// Written straight onto the row: this is display state being
					// restored, and must not mark a saved document dirty.
					row.custom_price_options = entry.count;
				}
			});
			frm.refresh_field("items");
		})
		.catch((error) => {
			console.error("mu_customers: could not backfill item price options", error);
		});
}

Object.keys(MU_PRICE_PARENTS).forEach((parent_doctype) => {
	frappe.ui.form.on(parent_doctype, {
		setup(frm) {
			// Registered once on the grid field; the callback reads the row at
			// query time, so every row filters by its own item.
			frm.set_query("custom_item_price_type", "items", (doc, cdt, cdn) => {
				const row = locals[cdt][cdn] || {};
				return {
					query: `${MU_PRICE_METHOD}.price_type_query`,
					filters: {
						item_code: row.item_code || "",
						invoice_type: mu_price_direction(frm),
					},
				};
			});
		},

		refresh(frm) {
			mu_backfill_option_counts(frm);
		},

	});

	frappe.ui.form.on(`${parent_doctype} Item`, {
		item_code(frm, cdt, cdn) {
			// A price type belonging to the previous item must not survive.
			const row = locals[cdt][cdn];
			if (row && row.custom_item_price_type) {
				frappe.model.set_value(cdt, cdn, "custom_item_price_type", "");
			}
			mu_refresh_row_options(frm, cdt, cdn);
		},

		custom_item_price_type(frm, cdt, cdn) {
			mu_apply_selected_price(frm, cdt, cdn);
		},

		uom(frm, cdt, cdn) {
			mu_apply_selected_price(frm, cdt, cdn, { keep_uom: true });
		},
	});
});
