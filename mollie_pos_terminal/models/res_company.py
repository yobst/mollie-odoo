from odoo import models, fields, _


class Company(models.Model):
    _inherit = 'res.company'

    mollie_terminal_api_key = fields.Char(string="Mollie Terminal Api Key")
    mollie_allow_payment_splits = fields.Boolean(string="Mollie Allow Payment Splits")
