from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PosDiscountHourlyRule(models.Model):
    _name = "pos.order.hourly.discount.rule"
    _description = "Regla de descuento por hora"

    name = fields.Char(
        string="Nombre",
        required=True,
    )

    hour_from = fields.Float(
        string="Hora inicio",
        required=True,
    )

    hour_to = fields.Float(
        string="Hora fin",
        required=True,
    )

    discount_percentage = fields.Float(
        string="Porcentaje de descuento",
        required=True,
    )

    # Validate the time range is logically correct and doesn't overlap
    # with any existing rule. Overlap occurs when two intervals share any
    # interior point — e.g. [0,2] overlaps both [0,1] and [1,3] but is
    # considered adjacent (not overlapping) with [2,4].
    @api.constrains("hour_from", "hour_to")
    def _check_hour_range(self):
        for record in self:
            if record.hour_from >= record.hour_to:
                raise ValidationError(
                    _("La hora de inicio debe ser menor a la hora de fin.")
                )
            overlapping = self.env["pos.order.hourly.discount.rule"].search([
                ("id", "!=", record.id),
                ("hour_from", "<", record.hour_to),
                ("hour_to", ">", record.hour_from),
            ])
            if overlapping:
                raise ValidationError(
                    _("El rango horario se superpone con la regla «%s».")
                    % overlapping[0].name
                )
