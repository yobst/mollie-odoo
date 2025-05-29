from odoo import _, exceptions, models
import logging

logger = logging.getLogger()

class MolliePosTerminal(models.Model):
    _inherit = 'mollie.pos.terminal'
        
    def _prepare_payment_payload(self, data):
        payload = super()._prepare_payment_payload(data) # check if amounts negative
        
        if data['amount'] < 0:
            payload['reverseRouting'] = payload.pop('routing') # check if negative values
            
        return payload

    def _api_make_payment_request(self, data):
        payment_payload = self._prepare_payment_payload(data)
        logger.info('Mollie POS Terminal Payload: %s', str(payment_payload))
        if data['amount'] < 0:
            if len(self.refunded_order_ids.payment_ids) == 0:
                raise exceptions.ValidationError(_("Keinen bezahlten Ursprungsauftrag für diesen Rückerstattungsauftrag gefunden!"))
        
            payment_id = self.refunded_order_ids.payment_ids[0].transaction_id # von Modell pos.payment
            result = self._mollie_api_call(f'/payments/{payment_id}/refunds"', data=payment_payload, method='POST', silent=True)
        else:
            result = self._mollie_api_call('/payments', data=payment_payload, method='POST', silent=True)
        self.env['mollie.pos.terminal.payments']._create_mollie_payment_request(result, {**data, 'terminal_id': self.id})
        return result
