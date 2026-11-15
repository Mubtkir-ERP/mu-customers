// Enable Full Width mode by default across Desk
(function () {
	try {
		if (localStorage.getItem("container_fullwidth") === null) {
			localStorage.setItem("container_fullwidth", "true");
		}
		if (JSON.parse(localStorage.getItem("container_fullwidth") || "true")) {
			$(document.body).addClass("full-width");
		}
	} catch (e) {
		// Ignore storage errors in restricted contexts
	}
})();

$(document).on("toolbar_setup", function () {
	try {
		if (localStorage.getItem("container_fullwidth") === null) {
			localStorage.setItem("container_fullwidth", "true");
		}
		if (frappe.ui.toolbar && frappe.ui.toolbar.set_fullwidth_if_enabled) {
			frappe.ui.toolbar.set_fullwidth_if_enabled();
		}
	} catch (e) {
		// Ignore
	}
});
