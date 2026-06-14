from freezegun import freeze_time
from odoo.exceptions import ValidationError

from odoo.tests import common, tagged

# odoo --config=config/local.conf --http-port=8075 --test-enable --test-tags=/binaural_pos:TestPosOrder --stop-after-init
@tagged('post_install', '-at_install')
class TestPosOrder(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.DiscountRule = cls.env["pos.order.hourly.discount.rule"]

    def _create_rule(self, name, hour_from, hour_to, discount=10.0):
        return self.DiscountRule.create({
            "name": name,
            "hour_from": hour_from,
            "hour_to": hour_to,
            "discount_percentage": discount,
        })
    def test_hour_from_greater_than_hour_to_raises_error(self):
        """hour_from > hour_to debe levantar ValidationError"""
        with self.assertRaises(ValidationError):
            self._create_rule("Invalid", 18.0, 14.0, 10.0)

    def test_update_to_invalid_range_raises_error(self):
        """Actualizar una regla existente con hour_from >= hour_to levanta error"""
        rule = self._create_rule("Test", 8.0, 18.0, 10.0)
        with self.assertRaises(ValidationError):
            rule.hour_from = 20.0
        with self.assertRaises(ValidationError):
            rule.hour_to = 5.0

    @freeze_time("2000-01-01 14:30:00")
    def test_matches_when_current_time_is_within_window(self):
        """Verifica que retorna la regla si la hora actual esta entre hour_from y hour_to"""
        self._create_rule("Happy Hour", 12.0, 18.0, 15.0)
        rule = self.env["pos.order"]._get_hourly_discount_rule()
        self.assertTrue(rule)
        self.assertEqual(rule.discount_percentage, 15.0)

    @freeze_time("2000-01-01 14:30:00")
    def test_returns_no_rule_when_no_window_matches(self):
        """Verifica que retorna vacio si la hora actual no esta en ninguna ventana"""
        self._create_rule("Morning", 6.0, 10.0, 5.0)
        rule = self.env["pos.order"]._get_hourly_discount_rule()
        self.assertFalse(rule)

    @freeze_time("2000-01-01 14:30:00")
    def test_returns_first_rule_when_multiple_overlap(self):
        """Verifica que retorna la primera regla (orden de creacion) si varias coinciden"""
        self._create_rule("First", 8.0, 20.0, 5.0)
        self._create_rule("Second", 12.0, 16.0, 10.0)
        rule = self.env["pos.order"]._get_hourly_discount_rule()
        self.assertEqual(rule.name, "First")

    @freeze_time("2000-01-01 14:30:00")
    def test_compares_decimal_hours_directly(self):
        """Verifica que compara floats directamente sin conversion de zona horaria"""
        self._create_rule("Match", 14.0, 15.0, 8.0)
        rule = self.env["pos.order"]._get_hourly_discount_rule()
        self.assertTrue(rule)

    @freeze_time("2000-01-01 14:30:00")
    def test_no_rules_returns_empty(self):
        """Verifica que retorna Recordset vacio si no hay reglas en la base"""
        rule = self.env["pos.order"]._get_hourly_discount_rule()
        self.assertFalse(rule)

