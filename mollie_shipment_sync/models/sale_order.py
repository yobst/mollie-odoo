# -*- coding: utf-8 -*-

from odoo import _, api, fields, models, Command


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    mollie_payment = fields.Boolean(compute='_compute_mollie_payment')
    mollie_need_shipment_sync = fields.Boolean(compute='_compute_mollie_need_shipment_sync', store=True, default=False)

    def mollie_sync_shipment_data(self):
        return self._mollie_sync_shipment_data('wizard')

    def _mollie_sync_shipment_data(self, cancelation_mode):
        transaction = self._mollie_get_valid_transaction()
        if transaction:
            data = transaction.provider_id._api_mollie_get_payment_data(transaction.provider_reference)
            shipment_lines = []
            manage_order_lines = []
            order_qty_diff = []
            shipping_line_qty_increase = False
            mollie_sync_lines = self.env['sale.order.line']
            if data and data.get('lines'):
                order_status = data.get('status')
                for mollie_line in data.get('lines'):
                    if mollie_line.get('status') == 'canceled':
                        continue
                    mollie_line_metadata = mollie_line.get('metadata')
                    order_reference = data.get('id')
                    if mollie_line_metadata:
                        order_line = self.order_line.filtered(lambda l: l.id == mollie_line_metadata.get('line_id'))
                        if order_line:
                            mollie_sync_lines += order_line
                            if order_line.qty_delivered > mollie_line['quantityShipped']:
                                qty_to_ship = order_line.qty_delivered - mollie_line['quantityShipped']
                                if qty_to_ship and mollie_line.get('shippableQuantity') >= qty_to_ship:
                                    shipment_lines.append({
                                        'id': mollie_line['id'],
                                        'quantity': int(qty_to_ship)    # mollie does not support float values
                                    })
                            mollie_line_order_qty = mollie_line['quantity'] - mollie_line['quantityCanceled']
                            if mollie_line_order_qty != order_line.product_uom_qty:
                                if order_status in ('created', 'pending', 'authorized'):
                                    if order_line.product_uom_qty:
                                        manage_order_lines.append({
                                            'operation': 'update',
                                            'data': {
                                                'id': mollie_line['id'],
                                                'quantity': int(order_line.product_uom_qty),
                                                'unitPrice': {
                                                    'currency': order_line.currency_id.name,
                                                    'value': "%.2f" % order_line.price_reduce_taxinc
                                                },
                                                'totalAmount': {
                                                    'currency': order_line.currency_id.name,
                                                    'value': "%.2f" % order_line.price_total,
                                                },
                                                'vatRate': "%.2f" % sum(order_line.tax_id.mapped('amount')),
                                                'vatAmount': {
                                                    'currency': order_line.currency_id.name,
                                                    'value': "%.2f" % order_line.price_tax,
                                                }
                                            }
                                        })
                                    elif not order_line.product_uom_qty and mollie_line['isCancelable']:
                                        manage_order_lines.append({
                                            'operation': 'cancel',
                                            'data': {
                                                'id': mollie_line['id'],
                                            }
                                        })
                                elif order_status == 'shipping' and mollie_line.get('status') in ['shipping', 'authorized']:
                                    if order_line.product_uom_qty < mollie_line_order_qty:  # shipping state order only reduce quantity sync
                                        if order_line.product_uom_qty:
                                            manage_order_lines.append({
                                                'id': mollie_line['id'],
                                                'quantity': mollie_line_order_qty - order_line.product_uom_qty
                                            })
                                        else:
                                            manage_order_lines.append({
                                                'id': mollie_line['id'],
                                            })
                                    elif order_line.product_uom_qty > mollie_line_order_qty:
                                        shipping_line_qty_increase = True
                                        continue  # shipping line quanity increase, not sync with mollie
                                else:
                                    continue  # other status line not sync with mollie
                                if cancelation_mode == 'wizard':
                                    order_qty_diff.append(Command.create({
                                        'product_id': order_line.product_id.id,
                                        'quantity_at_odoo': order_line.product_uom_qty,
                                        'quantity_in_mollie': mollie_line_order_qty,
                                        'diffrence': order_line.product_uom_qty - mollie_line_order_qty
                                    }))
                if shipment_lines:
                    transaction.provider_id._api_mollie_sync_shipment(transaction.provider_reference, {'lines': shipment_lines})
                if order_status in ('created', 'pending', 'authorized'):
                    diff_lines = self.order_line - mollie_sync_lines
                    if diff_lines:
                        order_lines_data = transaction._mollie_get_order_lines(self)
                        for line_data in order_lines_data:
                            order_line = line_data['metadata']['line_id']
                            if order_line in diff_lines.ids and line_data['quantity'] > 0:
                                manage_order_lines.append({
                                    'operation': 'add',
                                    'data': line_data
                                })
                        for order_line in diff_lines:
                            if cancelation_mode == 'wizard' and order_line.product_uom_qty:
                                order_qty_diff.append(Command.create({
                                    'product_id': order_line.product_id.id,
                                    'quantity_at_odoo': order_line.product_uom_qty,
                                    'quantity_in_mollie': 0.0,
                                    'diffrence': order_line.product_uom_qty
                                }))
                if cancelation_mode in ('wizard', 'auto_sync'):
                    key = 'lines' if order_status == 'shipping' else 'operations'
                    order_line_data = {
                        key: manage_order_lines
                    }
                if manage_order_lines or shipping_line_qty_increase:
                    if cancelation_mode == 'wizard':
                        return self.sync_order_line_confirmation(transaction, order_reference, order_line_data, order_qty_diff, order_status, shipping_line_qty_increase)
                    elif cancelation_mode == 'generate_activity':
                        self.activity_schedule(
                            'mollie_shipment_sync.mail_activity_mollie_exception',
                            summary='Sync Shipment',
                            note=_('Order quantity not match with mollie, manually sync with mollie.'),
                            user_id=self.user_id.id)
                    elif cancelation_mode == 'auto_sync':
                        transaction.provider_id._api_mollie_manage_order(order_reference, order_line_data, order_status, silent_errors=True)
                elif not manage_order_lines and cancelation_mode == 'wizard':
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _("Nothing to sync."),
                            'type': 'success',
                            'sticky': False,
                        },
                    }

        # For all the cases we will un-mark the sales orders
        self.mollie_need_shipment_sync = False

    def sync_order_line_confirmation(self, transaction, order_reference, order_data, order_qty_diff, status, shipping_line_qty_increase=False):
        return {
            'name': _("Confirm dialog"),
            'type': 'ir.actions.act_window',
            'res_model': 'mollie.confirmation.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                'status': status,
                'transaction': transaction.id,
                'order_reference': order_reference,
                'order_data': order_data,
                'default_wizard_line_ids': order_qty_diff,
                'default_shipping_line_qty_increase': shipping_line_qty_increase
            },
            'view_id': self.env.ref('mollie_shipment_sync.mollie_confirmation_wizard_view_form').id,
            'target': 'new',
        }

    def _compute_mollie_payment(self):
        for order in self:
            valid_transaction = order._mollie_get_valid_transaction()
            order.mollie_payment = len(valid_transaction) >= 1

    @api.depends('order_line.qty_delivered', 'order_line.product_uom_qty')
    def _compute_mollie_need_shipment_sync(self):
        for order in self:
            if order.mollie_payment:
                order.mollie_need_shipment_sync = True
            else:
                order.mollie_need_shipment_sync = False

    def _mollie_get_valid_transaction(self):
        self.ensure_one()
        return self.transaction_ids.filtered(lambda t: t.provider_id.code == 'mollie' and t.state in ['authorized', 'done'] and t.provider_reference.startswith("ord_"))

    def _cron_mollie_sync_shipment(self):
        mollie_provider = self.env.ref('payment.payment_provider_mollie')
        if mollie_provider.mollie_auto_sync_shipment:
            cancelation_mode = mollie_provider.reduce_quantity_action
            orders = self.search([('mollie_need_shipment_sync', '=', True)])
            for order in orders:
                order._mollie_sync_shipment_data(cancelation_mode)
                self.env.cr.commit()
        return True
