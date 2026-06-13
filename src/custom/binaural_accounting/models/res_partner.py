from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    fiscal_profile = fields.Many2one(
        comodel_name="account.fiscal.profile",
        string="Perfil Fiscal",
    )

