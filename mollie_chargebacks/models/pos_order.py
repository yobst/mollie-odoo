from odoo import models
import logging

logger = logging.getLogger()

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _refund_rounting_reversals(self):
        self.ensure_one()
        refund_per_vendor = {}
        for line in self.orderline:
            if line.product_id.supplier_is_owner:
                vendor = line.product_id.vendor_id
                if vendor not in refund_per_vendor:
                    refund_per_vendor[vendor] = 0
                refund_per_vendor += line.price_subtotal_incl * -1 # amount is negative
        # maybe use _prepare_payment_payload instead and reverse amounts
            
        return [{'name': vendor.mollie_partner_id, 'amount': amount} for vendor, amount in refund_per_vendor.items()]
                
                    
    
    def _refund(self):
        self.ensure_one()
        
        payment_id = False #TODO
        route = f"https://api.mollie.com/v2/payments/{payment_id}/refunds"
