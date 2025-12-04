app_name = "mu_customers"
app_title = "Mu Customers"
app_publisher = "Mubtkir"
app_description = "Mu Customers"
app_email = "mu@company.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "mu_customers",
# 		"logo": "/assets/mu_customers/logo.png",
# 		"title": "Mu Customers",
# 		"route": "/mu_customers",
# 		"has_permission": "mu_customers.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/mu_customers/css/mu_customers.css"
# app_include_js = "/assets/mu_customers/js/mu_customers.js"

# include js, css files in header of web template
# web_include_css = "/assets/mu_customers/css/mu_customers.css"
# web_include_js = "/assets/mu_customers/js/mu_customers.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "mu_customers/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Payment Entry": "public/js/payment_entry.js",
	"Sales Invoice": [
		"public/js/sales_invoice.js",
		"public/js/item_prices_select.js",
		"public/js/customer_branches_sales.js",
	],
	"Delivery Note": [
		"public/js/item_prices_select.js",
		"public/js/customer_branches_sales.js",
	],
	"Sales Order": [
		"public/js/item_prices_select.js",
		"public/js/customer_branches_sales.js",
	],
	"Purchase Invoice": "public/js/item_prices_select.js",
	"Purchase Order": ["public/js/item_prices_select.js"],
	"Purchase Receipt": ["public/js/item_prices_select.js"],
	"Quotation": ["public/js/item_prices_select.js"],
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "mu_customers/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "mu_customers.utils.jinja_methods",
# 	"filters": "mu_customers.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "mu_customers.install.before_install"
# after_install = "mu_customers.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "mu_customers.uninstall.before_uninstall"
# after_uninstall = "mu_customers.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "mu_customers.utils.before_app_install"
# after_app_install = "mu_customers.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "mu_customers.utils.before_app_uninstall"
# after_app_uninstall = "mu_customers.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "mu_customers.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Item": {"validate": "mu_customers.events.item.clear_auto_description"},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"mu_customers.tasks.all"
# 	],
# 	"daily": [
# 		"mu_customers.tasks.daily"
# 	],
# 	"hourly": [
# 		"mu_customers.tasks.hourly"
# 	],
# 	"weekly": [
# 		"mu_customers.tasks.weekly"
# 	],
# 	"monthly": [
# 		"mu_customers.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "mu_customers.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "mu_customers.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "mu_customers.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["mu_customers.utils.before_request"]
# after_request = ["mu_customers.utils.after_request"]

# Job Events
# ----------
# before_job = ["mu_customers.utils.before_job"]
# after_job = ["mu_customers.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"mu_customers.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Mu Customers"]]},
	{"dt": "Property Setter", "filters": [["module", "=", "Mu Customers"]]},
]
