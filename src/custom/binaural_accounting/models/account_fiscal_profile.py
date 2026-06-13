from odoo import models, fields


class AccountFiscalProfile(models.Model):
    _name = "account.fiscal.profile"
    _description = "Perfil fiscal"

    name = fields.Char(
        string="Nombre",
        help="Nombre del perfil fiscal",
    )

    tax_id = fields.Many2one(
        string="Impuesto",
        help="Puede ser un grupo de impuesto o impuesto normal",
        comodel_name="account.tax",
    )
