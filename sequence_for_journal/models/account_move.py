# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Akhil Ashok(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from odoo import models
import re


class AccountMove(models.Model):
    """inherit account.move to add methods"""
    _inherit = 'account.move'

    def _get_starting_sequence(self):
        """Overriding the methode, this methode get the initial sequence of a
        journal"""
        self.ensure_one()
        if self.journal_id.type in ['sale', 'bank', 'cash'] and \
                self.journal_id.sequence_id.suffix:
            starting_sequence = "%s/%s/%s%s" % (
                self.journal_id.sequence_id.prefix,
                self.date.year,
                self.journal_id.step_size,
                self.journal_id.sequence_id.suffix)
        elif self.journal_id.type in ['sale', 'bank', 'cash']:
            starting_sequence = "%s/%s/000%d" % (
                self.journal_id.code,
                self.date.year,
                self.journal_id.step_size)
        elif self.journal_id.type in ['purchase', 'general'] and \
                self.journal_id.sequence_id.suffix:
            starting_sequence = "%s/%s/%s%s" % (
                self.journal_id.sequence_id.prefix, self.date.year,
                self.journal_id.step_size,
                self.journal_id.sequence_id.suffix)
        else:
            starting_sequence = "%s/%s/%s000" % (
                self.journal_id.code, self.date.year,
                self.journal_id.default_step_size)
        if self.journal_id.refund_sequence and self.move_type in (
                'out_refund', 'in_refund'):
            starting_sequence = "R" + starting_sequence
        if self.journal_id.payment_sequence and self.payment_id or \
                self._context.get('is_payment'):
            starting_sequence = "P" + starting_sequence
        return starting_sequence

    def _set_next_sequence(self):
        """Overriding, to get the next sequence number"""
        self.ensure_one()
        last_sequence = self._get_last_sequence()
        new = not last_sequence
        if new:
            last_sequence = self._get_last_sequence(relaxed=True) or \
                            self._get_starting_sequence()

        format, format_values = self._get_sequence_format_param(last_sequence)

        # My Custom
        if format_values.get("month"):
            format_values.pop("month")
            if format_values.get("prefix3"):
                if format_values["prefix3"] == "/":
                    format_values["prefix3"] = ""
        if new:
            format_values['seq'] = 0
        if self.journal_id.sequence_id.number_increment > 0:
            interpolated_prefix, interpolated_suffix = \
                self.journal_id.sequence_id._get_prefix_suffix()
            format_values['seq'] = format_values['seq'] + self.journal_id.\
                sequence_id.number_increment
            format_values['prefix1'] = interpolated_prefix + "/"
            if self.journal_id.sequence_id.suffix:
                format_values[
                    'suffix'] = "/" + interpolated_suffix
            else:
                format_values['suffix'] = ""
        else:
            format_values['seq'] = format_values['seq'] + \
                                   self.journal_id.default_step_size
        self[self._sequence_field] = format.format(**format_values)
        self._compute_split_sequence()

    def _get_sequence_format_param(self, previous):
        """Get the python format and format values for the sequence.

        :param previous: the sequence we want to extract the format from
        :return tuple(format, format_values):
            format is the format string on which we should call .format()
            format_values is the dict of values to format the `format` string
            ``format.format(**format_values)`` should be equal to ``previous``
        """
        sequence_number_reset = self._deduce_sequence_number_reset(previous)
        regex = self._sequence_fixed_regex
        if sequence_number_reset == 'year':
            regex = self._sequence_yearly_regex
        elif sequence_number_reset == 'year_range':
            regex = self._sequence_year_range_regex
        elif sequence_number_reset == 'month':
            regex = self._sequence_monthly_regex
        format_values = re.match(regex, previous).groupdict()
        format_values['seq_length'] = len(format_values['seq'])
        format_values['year_length'] = len(format_values.get('year') or '')
        format_values['year_end_length'] = len(format_values.get('year_end') or '')
        if not format_values.get('seq') and 'prefix1' in format_values and 'suffix' in format_values:
            # if we don't have a seq, consider we only have a prefix and not a suffix
            format_values['prefix1'] = format_values['suffix']
            format_values['suffix'] = ''
        for field in ('seq', 'year', 'month', 'year_end'):
            format_values[field] = int(format_values.get(field) or 0)

        # placeholders = re.findall(r'\b(prefix\d|seq|suffix\d?|year|year_end|month)\b', regex)
        placeholders = re.findall(r'\b(prefix\d|seq|suffix\d?|year|year_end)\b', regex)
        format = ''.join(
            "{seq:0{seq_length}d}" if s == 'seq' else
            "{year:0{year_length}d}" if s == 'year' else
            "{year_end:0{year_end_length}d}" if s == 'year_end' else
            "{%s}" % s
            for s in placeholders
        )
        return format, format_values
