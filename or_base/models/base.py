import datetime

from psycopg2 import sql

from odoo import models, _
from odoo.exceptions import ValidationError


class BaseModel(models.AbstractModel):
    """
    Allow to define a model with 'bigint' ID by setting the '_big_id' attribute to True.
    All the relational fields which relate to this model will be of type 'bigint' too.
    You can also manually set an integer field to 'bigint' by adding 'bigint=True' to it.
    """
    _inherit = 'base'
    _big_id = False

    def _auto_init(self):
        cr = self._cr
        columns_to_convert = []
        for field_name, field in self._fields.items():
            if field_name == 'id' and self._big_id:
                field.column_type = ('bigint', 'bigint')
                # Because id is a special column and only create via first database initialization
                # so it won't convert into bigint serial unless we take action here
                columns_to_convert.append((self._table, 'id'))
            elif field.type == 'many2one' and self.env[field.comodel_name]._big_id:
                field.column_type = ('bigint', 'bigint')
            elif field.type == 'integer' and getattr(field, 'bigint', None):
                field.column_type = ('bigint', 'bigint')
            elif field.type == 'many2many' and field.store:
                if self._big_id:
                    columns_to_convert.append((field.relation, field.column1))
                if self.env[field.comodel_name]._big_id:
                    columns_to_convert.append((field.relation, field.column2))

        super(BaseModel, self)._auto_init()

        for table, column in columns_to_convert:
            cr.execute(
                "SELECT data_type FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
                (table, column),
            )
            res = cr.fetchone()
            if res and res[0] != 'bigint':
                cr.execute(
                    sql.SQL("ALTER TABLE {table} ALTER COLUMN {column} TYPE bigint").format(
                        table=sql.Identifier(table),
                        column=sql.Identifier(column),
                    )
                )

    def _get_sort_key(self, record, custom_order=None, custom_order_position='before'):
        """
        Generate a dynamic sort key for a record based on a combination of the model's `_order` and a custom order.

        :param record: A single record.
        :param custom_order: A custom order string (e.g., 'field1 asc, field2 desc'). Defaults to None.
        :param custom_order_position: Determines the position of `custom_order` relative to the model's `_order`.
                                       - 'before': `custom_order` precedes `_order`.
                                       - 'after': `custom_order` follows `_order`.
                                       - 'replace': Only `custom_order` is used, replacing `_order`.
                                       Defaults to 'before'.
        :return: A tuple representing the sort key.
        """

        def normalize_value_for_sorting(value, direction):
            """
            Normalize a value for sorting based on direction ('asc' or 'desc').

            :param value: The value to normalize.
            :param direction: 'asc' or 'desc'.
            :return: Normalized value.
            """
            if value is None:
                return float('inf') if direction == 'asc' else -float('inf')

            if direction == 'desc':
                if isinstance(value, (int, float)):
                    return -value
                if isinstance(value, str):
                    return ''.join(chr(255 - ord(char)) for char in value)
                if isinstance(value, bool):
                    return not value
                if isinstance(value, (datetime.date, datetime.datetime)):
                    return -value.timestamp()
            return value

        model = record._name
        base_order = self.env[model]._order or 'id asc'

        # Combine orders based on the specified position
        if custom_order:
            if custom_order_position == 'before':
                combined_order = ', '.join(filter(None, [custom_order, base_order]))
            elif custom_order_position == 'after':
                combined_order = ', '.join(filter(None, [base_order, custom_order]))
            elif custom_order_position == 'replace':
                combined_order = custom_order
            else:
                raise ValidationError(
                    _(
                        "Invalid `custom_order_position` value: %s. Must be 'before', 'after', or 'replace'.",
                        custom_order_position
                    )
                )
        else:
            combined_order = base_order

        # Parse the combined order string
        order_fields = [
            (field.split()[0].strip(), 'desc' if 'desc' in field.lower() else 'asc')
            for field in combined_order.split(',')
        ]

        # Generate the sort key
        sort_values = []
        for field, direction in order_fields:
            value = getattr(record, field, None)
            sort_values.append(normalize_value_for_sorting(value, direction))
        return tuple(sort_values)
