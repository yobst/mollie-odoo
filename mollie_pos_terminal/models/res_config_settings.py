from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mollie_terminal_api_key = fields.Char(related='company_id.mollie_terminal_api_key', string='Mollie Terminal Api Key', readonly=False)
    mollie_allow_payment_splits = fields.Boolean(related='company_id.mollie_allow_payment_splits', string='Mollie Allow Payment Splits', readonly=False)
