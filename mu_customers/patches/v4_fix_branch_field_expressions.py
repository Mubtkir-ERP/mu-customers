import frappe

# v3_prefix_branch_fields renamed the branch fields to the custom_ prefix but
# left the expressions that *reference* them untouched, so every custom field
# still pointed at the old name:
#
#   fetch_from           = "customer.has_branches"
#   depends_on           = "has_branches"
#   mandatory_depends_on = "has_branches"
#
# fetch_from is the damaging one: selecting a customer made the client fetch
# Customer.has_branches, a column that no longer exists, and the form died with
# "Field not permitted in query: has_branches". depends_on silently evaluated
# undefined, so the Branch field never appeared either.

RENAMED = {
	"has_branches": "custom_has_branches",
	"branches": "custom_branches",
	"branch": "custom_branch",
}

EXPRESSION_FIELDS = ("depends_on", "mandatory_depends_on", "read_only_depends_on", "fetch_from")


def execute():
	changed = 0

	for row in frappe.get_all(
		"Custom Field",
		filters={"module": "Mu Customers"},
		fields=["name", *EXPRESSION_FIELDS],
	):
		updates = {}

		for key in EXPRESSION_FIELDS:
			current = row.get(key)
			if not current:
				continue
			rewritten = _rewrite(current)
			if rewritten != current:
				updates[key] = rewritten

		if updates:
			for key, value in updates.items():
				frappe.db.set_value("Custom Field", row.name, key, value, update_modified=False)
			changed += 1

	if changed:
		frappe.db.commit()
		frappe.clear_cache()

	print(f"mu_customers: rewrote branch references on {changed} custom field(s)")


def _rewrite(expression):
	"""Replace bare references to the old field names, leaving prefixed ones alone."""
	import re

	def replace(match):
		name = match.group(0)
		# Already prefixed - the regex boundary below can still match the tail
		# of custom_has_branches, so guard on what precedes it.
		return RENAMED.get(name, name)

	# \b would match inside "custom_has_branches"; require the name is not
	# already preceded by "custom_".
	pattern = re.compile(r"(?<!custom_)\b(" + "|".join(sorted(RENAMED, key=len, reverse=True)) + r")\b")
	return pattern.sub(replace, expression)
