from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests
import json


class GeneralLedgerCustomHandler(models.AbstractModel):
    # region [Initial]
    _inherit = 'account.general.ledger.report.handler'
    # endregion [Initial]

    def _query_values(self, report, options):
        """ Executes the queries, and performs all the computations.

        :return:    [(record, values_by_column_group), ...],  where
                    - record is an account.account record.
                    - values_by_column_group is a dict in the form {column_group_key: values, ...}
                        - column_group_key is a string identifying a column group, as in options['column_groups']
                        - values is a list of dictionaries, one per period containing:
                            - sum:                              {'debit': float, 'credit': float, 'balance': float}
                            - (optional) initial_balance:       {'debit': float, 'credit': float, 'balance': float}
                            - (optional) unaffected_earnings:   {'debit': float, 'credit': float, 'balance': float}
        """
        # Execute the queries and dispatch the results.
        query, params = self._get_query_sums(report, options)

        if not query:
            return []

        groupby_accounts = {}
        groupby_companies = {}

        self._cr.execute(query, params)
        for res in self._cr.dictfetchall():
            # No result to aggregate.
            if res['groupby'] is None:
                continue

            column_group_key = res['column_group_key']
            key = res['key']
            if key == 'sum':
                groupby_accounts.setdefault(res['groupby'], {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_accounts[res['groupby']][column_group_key][key] = res

            elif key == 'initial_balance':
                groupby_accounts.setdefault(res['groupby'], {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_accounts[res['groupby']][column_group_key][key] = res

            elif key == 'unaffected_earnings':
                groupby_companies.setdefault(res['groupby'], {col_group_key: {} for col_group_key in options['column_groups']})
                groupby_companies[res['groupby']][column_group_key] = res

        # Affect the unaffected earnings to the first fetched account of type 'account.data_unaffected_earnings'.
        # There is an unaffected earnings for each company but it's less costly to fetch all candidate accounts in
        # a single search and then iterate it.
        if groupby_companies:
            equity_unaffected_account_ids_by_company = self.env['account.account'].browse(
                self.env['account.account']._name_search(options.get('filter_search_bar'), [
                    *self.env['account.account']._check_company_domain(list(groupby_companies.keys())),
                    ('account_type', '=', 'equity_unaffected'),
                ])
            ).grouped('company_id')

            for company_id, groupby_company in groupby_companies.items():
                if equity_unaffected_account := equity_unaffected_account_ids_by_company.get(self.env['res.company'].browse(company_id).root_id):
                    for column_group_key in options['column_groups']:
                        groupby_accounts.setdefault(equity_unaffected_account.id, {col_group_key: {'unaffected_earnings': {}} for col_group_key in options['column_groups']})

                        if unaffected_earnings := groupby_company.get(column_group_key):
                            if groupby_accounts[equity_unaffected_account.id][column_group_key].get('unaffected_earnings'):
                                for key in ['amount_currency', 'debit', 'credit', 'balance']:
                                    groupby_accounts[equity_unaffected_account.id][column_group_key]['unaffected_earnings'][key] += unaffected_earnings[key]
                            else:
                                groupby_accounts[equity_unaffected_account.id][column_group_key]['unaffected_earnings'] = unaffected_earnings

        # Retrieve the accounts to browse.
        # groupby_accounts.keys() contains all account ids affected by:
        # - the amls in the current period.
        # - the amls affecting the initial balance.
        # - the unaffected earnings allocation.
        # Note a search is done instead of a browse to preserve the table ordering.
        if groupby_accounts:
            accounts = self.env['account.account'].search([('id', 'in', list(groupby_accounts.keys()))])
            if self.env.user.has_group('account.group_account_manager') or self.env.user.has_group('pr_account.custom_group_accounting_manager'):
                accounts = accounts
            else:
                accounts = accounts.filtered(lambda a: a.id not in [748, 749, 1132])
        else:
            accounts = []

        return [(account, groupby_accounts[account.id]) for account in accounts]

