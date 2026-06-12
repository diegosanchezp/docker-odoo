from odoo.tests import common

# odoo --config=config/local.conf --http-port=8070 --test-enable --test-tags=/regla_reabastecimiento_prioridad:TestReglaReabastecimiento
class TestReglaReabastecimiento(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Crear un producto de nombre "Escritorio"
        cls.product_escritorio_id = cls.env["product.product"].create(
            {
                "name": "Escritorio",
                "is_storable": True,
            }
        )

    # odoo --config=local.conf --http-port=8070 --test-enable --test-tags=/regla_reabastecimiento_prioridad:TestReglaReabastecimiento.test_compute_pendiente_reabastecimiento
    def test_compute_pendiente_reabastecimiento(self):
        """Verifica que pendiente_reabastecimiento sea True cuando qty_available < stock_objetivo"""
        # Asignar de cantidad stock de stock 1 al product_escritorio_id
        self.env['stock.quant'].create({
            'product_id': self.product_escritorio_id.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 1.0,
        })

        # Le ponemos al stock_objetivo 2, 2 > 1
        self.product_escritorio_id.write({
            "stock_objetivo": 2,
        })

        # Forzamos la llamada para que trabaje con datos actualizados
        self.product_escritorio_id.product_tmpl_id._compute_pendiente_reabastecimiento()

        # pendiente_reabastecimiento deberia de ser true.
        self.assertTrue(self.product_escritorio_id.pendiente_reabastecimiento)

    # odoo --config=config/local.conf --http-port=8070 --test-enable --test-tags=/regla_reabastecimiento_prioridad:TestReglaReabastecimiento.test_identificar_stock_debajo
    def test_identificar_stock_debajo(self):
        """Verifica que _identificar_stock_debajo cree una mail.activity de tipo To-Do para el producto con stock bajo"""
        # Crear un stock.quant con cantidad 1 para que el producto tenga qty_available = 1
        self.env['stock.quant'].create({
            'product_id': self.product_escritorio_id.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 1.0,
        })

        # Poner stock_objetivo en 5 para que qty_available (1) < stock_objetivo (5) sea True
        self.product_escritorio_id.write({
            "stock_objetivo": 5,
        })

        # Forzar el compute para que pendiente_reabastecimiento quede en True y almacenado
        self.product_escritorio_id.product_tmpl_id._compute_pendiente_reabastecimiento()
        self.assertTrue(self.product_escritorio_id.pendiente_reabastecimiento)

        # Llamar al metodo que busca productos con pendiente_reabastecimiento = True
        # y crea actividades de tipo "To Do" para el responsable del almacen
        self.env['product.template']._identificar_stock_debajo()

        # Buscar la actividad creada para el producto "Escritorio"
        actividad = self.env['mail.activity'].search([
            ('res_model_id', '=', self.env['ir.model']._get('product.template').id),
            ('res_id', '=', self.product_escritorio_id.product_tmpl_id.id),
            ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
            ('automated', '=', True),
        ])

        # Verificar que se haya creado exactamente una actividad
        self.assertTrue(actividad)
        self.assertEqual(len(actividad), 1)

        # Verificar que sea de tipo "To Do"
        self.assertEqual(
            actividad.activity_type_id,
            self.env.ref('mail.mail_activity_data_todo'),
        )

        # Verificar que el responsable sea el administrador (fallback por defecto)
        self.assertEqual(
            actividad.user_id,
            self.env.ref('base.user_admin'),
        )

        # Verificar que la actividad esta marcada como automatica
        self.assertTrue(actividad.automated)

    # odoo --config=config/local.conf --http-port=8070 --test-enable --test-tags=/regla_reabastecimiento_prioridad:TestReglaReabastecimiento.test_identificar_stock_debajo_no_duplicados
    def test_identificar_stock_debajo_no_duplicados(self):
        """Verifica que llamar _identificar_stock_debajo dos veces no cree mail.activity duplicadas"""
        # Crear un stock.quant con cantidad 1 para que el producto tenga qty_available = 1
        self.env['stock.quant'].create({
            'product_id': self.product_escritorio_id.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 1.0,
        })

        # Poner stock_objetivo en 5 para que qty_available (1) < stock_objetivo (5) sea True
        self.product_escritorio_id.write({
            "stock_objetivo": 5,
        })

        # Forzar el compute para que pendiente_reabastecimiento quede en True y almacenado
        self.product_escritorio_id.product_tmpl_id._compute_pendiente_reabastecimiento()
        self.assertTrue(self.product_escritorio_id.pendiente_reabastecimiento)

        # Primera llamada a _identificar_stock_debajo - debe crear la actividad
        self.env['product.template']._identificar_stock_debajo()

        # Segunda llamada a _identificar_stock_debajo - NO debe crear duplicado
        self.env['product.template']._identificar_stock_debajo()

        # Buscar actividades creadas para el producto
        actividades = self.env['mail.activity'].search([
            ('res_model_id', '=', self.env['ir.model']._get('product.template').id),
            ('res_id', '=', self.product_escritorio_id.product_tmpl_id.id),
            ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
            ('automated', '=', True),
        ])

        # Verificar que solo exista una actividad, no dos
        self.assertEqual(len(actividades), 1)

