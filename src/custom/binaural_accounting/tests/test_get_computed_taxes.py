from odoo import fields, Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

# odoo --config=config/local.conf --http-port=8079 --test-enable --test-tags=/binaural_accounting:TestGetComputedTaxes --stop-after-init
@tagged('post_install', '-at_install')
class TestGetComputedTaxes(AccountTestInvoicingCommon):
    """Pruebas unitarias para _get_computed_taxes sobreescrito en account.move.line.

    El metodo base (core) resuelve los impuestos segun:
      - Producto (taxes_id / supplier_taxes_id)
      - Cuenta contable (account_id.tax_ids)
      - Contexto (account_default_taxes, skip_computed_taxes)
      - Posicion fiscal (fiscal_position_id.map_tax)

    La sobreescritura en binaural_accounting agrega el impuesto definido
    en el perfil fiscal (fiscal_profile.tax_id) del partner de la factura.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Impuestos basados en data/account_data_tax.xml pero creados con la compania del test
        cls.tax_iva_16 = cls.env['account.tax'].sudo().create({
            'name': 'IVA 16% (VE)',
            'description': 'IVA 16%',
            'amount': 16,
            'amount_type': 'percent',
            'company_id': cls.env.company.id,
        })
        cls.tax_retencion_75 = cls.env['account.tax'].sudo().create({
            'name': 'Retencion 75% (VE)',
            'description': 'Retencion 75%',
            'amount': -12,
            'amount_type': 'percent',
            'company_id': cls.env.company.id,
        })
        cls.tax_retencion_group = cls.env['account.tax'].sudo().create({
            'name': 'Retencion 75% sobre IVA 16% (12%) (VE)',
            'amount': -75,
            'amount_type': 'group',
            'company_id': cls.env.company.id,
            'children_tax_ids': [Command.link(cls.tax_iva_16.id), Command.link(cls.tax_retencion_75.id)],
        })

        # Perfil fiscal que agrega la retencion del 75%
        cls.fiscal_profile = cls.env['account.fiscal.profile'].create({
            'name': 'Perfil con Retencion 75%',
            'tax_id': cls.tax_retencion_75.id,
        })

        # Partner CON perfil fiscal
        cls.partner_with_profile = cls.env['res.partner'].create({
            'name': 'Partner Con Perfil Fiscal',
            'fiscal_profile': cls.fiscal_profile.id,
        })

        # Partner SIN perfil fiscal
        cls.partner_without_profile = cls.env['res.partner'].create({
            'name': 'Partner Sin Perfil Fiscal',
        })

        # Producto sin impuestos (para probar fallback a cuenta)
        cls.product_no_tax = cls._create_product(
            name='product_no_tax',
            taxes_id=[Command.clear()],
            supplier_taxes_id=[Command.clear()],
        )

        # Impuesto de compra para pruebas (ninguno de los XML es de tipo 'purchase')
        cls.tax_purchase = cls.env['account.tax'].create({
            'name': 'Compra IVA 16%',
            'amount_type': 'percent',
            'amount': 16.0,
            'company_id': cls.env.company.id,
            'type_tax_use': 'purchase',
        })

        # Asignar tax_iva_16 a la cuenta de ingresos para probar fallback
        cls.company_data['default_account_revenue'].sudo().write({
            'tax_ids': [Command.set(cls.tax_iva_16.ids)],
        })

    # -------------------------------------------------------------------------
    # helpers
    # -------------------------------------------------------------------------

    def _create_sale_invoice(self, product, partner, price_unit=100.0):
        """Crea una factura de venta con una sola linea y devuelve la linea."""
        invoice = self._create_invoice(
            move_type='out_invoice',
            partner_id=partner.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=product.id,
                    price_unit=price_unit,
                ),
            ],
        )
        return invoice.invoice_line_ids[0]

    def _create_purchase_invoice(self, product, partner, price_unit=100.0):
        """Crea una factura de compra con una sola linea y devuelve la linea."""
        invoice = self._create_invoice(
            move_type='in_invoice',
            partner_id=partner.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=product.id,
                    price_unit=price_unit,
                ),
            ],
        )
        return invoice.invoice_line_ids[0]

    # -------------------------------------------------------------------------
    # Escenario: Factura de venta (out_invoice)
    # -------------------------------------------------------------------------

    def test_sale_invoice_returns_product_taxes(self):
        """Verifica que en una factura de venta se devuelvan los impuestos del producto (taxes_id).

        Crea una factura de venta con un producto que tiene tax_iva_16 configurado.
        El metodo debe detectar que es un documento de venta, tomar los impuestos
        del producto y devolver tax_iva_16.
        """
        # Asignar tax_iva_16 al producto
        self.product_a.sudo().write({
            'taxes_id': [Command.set(self.tax_iva_16.ids)],
        })

        line = self._create_sale_invoice(self.product_a, self.partner_without_profile)
        result = line._get_computed_taxes()
        self.assertEqual(result, self.tax_iva_16)

    def test_sale_invoice_falls_back_to_account_taxes(self):
        """Verifica que, si el producto no tiene impuestos, se usen los de la cuenta contable.

        product_no_tax no tiene taxes_id, por lo que filtered_taxes_id queda vacio.
        El metodo debe caer en account_id.tax_ids filtrados por type_tax_use == 'sale'.
        La cuenta revenue tiene tax_iva_16 (type_tax_use='sale' por defecto).
        """
        line = self._create_sale_invoice(self.product_no_tax, self.partner_without_profile)
        result = line._get_computed_taxes()
        self.assertIn(self.tax_iva_16, result)

    # -------------------------------------------------------------------------
    # Escenario: Factura de compra (in_invoice)
    # -------------------------------------------------------------------------

    def test_purchase_invoice_returns_supplier_taxes(self):
        """Verifica que en una factura de compra se devuelvan supplier_taxes_id del producto.

        Crea una factura de compra con product_b y supplier_taxes_id = tax_purchase.
        El metodo debe detectar is_purchase_document y tomar supplier_taxes_id.
        """
        self.product_b.sudo().write({
            'supplier_taxes_id': [Command.set(self.tax_purchase.ids)],
        })

        line = self._create_purchase_invoice(self.product_b, self.partner_without_profile)
        result = line._get_computed_taxes()
        self.assertEqual(result, self.tax_purchase)

    # -------------------------------------------------------------------------
    # Escenario: Perfil fiscal
    # -------------------------------------------------------------------------

    def test_fiscal_profile_adds_tax_to_result(self):
        """Verifica que el impuesto del perfil fiscal se agregue a los impuestos computados.

        Crea una factura de venta con partner_with_profile (tiene perfil fiscal con retencion 75%).
        Flujo:
          1. super()._get_computed_taxes() devuelve tax_iva_16 (del producto)
          2. La sobreescritura detecta fiscal_profile en el partner
          3. Agrega tax_retencion_75 al resultado
        """
        self.product_a.sudo().write({
            'taxes_id': [Command.set(self.tax_iva_16.ids)],
        })

        line = self._create_sale_invoice(self.product_a, self.partner_with_profile)
        result = line._get_computed_taxes()
        self.assertIn(self.tax_iva_16, result)
        self.assertIn(self.tax_retencion_75, result)

    def test_fiscal_profile_adds_tax_even_with_empty_product_taxes(self):
        """Verifica que el perfil fiscal agregue su impuesto aunque el producto no tenga impuestos.

        product_no_tax no tiene impuestos, por lo que la base devuelve tax_iva_16 (fallback cuenta).
        La sobreescritura debe agregar tax_retencion_75 ademas.
        """
        line = self._create_sale_invoice(self.product_no_tax, self.partner_with_profile)
        result = line._get_computed_taxes()
        self.assertIn(self.tax_iva_16, result)
        self.assertIn(self.tax_retencion_75, result)

    def test_without_fiscal_profile_returns_base_taxes_only(self):
        """Verifica que, sin perfil fiscal, solo se devuelvan los impuestos base.

        partner_without_profile no tiene fiscal_profile, por lo que la condicion
        'if self.move_id.partner_id and fiscal_profile' es False.
        El resultado debe ser exactamente lo que devuelve super().
        """
        self.product_a.sudo().write({
            'taxes_id': [Command.set(self.tax_iva_16.ids)],
        })

        line = self._create_sale_invoice(self.product_a, self.partner_without_profile)
        result = line._get_computed_taxes()
        self.assertEqual(result, self.tax_iva_16)
        self.assertNotIn(self.tax_retencion_75, result)

    # -------------------------------------------------------------------------
    # Escenario: Grupo de impuestos
    # -------------------------------------------------------------------------

    def test_fiscal_profile_with_group_tax(self):
        """Verifica que el perfil fiscal funcione con un grupo de impuestos como tax_id.

        El perfil fiscal apunta a tax_retencion_group (grupo IVA 16% + Retencion 75%).
        Al llamar _get_computed_taxes, el grupo se agrega al resultado ademas
        de los impuestos del producto.
        """
        # Crear un perfil fiscal con el grupo de retencion
        profile_group = self.env['account.fiscal.profile'].create({
            'name': 'Perfil con Grupo Retencion 75%',
            'tax_id': self.tax_retencion_group.id,
        })
        partner_group = self.env['res.partner'].create({
            'name': 'Partner Con Grupo',
            'fiscal_profile': profile_group.id,
        })

        self.product_a.sudo().write({
            'taxes_id': [Command.set(self.tax_iva_16.ids)],
        })

        line = self._create_sale_invoice(self.product_a, partner_group)
        result = line._get_computed_taxes()

        # Debe contener tax_iva_16 (del producto) y tax_retencion_group (del perfil)
        self.assertIn(self.tax_iva_16, result)
        self.assertIn(self.tax_retencion_group, result)

    # -------------------------------------------------------------------------
    # Escenario: Posicion fiscal
    # -------------------------------------------------------------------------

    def test_fiscal_position_maps_taxes(self):
        """Verifica que los impuestos se mapeen a traves de la posicion fiscal.

        Crea un impuesto destino (tax_iva_16_mapped) con original_tax_ids = tax_iva_16
        y lo asigna a fiscal_pos_a. El map_tax de la posicion fiscal reemplaza
        tax_iva_16 por tax_iva_16_mapped en el resultado.
        """
        # Crear un impuesto destino que mapea tax_iva_16
        tax_iva_16_mapped = self.env['account.tax'].sudo().create({
            'name': 'IVA 16% Mapped',
            'amount_type': 'percent',
            'amount': 16.0,
            'company_id': self.env.company.id,
            'fiscal_position_ids': [Command.set(self.fiscal_pos_a.ids)],
            'original_tax_ids': [Command.set(self.tax_iva_16.ids)],
        })

        self.product_a.sudo().write({
            'taxes_id': [Command.set(self.tax_iva_16.ids)],
        })

        invoice = self._create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_without_profile.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a.id,
                    price_unit=100.0,
                ),
            ],
            fiscal_position_id=self.fiscal_pos_a.id,
        )
        line = invoice.invoice_line_ids[0]

        result = line._get_computed_taxes()
        self.assertIn(tax_iva_16_mapped, result)
        self.assertNotIn(self.tax_iva_16, result)

    def test_fiscal_profile_tax_not_mapped_by_fiscal_position(self):
        """Verifica que el impuesto del perfil fiscal NO se mapee por posicion fiscal.

        El perfil fiscal se agrega DESPUES de que super() aplica el mapeo de la
        posicion fiscal (map_tax). Por lo tanto, tax_retencion_75 permanece sin
        mapear en el resultado, incluso si existe un impuesto destino configurado.
        """
        # Crear un impuesto destino que mapearia tax_retencion_75 si pasara por map_tax
        self.env['account.tax'].sudo().create({
            'name': 'Retencion 50% Mapped',
            'amount_type': 'percent',
            'amount': -8.0,
            'company_id': self.env.company.id,
            'fiscal_position_ids': [Command.set(self.fiscal_pos_a.ids)],
            'original_tax_ids': [Command.set(self.tax_retencion_75.ids)],
        })

        self.product_a.sudo().write({
            'taxes_id': [Command.set(self.tax_iva_16.ids)],
        })

        invoice = self._create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_with_profile.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a.id,
                    price_unit=100.0,
                ),
            ],
            fiscal_position_id=self.fiscal_pos_a.id,
        )
        line = invoice.invoice_line_ids[0]

        result = line._get_computed_taxes()
        # tax_iva_16 del producto SÍ se mapea porque pasa por super()
        # tax_retencion_75 del perfil fiscal NO se mapea porque se agrega despues de super()
        self.assertIn(self.tax_retencion_75, result)

    # -------------------------------------------------------------------------
    # Escenario: Asiento contable (entry) / Contextos especiales
    # -------------------------------------------------------------------------

    def test_entry_move_returns_empty(self):
        """Verifica que un asiento contable (entry) devuelva recordset vacio.

        Los asientos contables no son documentos de venta ni compra.
        Al no tener contexto account_default_taxes, la rama 'else' del metodo base
        se ejecuta con is_entry() = True, devolviendo False.
        Como el asiento no tiene partner, la sobreescritura no agrega nada.
        """
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': fields.Date.today(),
            'line_ids': [
                Command.create({
                    'name': 'Linea debito',
                    'debit': 100.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
                Command.create({
                    'name': 'Contrapartida',
                    'credit': 100.0,
                    'account_id': self.company_data['default_account_receivable'].id,
                }),
            ],
        })
        line = move.line_ids[0]
        result = line._get_computed_taxes()
        self.assertFalse(result)

    def test_account_default_taxes_context_uses_account_taxes(self):
        """Verifica que con account_default_taxes se tomen los impuestos de la cuenta.

        El contexto account_default_taxes hace que el metodo base salte la logica
        de tipo de documento y use directamente account_id.tax_ids.
        """
        line = self._create_sale_invoice(self.product_no_tax, self.partner_without_profile)
        result = line.with_context(account_default_taxes=True)._get_computed_taxes()
        self.assertIn(self.tax_iva_16, result)
