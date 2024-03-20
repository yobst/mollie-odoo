# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PaymentproviderMollie(models.Model):
    _inherit = 'payment.provider'

    mollie_auto_sync_shipment = fields.Boolean()
    reduce_quantity_action = fields.Selection([
        ('generate_activity', 'Generate Activity For Manual Action'),
        ('auto_sync', 'Automatic Sync Quantity In Mollie')
    ], string='Reduce Quantity Action', default='generate_activity')

    # -----------------------------------------------
    # Methods that uses to mollie python lib
    # -----------------------------------------------

    def _api_mollie_sync_shipment(self, order_reference, shipment_data):
        return self._mollie_make_request(f'/orders/{order_reference}/shipments', data=shipment_data, method="POST")

    def _api_mollie_manage_order(self, order_reference, data, order_status, silent_errors=False):
        """ Manage the payment records on the mollie.
        :param str order_reference: api is selected based on this parameter
        :param dict data: Change of data opration type in (add, update, cancel).
        :return: details of Order
        :rtype: dict
        """
        endpoint = f'/orders/{order_reference}/lines'
        if order_status in ('created', 'pending', 'authorized'):
            method = "PATCH"
        if order_status == 'shipping':
            method = "DELETE"
        return self._mollie_make_request(endpoint, data=data, method=method, silent_errors=silent_errors)
