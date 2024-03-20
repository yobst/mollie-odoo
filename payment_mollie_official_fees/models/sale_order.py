# -*- coding: utf-8 -*-

from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _remove_mollie_fees_line(self):
        """ Remove delivery products from the sales orders """
        if self.state == 'draft':
            mollie_fees_line = self.order_line.filtered(lambda line: line.is_mollie_fees)
            if mollie_fees_line:
                mollie_fees_line.sudo().unlink()

    def _manage_mollie_fees_line(self, transaction):
        """ Manage mollie fees based on mollie methods.

            :param recordset transaction: The transaction of the current website payment, as a `payment.transaction` record
        """
        self._remove_mollie_fees_line()
        fees_product_id = transaction.provider_id.mollie_fees_product_id
        if transaction.provider_code == 'mollie' and fees_product_id:
            mollie_fees = transaction.payment_method_id._compute_fees(
                transaction.amount, transaction.partner_id.country_id, transaction.provider_id
            )
            self.env['sale.order.line'].create({
                'product_id': fees_product_id.id,
                'product_uom_qty': 1,
                'order_id': self.id,
                'price_unit': mollie_fees,
                'is_mollie_fees': True
            })


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_mollie_fees = fields.Boolean('Is Mollie Fees')

    def _show_in_cart(self):
        """ Exclude mollie fees line from showing up in the cart """
        return not self.is_mollie_fees and super()._show_in_cart()
