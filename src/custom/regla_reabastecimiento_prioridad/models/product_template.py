# from odoo import models, fields, api

from odoo.orm.domains import Domain

from odoo import api, fields, models, tools

class ProductTemplate(models.Model):
    _inherit = "product.template"

    prioridad_reabastecimiento = fields.Selection(
        string="Prioridad de Reabastecimiento",
        selection=[
            ("baja", "Baja"),
            ("media", "Media"),
            ("alta", "Alta"),
        ],
    )

    stock_objetivo = fields.Integer(
        string="Stock objetivo",
    )

    pendiente_reabastecimiento = fields.Boolean(
        string="Pendiente de reabastecer",
        compute="_compute_pendiente_reabastecimiento",
        # Se guarda el valor de este campo
        store=True,
    )

    @api.depends("pendiente_reabastecimiento", "qty_available")
    def _compute_pendiente_reabastecimiento(self):
        """
        Determina si el producto esta pendiente por reabastecer

        Un producto esta pendiente de reabastecer si la cantidad en stock del producto es menor a del stock objetivo (qty_available < stock_objetivo)
        """
        for product in self:
            product.pendiente_reabastecimiento = product.qty_available < product.stock_objetivo


    @api.model
    def _identificar_stock_debajo(self):
        """
        Acción automática ejecutada por una acción planificada (cronjob) que identifica productos con stock debajo menor a stock_objetivo
        """

        # Ver addons/stock/security/stock_security.xml
        # Ver addons/mail/models/mail_activity.py


        # Obtener productos con menos cantidad que el stock objetivo
        productos_reabastecer = self.env["product.template"].search(Domain("pendiente_reabastecimiento", "=", True))

        todo_activity_type_id = self.env.ref("mail.mail_activity_data_todo")
        product_template_res_model_id = self.env['ir.model']._get('product.template').id
        for product in productos_reabastecer:
            self.env["stock.move.line"].search(Domain("product_id", "=", product.id))
            # Obtener el responsable de almacen
            # El responsable del almacen es el usuario encargado del almacen en donde esta guardado el producto
            # Se puede obtener del warehouse de donde se ubica el producto
            warehouse_user_id = product.property_stock_inventory.warehouse_id.partner_id.user_id

            # Si no hay usuario responsable, entonces asumimos que el usuario administrador es el responsable
            if not warehouse_user_id:
                warehouse_user_id = self.env.ref("base.user_admin")


            # Verificar si ya existe una actividad automatizada del mismo tipo para este producto
            existing = self.env['mail.activity'].search([
                ('res_model_id', '=', product_template_res_model_id),
                ('res_id', '=', product.id),
                ('activity_type_id', '=', todo_activity_type_id.id),
                ('automated', '=', True),
            ], limit=1)

            if existing:
                continue

            # Asignar actividad de tipo todo a el responsable del almacen indicandole que debe reabastecer el producto.
            self.env['mail.activity'].create({
                'activity_type_id': todo_activity_type_id.id,
                'automated': True,
                'res_id': product.id,
                'res_model_id': product_template_res_model_id,
                "summary": f"El producto {product.name} esta pendiente por reabastecer",
                'user_id': warehouse_user_id.id,
            })

