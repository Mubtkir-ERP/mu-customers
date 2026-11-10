// Quick login link buttons on the User document.
// ------------------------------------------------------------------
// Visible only to Administrator or users with write permission on User.
// Validity days (custom_login_link_validity_days): 0 = permanent until revoked.

frappe.ui.form.on("User", {
	refresh(frm) {
		// Do not show for new unsaved users or system accounts.
		if (frm.is_new()) return;
		if (["Administrator", "Guest"].includes(frm.doc.name)) return;

		// Permissions: Administrator or has write permission on User.
		const can_manage =
			frappe.session.user === "Administrator" ||
			frappe.perm.has_perm("User", 0, "write");
		if (!can_manage) return;

		const group = __("Quick Login Link");

		// Button: Generate / update link
		frm.add_custom_button(
			__("Create Login Link"),
			() => mu_generate_login_link(frm),
			group
		);

		// Button: Revoke link
		frm.add_custom_button(
			__("Revoke Login Link"),
			() => mu_revoke_login_link(frm),
			group
		);

		// Show status indicator of current link (active / expired / none).
		mu_show_link_indicator(frm);
	},
});

function mu_generate_login_link(frm) {
	frappe.call({
		method: "mu_customers.login_link.generate",
		args: {
			user: frm.doc.name,
			validity_days: frm.doc.custom_login_link_validity_days || 0,
		},
		freeze: true,
		freeze_message: __("Generating login link..."),
		callback(r) {
			if (!r.message) return;
			mu_render_link_dialog(frm, r.message);
			frm.reload_doc();
		},
	});
}

function mu_revoke_login_link(frm) {
	frappe.confirm(
		__("Current login link will be revoked immediately. Are you sure?"),
		() => {
			frappe.call({
				method: "mu_customers.login_link.revoke",
				args: { user: frm.doc.name },
				freeze: true,
				callback() {
					frappe.show_alert(
						{ message: __("Login link revoked"), indicator: "orange" },
						4
					);
					frm.reload_doc();
				},
			});
		}
	);
}

function mu_render_link_dialog(frm, data) {
	const expiry_text = data.permanent
		? __("Permanent (Valid until revoked)")
		: __("Expires on: {0}", [frappe.datetime.str_to_user(data.expiry)]);

	const d = new frappe.ui.Dialog({
		title: __("Quick Login Link for {0}", [data.full_name || data.user]),
		fields: [
			{
				fieldname: "link_html",
				fieldtype: "HTML",
				options: `
					<div style="direction:ltr;text-align:left;
						background:#f4f5f6;border:1px solid #d1d8dd;
						border-radius:6px;padding:10px;word-break:break-all;
						font-family:monospace;font-size:12px;margin-bottom:10px">
						${frappe.utils.escape_html(data.link)}
					</div>
					<div style="color:#8d99a6;font-size:12px">
						${frappe.utils.escape_html(expiry_text)}
					</div>
				`,
			},
		],
		primary_action_label: __("Copy Link"),
		primary_action() {
			navigator.clipboard
				.writeText(data.link)
				.then(() =>
					frappe.show_alert(
						{ message: __("Login link copied to clipboard"), indicator: "green" },
						3
					)
				)
				.catch(() => {
					frappe.msgprint(__("Copy the link manually from the box above"));
				});
		},
	});
	d.show();
}

function mu_show_link_indicator(frm) {
	frappe.call({
		method: "mu_customers.login_link.status",
		args: { user: frm.doc.name },
		callback(r) {
			const s = r.message || {};
			if (!s.exists) {
				frm.dashboard.set_headline_alert(
					__("No quick login link found for this user"),
					"gray"
				);
			} else if (s.expired) {
				frm.dashboard.set_headline_alert(
					__("Quick login link expired — please generate a new one"),
					"red"
				);
			} else {
				const txt = s.permanent
					? __("Active quick login link exists (Permanent)")
					: __("Active quick login link exists — Expires: {0}", [
							frappe.datetime.str_to_user(s.expiry),
					  ]);
				frm.dashboard.set_headline_alert(txt, "green");
			}
		},
	});
}
