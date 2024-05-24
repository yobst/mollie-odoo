# -*- coding: utf-8 -*-

from odoo.osv import expression
from odoo import api, fields, models

class MolliePaymentMethod(models.Model):
    _name = 'mollie.payment.method'
    _description = 'Mollie payment method'
    _order = "sequence, id"

    name = fields.Char(translate=True)
    sequence = fields.Integer()
    provider_id = fields.Many2one('payment.provider', string='Provider')  # This will be always mollie
    method_code = fields.Char(string="Method code")
    payment_icon_ids = fields.Many2many('payment.icon', string='Supported Payment Icons')
    active = fields.Boolean(default=True)
    active_on_shop = fields.Boolean(string="Enabled on shop", default=True)
    country_ids = fields.Many2many('res.country', string='Country Availability')
    mollie_voucher_ids = fields.One2many('mollie.voucher.line', 'method_id', string='Mollie Voucher Config')
    company_id = fields.Many2one(related="provider_id.company_id")
    enable_qr_payment = fields.Boolean(string="Enable QR payment")

    # Hidden fields that are used for filtering methods
    supports_order_api = fields.Boolean(string="Supports Order API")
    supports_payment_api = fields.Boolean(string="Supports Payment API")
    payment_issuer_ids = fields.Many2many('mollie.payment.method.issuer', string='Issuers')

    # Fees fields
    fees_active = fields.Boolean(string="Add Extra Fees")
    fees_dom_fixed = fields.Float(string="Fixed domestic fees")
    fees_dom_var = fields.Float(string="Variable domestic fees (in percents)")
    fees_int_fixed = fields.Float(string="Fixed international fees")
    fees_int_var = fields.Float(string="Variable international fees (in percents)")

    # Fees fields
    journal_id = fields.Many2one(
        'account.journal', string="Journal",
        compute='_compute_journal_id', inverse='_inverse_journal_id',
        domain="[('type', '=', 'bank'), ('company_id', '=', company_id)]")

    def _compute_journal_id(self):
        for mollie_method in self:
            payment_method = self.env['account.payment.method.line'].search([
                ('journal_id.company_id', '=', mollie_method.company_id.id),
                ('code', '=', mollie_method._get_journal_method_code()),
            ], limit=1)
            if payment_method:
                mollie_method.journal_id = payment_method.journal_id
            else:
                mollie_method.journal_id = False

    def _inverse_journal_id(self):
        for mollie_method in self:
            payment_method_line = self.env['account.payment.method.line'].search([
                ('journal_id.company_id', '=', mollie_method.company_id.id),
                ('code', '=', mollie_method._get_journal_method_code())
            ], limit=1)
            if mollie_method.journal_id:
                if not payment_method_line:
                    default_payment_method_id = mollie_method._get_default_mollie_payment_method_id()
                    existing_payment_method_line = self.env['account.payment.method.line'].search([
                        ('payment_method_id', '=', default_payment_method_id),
                        ('journal_id', '=', mollie_method.journal_id.id)
                    ], limit=1)
                    if not existing_payment_method_line:
                        self.env['account.payment.method.line'].create({
                            'payment_method_id': default_payment_method_id,
                            'journal_id': mollie_method.journal_id.id,
                        })
                else:
                    payment_method_line.journal_id = mollie_method.journal_id
            elif payment_method_line:
                payment_method_line.unlink()

    def _get_journal_method_code(self):
        self.ensure_one()
        return f'mollie_{self.method_code}'

    def _get_default_mollie_payment_method_id(self):
        method_code = self._get_journal_method_code()
        payment_method = self.env['account.payment.method'].search([
            ('code', '=', method_code),
            ('payment_type', '=', 'inbound')
        ], limit=1)
        if not payment_method:
            payment_method = self.env['account.payment.method'].create({
                'name': f'Mollie {self.name}',
                'code': method_code,
                'payment_type': 'inbound',
            })
        return payment_method.id

    def _compute_fees(self, amount, currency, country):
        """ This method compute fees for the mollie method configuration.

        :param float amount: amount for fees
        :param recordset currency: The currency of the transaction, as a `res.currency` record
        :param recordset country: The customer country, as a `res.country` record
        :return: fees for the mollie method
        :rtype: float
        """
        self.ensure_one()
        fees = 0.0
        if self.fees_active:
            if country == self.provider_id.company_id.country_id:
                fixed = self.fees_dom_fixed
                variable = self.fees_dom_var
            else:
                fixed = self.fees_int_fixed
                variable = self.fees_int_var
            fees = (amount * variable / 100.0 + fixed) / (1 - variable / 100.0)
        return fees

    def _mollie_show_creditcard_option(self):
        if self.method_code != 'creditcard':
            return False
        provider_sudo = self.sudo().provider_id
        self.env.user._mollie_validate_customer_id(self.provider_id)
        if provider_sudo.mollie_profile_id and provider_sudo.sudo().mollie_use_components:
            return True
        if provider_sudo.sudo().mollie_show_save_card and not self.env.user.has_group('base.group_public'):
            return True

        return False


