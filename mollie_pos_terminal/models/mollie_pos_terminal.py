import logging
import requests
from werkzeug import urls

from odoo import fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MolliePosTerminal(models.Model):
    _name = 'mollie.pos.terminal'
    _description = 'Mollie Pos Terminal'

    name = fields.Char()
    terminal_id = fields.Char('Terminal ID')
    profile_id = fields.Char('Profile ID')
    serial_number = fields.Char('Serial Number')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ])
    currency_id = fields.Many2one('res.currency', string='Currency')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    def _sync_mollie_terminals(self):
        existing_terminals = self.search([])
        terminals_data = self._api_get_terminals()  # TODO: manage pager for 250+ terminals

        if not terminals_data.get('count'):
            return

        for terminal in terminals_data['_embedded']['terminals']:
            terminal_found = existing_terminals.filtered(lambda x: x.terminal_id == terminal['id'])
            currency = self.env['res.currency'].search([('name', '=', terminal['currency'])])

            if not currency:
                raise ValidationError(_('Currency ') + terminal['currency'] + _(' is not active. Please activate it first.'))

            terminal_data = {
                'name': terminal['description'],
                'terminal_id': terminal['id'],
                'profile_id': terminal['profileId'],
                'serial_number': terminal['serialNumber'],
                'status': terminal['status'],
                'currency_id': currency.id
            }
            if terminal_found:
                terminal_found.write(terminal_data)
            else:
                self.create(terminal_data)

    # =================
    # API CALLS METHODS
    # =================

    def _api_get_terminals(self):
        """ Fetch terminals data from mollie api """
        return self._mollie_api_call('/terminals', method='GET')

    def _api_make_payment_request(self, data):
        payment_payload = self._prepare_payment_payload(data)
        _logger.info('Mollie POS Terminal Payload on: %s', str(payment_payload))
        result = self._mollie_api_call('/payments', data=payment_payload, method='POST', silent=True)
        self.env['mollie.pos.terminal.payments']._create_mollie_payment_request(result, {**data, 'terminal_id': self.id})
        return result

    def _api_cancel_mollie_payment(self, transaction_id):
        return self.sudo()._mollie_api_call(f'/payments/{transaction_id}', method='DELETE', silent=True)

    def _api_get_mollie_payment_status(self, transaction_id):
        return self.sudo()._mollie_api_call(f'/payments/{transaction_id}', method='GET', silent=True)

    def _prepare_payment_payload(self, data):
        base_url = self.get_base_url()
        webhook_url = urls.url_join(base_url, '/pos_mollie/webhook/')
        splits = []
        fee = 0.8
        for line in data['lines']:
            amount = line['price'] * line['quantity'] * fee
            product = self.env['product.product'].search([
                    ('id', '=', line['product_id'])
                ], limit=1)
            if product:
                seller_id = product.variant_seller_ids[0]
                if seller_id:
                    partner_id = seller_id.partner_id
                    if partner_id:
                        mollie_partner_id = partner_id.mollie_partner_id
                        if mollie_partner_id:
                            splits.append((mollie_partner_id, f"{amount:.2f}"))
                        else:
                            raise ValidationError(_('Mollie ID for partner ') + str(partner_id.id) + _(' not found. Please add a Mollie ID.'))
                    else:
                        raise ValidationError(_('Partner ID for') + str(seller_id.id) + _(' not found. Please add a Mollie ID.'))
                else:
                    raise ValidationError(_('No seller for product  ') + str(product.id) + _(' found. Please add a seller id.'))
            else:
                raise ValidationError(_('Product ') + str(line['product_id']) + _(' not found. Please create it.'))

        routing_data = self._prepare_routing_payload(splits, data['curruncy'])
        return {
            "amount": {
                "currency": data['curruncy'],
                "value": f"{data['amount']:.2f}"
            },
            "description": data['description'],
            "webhookUrl": webhook_url,
            "redirectUrl": webhook_url,
            "method": "pointofsale",
            "terminalId": self.terminal_id,
            "metadata": {
                "mollie_uid": data['mollie_uid'],
                "order_id": data['order_id'],
            },
            "routing": routing_data
        }
    
    def _prepare_routing_payload(self, splits, currency):
        routing_payload = []
        for split in splits:
            payload = {
                'amount': {
                    'currency': currency,
                    'value': split[1]
                },
                'destination': {
                    'type': 'organization',
                    'organizationId': split[0]
                }
            }
            routing_payload.append(payload)
        return routing_payload

    # =====================
    # GENERIC TOOLS METHODS
    # =====================

    def _mollie_api_call(self, endpoint, data=None, method='POST', silent=False):
        company = self.company_id or self.env.company

        headers = {
            'content-type': 'application/json',
            "Authorization": f'Bearer {company.mollie_terminal_api_key}',
        }

        endpoint = f'/v2/{endpoint.strip("/")}'
        url = urls.url_join('https://api.mollie.com/', endpoint)

        _logger.info('Mollie POS Terminal CALL on: %s', url)

        try:
            response = requests.request(method, url, json=data, headers=headers, timeout=60)
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            error_details = response.json()
            _logger.exception("MOLLIE-POS-ERROR \n %s", error_details)
            if silent:
                return error_details
            else:
                raise ValidationError("MOLLIE: \n %s" % error_details)
        except requests.exceptions.RequestException as e:
            _logger.exception("unable to communicate with Mollie: %s \n %s", url, e)
            if silent:
                return {'error': "Some thing went wrong"}
            else:
                raise ValidationError("Mollie: " + _("Some thing went wrong."))
        return response.json()

    def show_form_and_tree(self):
        action = self.env['ir.actions.actions']._for_xml_id('mollie_pos_terminal.mollie_pos_terminal_payments_action')
        action.update({
            'domain': [('terminal_id', '=', self.id)],
            'views': [(self.env.ref('mollie_pos_terminal.mollie_pos_terminal_payments_view_tree').id, 'tree'), (self.env.ref('mollie_pos_terminal.mollie_pos_terminal_payments_view_form').id, 'form')],
            'res_id': self.id,
        })
        return action
