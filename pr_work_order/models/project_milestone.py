from odoo import api, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class ProjectMilestone(models.Model):
    _inherit = "project.milestone"

    @api.constrains("sale_line_id", "product_uom_qty", "quantity_percentage")
    def _check_sale_line_milestone_percentage(self):
        """
        Enforce that the sum of milestone % for the same Sale Order Line
        never exceeds 100%.

        NOTE:
        - In standard Odoo, quantity_percentage is a ratio (0..1), not 0..100.
        """
        for milestone in self:
            sale_line = milestone.sale_line_id
            if not sale_line:
                continue

            milestones = self.search([("sale_line_id", "=", sale_line.id)])
            total_ratio = sum(milestones.mapped("quantity_percentage"))  # 0..1

            # total_ratio > 1.0 means > 100%
            if float_compare(total_ratio, 1.0, precision_digits=4) > 0:
                raise ValidationError(_(
                    "The total milestone percentage for the sales order item '%(line)s' "
                    "cannot exceed 100%%. Current total: %(total).2f%%."
                ) % {
                    "line": sale_line.display_name,
                    "total": total_ratio * 100.0,
                })
