from odoo import models, fields, api


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def get_hourly_discount_rule(self):
        rules = self.env["pos.order.hourly.discount.rule"].search([])

        # 1. Get the current UTC time
        utc_now = fields.Datetime.now()

        # 2. Convert it to the user's localized datetime object
        local_datetime = fields.Datetime.context_timestamp(self, utc_now)

        # 3. Convert the local datetime to decimal hours (e.g., 14:30 -> 14.5)
        now_decimal = local_datetime.hour + local_datetime.minute / 60.0

        # 4. Get a rule that fits in the current hour
        rule = rules.filtered(
            lambda r: r.hour_from <= now_decimal <= r.hour_to
        )[:1]
        if rule:
            # Return dict instead of recordset because orm.call() serializes
            # recordsets as just IDs via JSON RPC. A dict gives the JS frontend
            # direct access to all field values without a second orm.read() call.
            return {
                "id": rule.id,
                "name": rule.name,
                "hour_from": rule.hour_from,
                "hour_to": rule.hour_to,
                "discount_percentage": rule.discount_percentage,
            }
        return {}

