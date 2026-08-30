"""Move the invoice note box back under the tax number.

Migrating custom_note into the standard `remarks` field kept the data but sent
the box to the end of the form. This restores the position staff were used to.
"""

from mu_customers.invoice_note_position import apply


def execute():
	moved = apply()
	if moved:
		print(f"mu_customers: note repositioned under the tax number on {', '.join(moved)}")
