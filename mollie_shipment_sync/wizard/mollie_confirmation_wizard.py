# -*- coding: utf-8 -*-

from odoo import fields, models, api


class MollieConfirmationWizard(models.TransientModel):
    _name = 'mollie.confirmation.wizard'

    sync = fields.Boolean("Order Quantity changed, Do you wan't Update quantity with mollie?")
    wizard_line_ids = fields.One2many('mollie.confirmation.wizard.line', 'wizard_id', string='Wizard Line')
    shipping_line_qty_increase = fields.Boolean('Shipping Line Qty Increase')
    wizard_line_count = fields.Integer(compute='_compute_wizard_line_count', string='Wizard Line Count')

    @api.depends('wizard_line_ids')
    def _compute_wizard_line_count(self):
        self.wizard_line_count = len(self.wizard_line_ids)

    def confirm(self):
        if self.sync:
            transaction = self.env.context.get('transaction')
            transaction_id = self.env['payment.transaction'].browse(int(transaction))
            order_reference = self.env.context.get('order_reference')
            order_data = self.env.context.get('order_data')
            order_status = self.env.context.get('status')
            transaction_id.provider_id._api_mollie_manage_order(order_reference, order_data, order_status, silent_errors=False)
            self.env['sale.order'].browse(self.env.context.get('active_id')).mollie_need_shipment_sync = False


class MollieConfirmationWizardLine(models.TransientModel):
    _name = 'mollie.confirmation.wizard.line'

    product_id = fields.Many2one('product.product', string='Product')
    quantity_at_odoo = fields.Float('Quantity At Odoo')
    quantity_in_mollie = fields.Float('Quantity In Mollie')
    diffrence = fields.Float('Diffrence')
    wizard_id = fields.Many2one('mollie.confirmation.wizard', string='wizard')
