"""Re-apply custom_note as the authoritative invoice Remarks value.

Older sites may already have executed migrate_custom_note_to_remarks when that
patch only filled an empty Remarks field. This new patch deliberately runs once
on upgrade so every non-empty legacy custom_note replaces Remarks, including
when Remarks currently contains different text.

The custom_note column/value is preserved; only the visible Remarks value is
replaced. Empty custom_note values do not erase Remarks.
"""

from mu_customers.patches.migrate_custom_note_to_remarks import (
	CANDIDATES,
	overwrite_remarks_from_custom_note,
)


def execute():
	for doctype in CANDIDATES:
		overwrite_remarks_from_custom_note(doctype)
