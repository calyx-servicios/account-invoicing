`15.0.1.0.0`
-----------

- Migrated to Odoo 15.0
- Removed payment creation functionality (invoice stays in draft)
- Removed action_post (no AFIP validation)
- Removed account_payment_group dependency
- Fixed product.template to product.product for invoice lines
- Fixed deprecated field type to move_type
- Adapted invoice line writing for Odoo 15 ORM (check_move_validity)
- Removed website=True from route decorator

`1.0.1`
-------

- changed how invoice posting works for easier inheritance

`1.0.0`
-------

- init version