class MolliePaymentIssuers(models.Model):
    _name = 'mollie.payment.method.issuer'
    _description = 'Mollie payment method issuers'
    _order = "sequence, id"

    name = fields.Char(translate=True)
    sequence = fields.Integer()
    provider_id = fields.Many2one('mollie.payment.method', string='Provider')
    payment_icon_ids = fields.Many2many('payment.icon', string='Supported Payment Icons')
    issuers_code = fields.Char()
    active = fields.Boolean(default=True)


class MollieVoucherLines(models.Model):
    _name = 'mollie.voucher.line'
    _description = 'Mollie voucher method'

    method_id = fields.Many2one('mollie.payment.method', string='Mollie Method')
    category_ids = fields.Many2many('product.category', string='Product Categories')
    product_ids = fields.Many2many('product.template', string='Products')
    mollie_voucher_category = fields.Selection([('meal', 'Meal'), ('eco', 'Eco'), ('gift', 'Gift')], required=True)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_mollie_voucher_category(self):
        domain = [('product_ids', 'in', self.ids)]
        categories = self.mapped('categ_id')
        if categories:
            domain = expression.OR([domain, [('category_ids', 'parent_of', categories.ids)]])
        voucher_line = self.env['mollie.voucher.line'].search(domain, limit=1)
        return voucher_line and voucher_line.mollie_voucher_category or False

class MollieContact(models.Model):
    _inherit = 'res.partner'

    mollie_partner_id = fields.Char(string="Mollie Partner ID", default="")


class MolliePosOrderLine(models.Model):
    _inherit = 'pos.order.line'
    mollie_partner_id = fields.Char(string="Mollie Partner ID")

    @api.model_create_multi
    def create(self, values_list):
        lines = super().create(values_list)
        for line in lines:
            supplierInfo = self.env['product.supplierinfo'].search([
                    ('product_tmpl_id', '=', line.product_id.id)
                ], limit=1)
            partner = self.env['res.partner'].search([
                ('id', '=', supplierInfo.partner_id.id)
            ], limit=1)
            line.mollie_partner_id = partner.mollie_partner_id
        return lines
    
class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _compute_splits(self):
        """ This method compute payment splits for the mollie method configuration.

        :param int order_id: order ID
        :return: payment splits for the mollie method
        :rtype: vector of payment records
        """
        splits = []
        splitMap = {}

        for line in self.lines.filtered(lambda l: not l.display_type):
            if line.mollie_partner_id in splitMap:
                splitMap[line.mollie_partner_id] += line.price_subtotal_incl
            else:
                splitMap[line.mollie_partner_id] = line.price_subtotal_incl

        for id, amount in splitMap.items():
            splits.append((id, amount))
        return splits
    

class MollieProductTemplate(models.Model):
    _inherit = 'product.template'

    seller_id = fields.one2Many('res.partner', string='Product Seller')

class MollieProductProduct(models.Model):
    _inherit = 'product.product'

    mollie_partner_id = fields.Char(compute='_compute_mollie_id', store=True)

    @api.depends('product_tmpl_id')
    def _compute_mollie_id(self):
        partner_id = self.product_tmpl_id.seller_id
        self.mollie_partner_id = partner_id.mollie_partner_id