from odoo import api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    work_order_id = fields.Many2one(
        "pr.work.order",
        string="Work Order",
        index=True,
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        index=True,
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if not defaults.get("work_order_id"):
            work_order_id = self.env.context.get("default_work_order_id")
            if work_order_id:
                defaults["work_order_id"] = work_order_id
        if not defaults.get("sale_order_id"):
            sale_order_id = self.env.context.get("default_sale_order_id")
            if sale_order_id:
                defaults["sale_order_id"] = sale_order_id
        if defaults.get("work_order_id") and not defaults.get("sale_order_id"):
            work_order = self.env["pr.work.order"].browse(defaults["work_order_id"])
            defaults["sale_order_id"] = work_order.sale_order_id.id if work_order.sale_order_id else False
        return defaults


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    work_order_id = fields.Many2one(
        "pr.work.order",
        string="Work Order",
        index=True,
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Sale Order",
        index=True,
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if not defaults.get("work_order_id"):
            work_order_id = self.env.context.get("default_work_order_id")
            if work_order_id:
                defaults["work_order_id"] = work_order_id
        if not defaults.get("sale_order_id"):
            sale_order_id = self.env.context.get("default_sale_order_id")
            if sale_order_id:
                defaults["sale_order_id"] = sale_order_id
        if defaults.get("work_order_id") and not defaults.get("sale_order_id"):
            work_order = self.env["pr.work.order"].browse(defaults["work_order_id"])
            defaults["sale_order_id"] = work_order.sale_order_id.id if work_order.sale_order_id else False
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            request_id = vals.get("request_id")
            if request_id and not vals.get("work_order_id"):
                request = self.env["purchase.request"].browse(request_id)
                if request.work_order_id:
                    vals["work_order_id"] = request.work_order_id.id
                if request.sale_order_id and not vals.get("sale_order_id"):
                    vals["sale_order_id"] = request.sale_order_id.id
            if vals.get("work_order_id") and not vals.get("sale_order_id"):
                work_order = self.env["pr.work.order"].browse(vals["work_order_id"])
                vals["sale_order_id"] = work_order.sale_order_id.id if work_order.sale_order_id else False
        lines = super().create(vals_list)
        lines._sync_from_moves()
        for line in lines:
            request = line.request_id
            if line.work_order_id and request and not request.work_order_id:
                request.work_order_id = line.work_order_id.id
            if line.sale_order_id and request and not request.sale_order_id:
                request.sale_order_id = line.sale_order_id.id
        return lines

    def write(self, vals):
        res = super().write(vals)
        self._sync_from_moves()
        for line in self:
            request = line.request_id
            if line.work_order_id and request and not request.work_order_id:
                request.work_order_id = line.work_order_id.id
            if line.sale_order_id and request and not request.sale_order_id:
                request.sale_order_id = line.sale_order_id.id
        return res

    def _sync_from_moves(self):
        for line in self:
            if not line.work_order_id:
                work_orders = line.move_dest_ids.mapped("work_order_id")
                line.work_order_id = work_orders[:1].id if work_orders else False
            if not line.sale_order_id:
                sale_orders = line.move_dest_ids.mapped("sale_line_id.order_id")
                if not sale_orders:
                    sale_orders = line.move_dest_ids.mapped("picking_id.sale_id")
                if not sale_orders and line.work_order_id:
                    sale_orders = line.work_order_id.sale_order_id
                line.sale_order_id = sale_orders[:1].id if sale_orders else False
