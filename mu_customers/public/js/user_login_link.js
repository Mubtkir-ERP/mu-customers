// زرّا "رابط الدخول السريع" على مستند User.
// ------------------------------------------------------------------
// يظهران فقط لـ Administrator أو من يملك صلاحية كتابة على User.
// حقل المدة (custom_login_link_validity_days): 0 = دائم حتى الإلغاء.

frappe.ui.form.on("User", {
	refresh(frm) {
		// لا نعرض شيئاً لمستخدم جديد غير محفوظ، ولا للحسابات النظامية.
		if (frm.is_new()) return;
		if (["Administrator", "Guest"].includes(frm.doc.name)) return;

		// الصلاحية: Administrator أو من يملك كتابة على User.
		const can_manage =
			frappe.session.user === "Administrator" ||
			frappe.perm.has_perm("User", 0, "write");
		if (!can_manage) return;

		const group = __("رابط الدخول السريع");

		// زر: إنشاء / تحديث الرابط
		frm.add_custom_button(
			__("إنشاء رابط دخول"),
			() => mu_generate_login_link(frm),
			group
		);

		// زر: إلغاء الرابط
		frm.add_custom_button(
			__("إلغاء الرابط"),
			() => mu_revoke_login_link(frm),
			group
		);

		// مؤشّر حالة الرابط الحالي (موجود/منتهٍ/لا يوجد).
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
		freeze_message: __("جارٍ إنشاء الرابط..."),
		callback(r) {
			if (!r.message) return;
			mu_render_link_dialog(frm, r.message);
			frm.reload_doc();
		},
	});
}

function mu_revoke_login_link(frm) {
	frappe.confirm(
		__("سيتم إبطال الرابط الحالي فوراً. هل أنت متأكد؟"),
		() => {
			frappe.call({
				method: "mu_customers.login_link.revoke",
				args: { user: frm.doc.name },
				freeze: true,
				callback() {
					frappe.show_alert(
						{ message: __("تم إلغاء الرابط"), indicator: "orange" },
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
		? __("دائم (لا ينتهي حتى الإلغاء اليدوي)")
		: __("ينتهي في: ") + frappe.datetime.str_to_user(data.expiry);

	const d = new frappe.ui.Dialog({
		title: __("رابط الدخول السريع لـ ") + (data.full_name || data.user),
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
					<div style="direction:rtl;color:#8d99a6;font-size:12px">
						${frappe.utils.escape_html(expiry_text)}
					</div>
				`,
			},
		],
		primary_action_label: __("نسخ الرابط"),
		primary_action() {
			navigator.clipboard
				.writeText(data.link)
				.then(() =>
					frappe.show_alert(
						{ message: __("تم نسخ الرابط"), indicator: "green" },
						3
					)
				)
				.catch(() => {
					// متصفحات قديمة: اختيار يدوي.
					frappe.msgprint(__("انسخ الرابط يدوياً من الصندوق أعلاه"));
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
					__("لا يوجد رابط دخول سريع لهذا المستخدم"),
					"gray"
				);
			} else if (s.expired) {
				frm.dashboard.set_headline_alert(
					__("رابط الدخول السريع منتهي الصلاحية — أنشئ رابطاً جديداً"),
					"red"
				);
			} else {
				const txt = s.permanent
					? __("يوجد رابط دخول سريع فعّال (دائم)")
					: __("يوجد رابط دخول سريع فعّال — ينتهي: ") +
					  frappe.datetime.str_to_user(s.expiry);
				frm.dashboard.set_headline_alert(txt, "green");
			}
		},
	});
}
