from mu_customers.install import enable_supplier_invoice_uniqueness

# The app's before_install used to delete Purchase Invoice-bill_no-unique,
# removing the guard against entering and paying the same supplier invoice
# twice. This turns ERPNext's own control back on.


def execute():
	enable_supplier_invoice_uniqueness()
