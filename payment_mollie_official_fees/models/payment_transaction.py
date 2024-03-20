# -*- coding: utf-8 -*-

from odoo import models, api


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model_create_multi
    def create(self, values_list):
        """ Add the mollie fees to the transaction based on mollie methods. """
        transactions = super().create(values_list)
        for transaction in transactions:
            sale_order = transaction.sale_order_ids and transaction.sale_order_ids[0]
            if sale_order and sale_order.website_id:
                sale_order._manage_mollie_fees_line(transaction)
                transaction.amount = sale_order.amount_total
        return transactions
