from datetime import timedelta

from odoo import models, fields, api
from odoo.fields import Command

class AccountCollectionAlertRule(models.Model):
    _name = "account.collection.alert.rule"
    _description = "Definicion de regla de Alerta de cobro"

    name = fields.Char(
        string="Nombre de la alerta",
    )

    days_overdue = fields.Integer(
        string="Días en mora",
    )

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id.id
    )

    amount_min = fields.Monetary(
        string="Monto mínimo",
        currency_field="currency_id"
    )

    risk_level = fields.Selection(
        string="Nivel de riesgo",
        selection=[
            ("bajo", "Bajo"),
            ("medio", "Medio"),
            ("alto", "Alto")
        ]
    )

    invoice_ids = fields.One2many(
        string="Facturas",
        comodel_name="account.move.overdue.invoice",
        inverse_name="alert_rule",
    )

    def _check_invoices(self):
        """
        Obtiene todas las facturas y verifica si estan en riesgo de cobro
        acorde con el monto y los dias de mora definidos en esta regla
        """

        # Fecha limite: hoy menos los dias de mora configurados
        date_due_limit = fields.Date.today() - timedelta(days=self.days_overdue or 0)

        # 1. Obtener todas las facturas que esten en riesgo acorde con el monto definido en esta regla
        invoice_enriesgo_ids = self.env["account.move"].search([
            # Solo se verifican facturas confirmadas
            ('state', '=', 'posted'),
            # Se trabaja con el campo de amount_residual por si se tienen pago parciales.
            ("amount_residual", ">=", self.amount_min),
            # Se verifica que no este pagada o con pago parcial
            ('payment_state', 'in', ('not_paid', 'partial')),
            # Se verifica que la fecha de vencimiento sea menor o igual a la fecha limite
            ('invoice_date_due', '<=', date_due_limit),
        ])

        # 2. Verificar que facturas ya tienen un registro en la alerta
        existing_records = self.env["account.move.overdue.invoice"].search([
            ("alert_rule", "=", self.id),
            ("invoice_id", "in", invoice_enriesgo_ids.ids),
        ])
        existing_invoice_ids = existing_records.mapped("invoice_id")

        # 3. Añadir solo las facturas que no esten ya registradas
        invoices_en_riesgo = []
        for invoice_id in invoice_enriesgo_ids:
            if invoice_id in existing_invoice_ids:
                continue
            invoices_en_riesgo.append({
                "alert_rule": self.id,
                "invoice_id": invoice_id.id,
            })

        if invoices_en_riesgo:
            self.env["account.move.overdue.invoice"].create(invoices_en_riesgo)

    @api.model
    def _cron_check_invoices(self):
        # Obtener todas las reglas de alerta para invoices
        alert_rules = self.env["account.collection.alert.rule"].search([])
        # Obtener aquellas facturas que estan en riesgo de impago para 
        for alert_rule in alert_rules:
            alert_rule._check_invoices()

class OverdueInvoices(models.Model):
    _name = "account.move.overdue.invoice"
    _description = "Factura con riesgo de cobro"
    alert_rule = fields.Many2one(
        comodel_name="account.collection.alert.rule",
        help="Alerta que determino que la factura estaba en riesgo",
    )

    # These fields are here mostly for ui purposes
    rule_name = fields.Char(
        related="alert_rule.name",
    )
    risk_level = fields.Selection(
        related="alert_rule.risk_level",
    )

    days_overdue = fields.Integer(
        related="alert_rule.days_overdue",
    )

    invoice_id = fields.Many2one(
        comodel_name="account.move",
    )
