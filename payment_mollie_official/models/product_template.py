from odoo import models, exceptions, _

import logging

logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    def check_product(self):
        super().check_product()
        if self.sale_ok and self.supplier_is_owner:
            if not self.seller_ids[0].partner_id.mollie_partner_id:
                raise exceptions.ValidationError(_("Für den Lieferanten muss eine Mollie-ID hinterlegt sein!"))
            #if not self.mollie_customer_exists(self.seller_ids[0].partner_id.mollie_partner_id):
            #    raise exceptions.ValidationError(_("Ungültige Mollie-ID!"))
