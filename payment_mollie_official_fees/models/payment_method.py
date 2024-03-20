# -*- coding: utf-8 -*-

from odoo import models, fields


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    fees_active = fields.Boolean(string="Add Extra Fees")
    fees_dom_fixed = fields.Float(string="Fixed domestic fees")
    fees_dom_var = fields.Float(string="Variable domestic fees (in percents)")
    fees_int_fixed = fields.Float(string="Fixed international fees")
    fees_int_var = fields.Float(string="Variable international fees (in percents)")

    def _compute_fees(self, amount, country, provider):
        """ This method compute fees for the mollie method configuration.

        :param float amount: amount for fees
        :param recordset country: The customer country, as a `res.country` record
        :param recordset provider: The provider of the transaction, as a `payment.provider` record
        :return: fees for the mollie method
        :rtype: float
        """
        self.ensure_one()
        fees = 0.0
        if self.fees_active:
            if country == provider.company_id.country_id:
                fixed = self.fees_dom_fixed
                variable = self.fees_dom_var
            else:
                fixed = self.fees_int_fixed
                variable = self.fees_int_var
            fees = (amount * variable / 100.0 + fixed)
            if provider.mollie_fees_product_id.taxes_id:
                fees = provider.mollie_fees_product_id.taxes_id.compute_all(fees, product=provider.mollie_fees_product_id)['total_included']
        return fees
