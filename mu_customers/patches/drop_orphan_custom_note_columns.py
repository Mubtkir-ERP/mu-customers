"""Legacy compatibility patch: intentionally non-destructive.

Older releases dropped the Sales Invoice / Purchase Invoice `custom_note`
column after migrating values to `remarks`. We now preserve that column so
historical note data is never destroyed. The field is hidden separately by
`v17_hide_invoice_custom_note_preserve_data`.
"""


def execute():
	# Intentionally do nothing. Never DROP custom_note here.
	return
