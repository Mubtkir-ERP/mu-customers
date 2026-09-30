"""Make the Update Stock default site-configurable.

The app used to ship the default as a fixture and also force the value at
runtime. Both behaviours prevented a customer from changing the default from
Customize Form because a later migrate/refresh could put it back to 1.

This patch creates the default only when the site has no Property Setter yet.
An existing 0 or 1 is therefore treated as the customer's choice and is left
untouched.
"""

from mu_customers.install import ensure_update_stock_defaults


def execute():
	ensure_update_stock_defaults()
