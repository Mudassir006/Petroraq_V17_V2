/** @odoo-module **/
import { SaleOrderLineProductField } from "@sale/js/sale_product_field";
import { patch } from "@web/core/utils/patch";
import {onWillStart, useState } from "@odoo/owl";

patch(SaleOrderLineProductField.prototype, {
    setup(){
        super.setup();
        this.access = useState({hide_prod_ext_link: false});
        onWillStart(async() => {
            this.access.hide_prod_ext_link = await this.orm.call(
                "access.management",
                "ishide_sale_product_ext_link",
                [[]]
            );
        });
    },
    get hasExternalButton() {
        const res = super.hasExternalButton;
        debugger
        if(res && !this.access.hide_prod_ext_link){
            return true;
        }else if(res && this.access.hide_prod_ext_link){
            return false;
        } 
        else{
            return res
        }
    }
});
