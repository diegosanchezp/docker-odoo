from odoo import models, fields

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_computed_taxes(self):
        tax_ids = super()._get_computed_taxes()

        # Añadir los taxes definidos del perfil fiscal
        fiscal_profile = self.move_id.partner_id.fiscal_profile
        if self.move_id.partner_id and fiscal_profile:
            tax_ids |= fiscal_profile.tax_id

        return tax_ids

