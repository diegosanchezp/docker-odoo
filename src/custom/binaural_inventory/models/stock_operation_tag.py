from random import randint
from odoo import api, fields, models

class StockOperationTag(models.Model):
    """
    Permitir clasificar productos con etiquetas
    operativas para optimizar picking, almacenamiento y despacho
    """
    _name = 'stock.operation.tag'
    _description = 'Partner Tags'


    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Nombre', required=True, translate=True)
    color = fields.Integer(string='Color', default=_get_default_color, aggregator=False)
    description = fields.Char('Descripcion')

    product_template_ids = fields.Many2many(
        "product.template",
        string="Productos"
    )

    operation_type = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Tipo de Operación",
        required=True,
    )
