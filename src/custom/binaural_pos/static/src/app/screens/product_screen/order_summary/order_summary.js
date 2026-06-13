import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

/**
 * @param {import("@web/core/orm_service").ORM} orm - The Odoo ORM service
 * @returns {Promise<Object>} The matching rule dict with keys {id, name, hour_from, hour_to, discount_percentage},
 *   or an empty dict if no rule applies at the current server time.
 *
 * Fetches fresh every call so it reflects the current server time,
 * catching windows that started after the POS was opened.
 */
async function getHourlyDiscountRule(orm) {
    return await orm.call("pos.order", "get_hourly_discount_rule", []);
}

/** Override PosStore.addLineToCurrentOrder to apply the hourly discount to
 * every product newly added to the order.
 *
 * Why override: super.addLineToCurrentOrder handles the full product-addition
 * flow — variant popup, combo, lot tracking, weight scale, merging — and
 * returns the final (possibly merged) line. We hook in after that to stamp
 * the discount on the line, so it works regardless of which code path added
 * the product (click, barcode, optional products popup, ...). */
patch(PosStore.prototype, {
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        const line = await super.addLineToCurrentOrder(...arguments);
        if (!line) return line;
        const rule = await getHourlyDiscountRule(this.env.services.orm);
        if (rule?.discount_percentage && !line.getDiscount()) {
            await this.setDiscountFromUI(line, rule.discount_percentage);
        }
        return line;
    },
});

patch(OrderSummary.prototype, {
    /** Extend setup to grab the ORM service and, on mount, apply the discount
     * to any order lines that already exist.
     *
     * Why override: super.setup initialises numberBuffer, dialog, and the pos
     * hook that the component needs to function. We add our own init logic
     * after it. */
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        onWillStart(async () => {
            await this._applyHourlyDiscountToExistingLines();
        })
    },

    /** Fetch the current rule once and apply it to every line in the order
     * that doesn't already carry a manual discount. Called once on mount. */
    async _applyHourlyDiscountToExistingLines() {
        const order = this.currentOrder;
        if (!order) return;
        const rule = await getHourlyDiscountRule(this.orm);
        if (!rule?.discount_percentage) return;
        for (const line of order.lines) {
            if (!line.getDiscount()) {
                await this.pos.setDiscountFromUI(line, rule.discount_percentage);
            }
        }
    },

    /** Fetch the hourly rule and apply it to a single line.
     * Skips lines that already have a manual discount or are falsy. */
    async _applyHourlyDiscountToLine(line) {
        if (!line || line.getDiscount()) return;
        const rule = await getHourlyDiscountRule(this.orm);
        if (rule?.discount_percentage) {
            await this.pos.setDiscountFromUI(line, rule.discount_percentage);
        }
    },

    /** Override updateSelectedOrderline to apply the hourly discount to the
     * currently selected line before the original handler runs.
     *
     * Why override: super.updateSelectedOrderline processes number-buffer
     * input — it parses the buffer, validates against numpadMode (quantity /
     * discount / price), and calls _setValue to apply the change to the line.
     * We apply the discount first so newly selected lines get it even when
     * the user is just changing quantity, not manually setting a discount. */
    async updateSelectedOrderline({ buffer, key }) {
        const selectedLine = this.currentOrder?.getSelectedOrderline();
        await this._applyHourlyDiscountToLine(selectedLine);
        return super.updateSelectedOrderline({buffer, key});
    }
})
