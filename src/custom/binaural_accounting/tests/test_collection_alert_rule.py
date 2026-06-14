from datetime import timedelta

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from freezegun import freeze_time


# odoo --config=config/local.conf --http-port=8079 --test-enable --test-tags=/binaural_accounting:TestCollectionAlertRule --stop-after-init
@tagged('post_install', '-at_install')
@freeze_time('2026-06-13')
class TestCollectionAlertRule(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.alert_rule = cls.env['account.collection.alert.rule'].create({
            'name': 'Test Rule',
            'amount_min': 100.0,
            'days_overdue': 30,
            'risk_level': 'medio',
        })

        # Fecha de vencimiento en el pasado para que supere el filtro de days_overdue
        cls.date_due_past = fields.Date.today() - timedelta(days=cls.alert_rule.days_overdue + 1)

    def _mapped_invoice_ids(self):
        """Retorna las account.move asociadas a invoice_ids de la regla."""
        return self.alert_rule.invoice_ids.mapped('invoice_id')

    def test_check_invoices_adds_matching_invoice_to_rule(self):
        """Verifica que una factura que cumple el dominio sea añadida a invoice_ids.

        La factura debe tener:
          - state = 'posted'
          - amount_residual >= amount_min (100.0)
          - payment_state in ('not_paid', 'partial')
          - invoice_date_due <= hoy - days_overdue (30)
        """
        # Factura de 200.0 > amount_min (100.0) con vencimiento hace 31 dias
        # invoice_payment_term_id=False evita que el plazo de pago del partner
        # recalcule invoice_date_due al validar la factura
        invoice = self._create_invoice(
            move_type='out_invoice',
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a.id,
                    price_unit=200.0,
                ),
            ],
            invoice_date_due=self.date_due_past,
            invoice_payment_term_id=False,
            post=True,
        )
        # Tras validarla: state='posted', amount_residual=200.0, payment_state='not_paid'
        # invoice_date_due=2026-05-13 <= 2026-05-14 -> cumple el filtro de mora

        self.alert_rule._check_invoices()

        self.assertIn(invoice, self._mapped_invoice_ids())

    def test_check_invoices_does_not_add_paid_invoice(self):
        """Verifica que una factura pagada NO sea añadida a invoice_ids.

        El dominio en _check_invoices filtra por payment_state in ('not_paid', 'partial').
        Una factura fully paid debe quedar excluida, incluso si cumple los demas filtros.
        """
        # Factura de 200.0 > amount_min (100.0) con vencimiento hace 31 dias
        invoice = self._create_invoice(
            move_type='out_invoice',
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a.id,
                    price_unit=200.0,
                ),
            ],
            invoice_date_due=self.date_due_past,
            invoice_payment_term_id=False,
            post=True,
        )
        # Tras validarla: state='posted', amount_residual=200.0, payment_state='not_paid'

        # Crear un pago por el total y conciliarlo para llevar payment_state a 'paid'
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
            'partner_type': 'customer',
            'partner_id': invoice.partner_id.id,
            'amount': invoice.amount_residual,
            'date': invoice.date,
            'journal_id': self.company_data['default_journal_bank'].id,
        })
        payment.action_post()
        # Reconciliar la linea de cuenta por cobrar del pago con la de la factura
        (payment.move_id + invoice).line_ids.filtered(
            lambda x: x.account_id == self.company_data['default_account_receivable']
        ).reconcile()
        # Ahora: payment_state='paid', no debe coincidir con el dominio

        self.alert_rule._check_invoices()

        self.assertNotIn(invoice, self._mapped_invoice_ids())

    def test_check_invoices_does_not_add_invoice_below_min_amount(self):
        """Verifica que una factura con amount_residual < amount_min NO sea añadida a invoice_ids.

        El dominio en _check_invoices filtra por amount_residual >= self.amount_min.
        Una factura con monto menor debe quedar excluida, incluso si cumple los demas filtros.
        """
        # Factura de 50.0 < amount_min (100.0) con vencimiento hace 31 dias
        invoice = self._create_invoice(
            move_type='out_invoice',
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a.id,
                    price_unit=50.0,
                ),
            ],
            invoice_date_due=self.date_due_past,
            invoice_payment_term_id=False,
            post=True,
        )
        # Tras validarla: state='posted', amount_residual=50.0, payment_state='not_paid'
        # amount_residual (50.0) < amount_min (100.0) -> no debe coincidir con el dominio

        self.alert_rule._check_invoices()

        self.assertNotIn(invoice, self._mapped_invoice_ids())

    def test_check_invoices_does_not_add_invoice_not_overdue_enough(self):
        """Verifica que una factura con pocos dias de mora NO sea añadida a invoice_ids.

        El dominio en _check_invoices filtra por invoice_date_due <= hoy - days_overdue.
        Una factura con vencimiento hoy tiene 0 dias de mora (< 30) y debe quedar excluida.
        """
        # Factura de 200.0 > amount_min (100.0) con vencimiento hoy
        # Cumple todos los filtros excepto el de dias de mora
        invoice = self._create_invoice(
            move_type='out_invoice',
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a.id,
                    price_unit=200.0,
                ),
            ],
            invoice_date_due=fields.Date.today(),
            invoice_payment_term_id=False,
            post=True,
        )
        # Tras validarla: state='posted', amount_residual=200.0, payment_state='not_paid'
        # invoice_date_due=2026-06-13 > 2026-05-14 (hoy-30) -> no cumple el filtro de mora

        self.alert_rule._check_invoices()

        self.assertNotIn(invoice, self._mapped_invoice_ids())

    def test_cron_check_invoices_calls_check_invoices_on_all_rules(self):
        """Verifica que _cron_check_invoices procese todas las reglas y agregue facturas.

        _cron_check_invoices busca todas las reglas de alerta y llama
        _check_invoices sobre el recordset completo.
        """
        invoice = self._create_invoice(
            move_type='out_invoice',
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a.id,
                    price_unit=200.0,
                ),
            ],
            invoice_date_due=self.date_due_past,
            invoice_payment_term_id=False,
            post=True,
        )

        self.env['account.collection.alert.rule']._cron_check_invoices()

        self.assertIn(invoice, self._mapped_invoice_ids())

    def test_check_invoices_does_not_duplicate_existing_record(self):
        """Verifica que _check_invoices no duplique una factura ya registrada.

        Si se ejecuta _check_invoices dos veces, la segunda ejecucion debe
        detectar que la factura ya tiene un account.move.overdue.invoice
        asociado a esta regla y no crear un duplicado.
        """
        invoice = self._create_invoice(
            move_type='out_invoice',
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a.id,
                    price_unit=200.0,
                ),
            ],
            invoice_date_due=self.date_due_past,
            invoice_payment_term_id=False,
            post=True,
        )

        # Primera ejecucion: debe añadir la factura
        self.alert_rule._check_invoices()
        self.assertIn(invoice, self._mapped_invoice_ids())
        self.assertEqual(len(self.alert_rule.invoice_ids), 1)

        # Segunda ejecucion: NO debe duplicar
        self.alert_rule._check_invoices()
        self.assertIn(invoice, self._mapped_invoice_ids())
        self.assertEqual(len(self.alert_rule.invoice_ids), 1)
