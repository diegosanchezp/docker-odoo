from odoo.tests import common, tagged
from odoo.exceptions import ValidationError


# odoo --config=config/local.conf --http-port=8075 --test-enable --test-tags=/binaural_pos:TestHourlyDiscountRule
@tagged('post_install', '-at_install')
class TestHourlyDiscountRule(common.TransactionCase):
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

    # ── constraint validation tests ──

    def test_hour_from_less_than_hour_to_succeeds(self):
        """hour_from < hour_to crea la regla sin errores"""
        rule = self._create_rule("Valid", 14.0, 18.0, 10.0)
        self.assertTrue(rule)

    def test_hour_from_equal_to_hour_to_raises_error(self):
        """hour_from == hour_to debe levantar ValidationError (rango invalido)"""
        with self.assertRaises(ValidationError):
            self._create_rule("Invalid", 14.5, 14.5, 10.0)

    # ── overlap validation tests ──

    def test_adjacent_ranges_at_boundary_are_valid(self):
        """[0,2] y [2,4] comparten solo el borde — NO se superponen, es valido"""
        self._create_rule("First", 0.0, 2.0)
        self._create_rule("Second", 2.0, 4.0)

    def test_contained_subrange_raises_error(self):
        """[0,24] ya contiene [0,2] — debe levantar ValidationError"""
        self._create_rule("Full Day", 0.0, 24.0)
        with self.assertRaises(ValidationError):
            self._create_rule("Partial", 0.0, 2.0)

    def test_containing_range_raises_error(self):
        """[0,2] no puede crear [0,24] porque lo engloba"""
        self._create_rule("Partial", 0.0, 2.0)
        with self.assertRaises(ValidationError):
            self._create_rule("Full Day", 0.0, 24.0)

    def test_partial_overlap_at_end_raises_error(self):
        """[0,4] y [2,6] se superponen en [2,4] — invalido"""
        self._create_rule("First", 0.0, 4.0)
        with self.assertRaises(ValidationError):
            self._create_rule("Second", 2.0, 6.0)

    def test_partial_overlap_at_start_raises_error(self):
        """[2,6] y [0,4] se superponen en [2,4] — invalido"""
        self._create_rule("First", 2.0, 6.0)
        with self.assertRaises(ValidationError):
            self._create_rule("Second", 0.0, 4.0)

    def test_exact_same_range_raises_error(self):
        """[0,2] duplicado — invalido"""
        self._create_rule("First", 0.0, 2.0)
        with self.assertRaises(ValidationError):
            self._create_rule("Duplicate", 0.0, 2.0)

    def test_non_overlapping_ranges_are_valid(self):
        """rangos completamente separados sin solapamiento — valido"""
        self._create_rule("Early", -2.0, 0.0)
        self._create_rule("Late", 2.0, 4.0)

    def test_update_rule_to_overlap_raises_error(self):
        """actualizar una regla existente para que solape con otra — invalido"""
        self._create_rule("Fixed", 8.0, 12.0)
        movable = self._create_rule("Movable", 14.0, 18.0)
        with self.assertRaises(ValidationError):
            movable.hour_from = 10.0

