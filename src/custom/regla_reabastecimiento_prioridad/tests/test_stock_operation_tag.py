from odoo.fields import Command
from odoo.tests import common

# odoo --config=config/local.conf --http-port=8070 --test-enable --test-tags=/regla_reabastecimiento_prioridad:TestStockOperationTag
class TestStockOperationTag(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.picking_type = cls.env["stock.picking.type"].create({
            "name": "Test Picking Type",
            "sequence_code": "TEST",
        })
        cls.product = cls.env["product.product"].create({"name": "Test Product", "is_storable": True})
        cls.product_tmpl = cls.product.product_tmpl_id

    def test_create_tag(self):
        """Verifica que se pueda crear una etiqueta con nombre, descripción y
        tipo de operación, y que el color se asigne automáticamente en el rango 1-11"""
        tag = self.env["stock.operation.tag"].create({
            "name": "Alta Prioridad",
            "description": "Productos con alta prioridad de despacho",
            "operation_type": self.picking_type.id,
        })
        self.assertTrue(tag)
        self.assertEqual(tag.name, "Alta Prioridad")
        self.assertEqual(tag.description, "Productos con alta prioridad de despacho")
        self.assertEqual(tag.operation_type, self.picking_type)
        self.assertIn(tag.color, range(1, 12))

    def test_assign_tag_to_product(self):
        """Verifica que una etiqueta se pueda asignar a un producto a través
        del Many2many product_template_ids usando Command.link, y que la
        relación sea bidireccional"""
        tag = self.env["stock.operation.tag"].create({
            "name": "Fragil",
            "operation_type": self.picking_type.id,
        })
        tag.write({"product_template_ids": [Command.link(self.product_tmpl.id)]})
        self.assertIn(self.product_tmpl, tag.product_template_ids)
        self.assertIn(tag, self.product_tmpl.stock_operation_tag_ids)

    def test_assign_multiple_tags_to_product(self):
        """Verifica que se puedan asignar varias etiquetas a un producto en
        una sola operación usando Command.set, y que ambas queden vinculadas"""
        tag1 = self.env["stock.operation.tag"].create({"name": "Fragil"})
        tag2 = self.env["stock.operation.tag"].create({"name": "Voluminoso"})
        self.product_tmpl.write({
            "stock_operation_tag_ids": [Command.set([tag1.id, tag2.id])],
        })
        self.assertIn(tag1, self.product_tmpl.stock_operation_tag_ids)
        self.assertIn(tag2, self.product_tmpl.stock_operation_tag_ids)
        self.assertEqual(len(self.product_tmpl.stock_operation_tag_ids), 2)

    def test_tag_without_operation_type(self):
        """Verifica que el campo operation_type sea opcional al crear
        una etiqueta"""
        tag = self.env["stock.operation.tag"].create({"name": "Standalone"})
        self.assertFalse(tag.operation_type)
