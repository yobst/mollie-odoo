from odoo import _, fields, models
from odoo.tools import float_is_zero

import logging

logger = logging.getLogger()

class PosMakepayment(models.Model):
    _inherit = 'pos.make.pament'
    
    def _default_name(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            order = self.env['pos.order'].browse(active_id)
            return _("Auftrag %s", order.name)
        return False
    
    payment_name = fields.Char(string='Payment Reference', default=_default_name)

    def _default_amount(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            order = self.env['pos.order'].browse(active_id)
            amount_total = order.amount_total
            # If we refund the entire order, we refund what was paid originally, else we refund the value of the items returned
            if float_is_zero(order.refunded_order_ids.amount_total + order.amount_total, precision_rounding=order.currency_id.rounding):
                amount_total = -order.refunded_order_ids.amount_paid
            return amount_total - order.amount_paid
        return False
    