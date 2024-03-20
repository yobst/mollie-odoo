# -*- coding: utf-8 -*-

{
    'name': 'Mollie Shipment Sync',
    'version': '17.0.0.0',
    'description': '',
    'summary': 'Sync shipment details to mollie payments',
    'author': 'Mollie',
    'maintainer': 'Applix',
    'license': 'LGPL-3',
    'category': '',
    'depends': [
        'sale_management',
        'payment_mollie_official'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'data/mail_activity.xml',
        'views/payment_acquirer.xml',
        'views/sale_order.xml',
        'wizard/mollie_confirmation_wizard_views.xml',
    ],

    'images': [
        'static/description/cover.png',
    ],
}
