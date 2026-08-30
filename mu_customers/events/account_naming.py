# Copyright (c) 2025, Mubtkir and contributors
# For license information, please see license.txt

import re

import frappe

LEADING_DIGITS = re.compile(r"\d+")


def is_enabled():
	return bool(frappe.db.get_single_value("Extra Features Settings", "enable_account_numeric_autoname"))


def _numeric_base(account_number):
	"""First numeric segment of an account number, as an int.

	ERPNext's standard chart ships group accounts numbered as ranges
	("1100-1600 - Current Assets"). The old code ran int() straight on that and
	raised ValueError, which made it impossible to add a child under any of
	them. Returns None when there is nothing numeric to build on.
	"""
	if account_number is None:
		return None

	match = LEADING_DIGITS.search(str(account_number).strip())
	return int(match.group()) if match else None


def _next_child_number(parent_account, company):
	"""Next free account number under `parent_account`, or None.

	Numbers stay at the parent's own digit width and increment by one, so the
	result sits inside the chart's hierarchy (7100 -> 7101, 7102 ...) instead of
	the old "parent number + zero-padded counter" concatenation, which produced
	values like 710001 and broke outright past 99 siblings.
	"""
	base = _numeric_base(frappe.db.get_value("Account", parent_account, "account_number"))
	if base is None:
		return None

	width = len(str(base))
	siblings = frappe.get_all(
		"Account",
		filters={"parent_account": parent_account, "company": company},
		pluck="account_number",
	)
	used = {str(n).strip() for n in siblings if n}

	candidate = base + 1
	# A generous ceiling: enough to walk past a full level, low enough that a
	# pathological chart cannot spin here.
	for _ in range(100000):
		number = str(candidate).zfill(width)
		if number not in used and not frappe.db.exists(
			"Account", {"account_number": number, "company": company}
		):
			return number
		candidate += 1

	return None


def _build_name(doc, company_abbr):
	parts = [doc.account_number, doc.account_name, company_abbr]
	return " - ".join(str(p).strip() for p in parts if p and str(p).strip())


def custom_autoname(doc, method=None):
	if not is_enabled():
		return

	company_abbr = frappe.db.get_value("Company", doc.company, "abbr") if doc.company else None

	# Only generate a number when the user did not supply one.
	if not doc.account_number and doc.parent_account:
		doc.account_number = _next_child_number(doc.parent_account, doc.company)

	name = _build_name(doc, company_abbr)
	if name:
		# Falsy parts are skipped, so an account with no number is named
		# "name - ABBR" like ERPNext's own, never "None - name - ABBR".
		doc.name = name
