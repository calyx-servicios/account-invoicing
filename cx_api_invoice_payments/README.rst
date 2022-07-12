===================================
Calyx Services Invoice Payments API
===================================

.. !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !! This file is intended to be in every module    !!
   !! to explain why and how it works.               !!
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


.. User https://shields.io for badge creation.
.. |badge1| image:: https://img.shields.io/badge/maturity-Stable-brightgreen
    :target: https://odoo-community.org/page/development-status
    :alt: Stable
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-calyx--servicios/account--invoicing-lightgray.png?logo=github
    :target: https://github.com/calyx-servicios/account-invoicing.git
    :alt: calyx-servicios/account-invoicing.git

|badge1| |badge2| |badge3|

.. !!! Description must be max 2-3 paragraphs, and is required.

This module allows to integrate external integrations to create Invoices and Payments into Odoo.

**Table of contents**

.. contents::
   :local:

.. !!! Configuration: This file is optional, it should explain how to configure the module before using it; it is aimed at advanced users. To configure this module, you need to:

Configure
=========

* Go to Users & Companies > JWT Validators > cx_api_invoice_payments and configure the Issuer and the Secret Key.

Usage
=====

1. Make a request to the API to create a new Invoice (/account/create/invoice).

Code example::

    import time
    import json
    import requests
    from jose import jwt

<<<<<<< HEAD

    DB_NAME = "13-bitex-test-1"

    BASE_URL = "http://localhost:8069"

    AUTH_URL = f"{BASE_URL}/account/create/invoice"
=======
    BASE_URL = "http://localhost:8069"

    CREATE_INVOICE_URL = f"{BASE_URL}/account/create/invoice"
>>>>>>> add_cx_api_invoice_payments

    TOKEN = jwt.encode(
        {
            "aud": "cx_api_invoice_payments",
            "iss": "issuer",
<<<<<<< HEAD
            "exp": time.time() + 600000,
=======
            "exp": time.time() + 600,
>>>>>>> add_cx_api_invoice_payments
            "email": "admin",
        },
        key="secretkey",  # They key is set in Odoo JWT Validators configuration.
        algorithm=jwt.ALGORITHMS.HS256,
    )


    def create_invoice():
        headers = {"Authorization": "Bearer " + TOKEN, "Content-type": "application/json"}
        data = {
            "jsonrpc": "2.0",
            "params": {
                "company": 1,
                "partner": "Adecco Argentina",
                "date": "01-01-2022",
                "journal": "Ventas",
                "document_type": "FACTURAS A",
                "lines": [
                    {
                        "product": "honorarios",
                        "quantity": 2,
                        "price_unit": 10,
                        "taxes": ["IVA 21%"],
                    },
                    {
                        "product": "ofi",
                        "quantity": 4,
                        "price_unit": 5,
                        "taxes": ["IVA 27%"],
                    },
                ],
                "payments": [{"journal": "Efectivo"}],
            },
        }

<<<<<<< HEAD
        res = requests.post(AUTH_URL, data=json.dumps(data), headers=headers)
=======
        res = requests.post(CREATE_INVOICE_URL, data=json.dumps(data), headers=headers)
>>>>>>> add_cx_api_invoice_payments
        res = json.loads(res.content)
        print(res)
        # {
        #     "jsonrpc": "2.0",
        #     "id": null,
        #     "result": {
        #         "result": "Invoice created",
        #         "invoice_id": 81611,
        #         "invoice_number": "FA-A 00000-00000021",
        #         "invoice_date": "2022-01-01",
        #         "invoice_amount": 49.6,
        #         "invoice_currency": "ARS",
        #         "invoice_state": "posted",
        #         "invoice_journal": "VENTAS",
        #         "invoice_partner": "Adecco Argentina",
        #         "invoice_partner_vat": "30656760172",
        #         "payment_group_id": 435,
        #         "payment_group_number": "RE-X 0001-00000021",
        #         "payment_group_amount": 49.6,
        #         "payment_group_state": "posted",
        #     },
        # }


    create_invoice()

Known issues / Roadmap
======================

* Customer Invoices implemented.

* Other types are not implemented yet.

Bug Tracker
===========

* Contact to the development team

Credits
=======

Authors
~~~~~~~

* Calyx Servicios S.A.

Contributors
~~~~~~~~~~~~

* `Calyx Servicios S.A. <https://odoo.calyx-cloud.com.ar/>`_
  
  * Federico Gregori

Maintainers
~~~~~~~~~~~

This module is maintained by Calyx Servicios S.A.

.. image:: https://ss-static-01.esmsv.com/id/13290/galeriaimagenes/obtenerimagen/?width=120&height=40&id=sitio_logo&ultimaModificacion=2020-05-25+21%3A45%3A05
   :alt: Calyx Servicios S.A.
   :target: https://odoo.calyx-cloud.com.ar/

CALYX SERVICIOS S.A. is part of the PGK Consultores economic group, member of an important global network, a world organization.
The PGK Consultores group is one of the 20 largest consultant-studios in Argentina with nearly 300 professionals.

This module is part of the `Account Invoicing <https://github.com/calyx-servicios/account-invoicing.git>`_ project on GitHub.
