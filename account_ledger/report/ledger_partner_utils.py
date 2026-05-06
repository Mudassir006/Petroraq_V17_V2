# -*- coding: utf-8 -*-

from datetime import datetime, date

from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


def as_date(value):
    """Return a Python date for wizard/report date values."""
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), DATE_FORMAT).date()


def get_mapped_partner_ids(env, account_ids, company_id):
    """Partners whose legacy ledger account is among the selected accounts.

    Include commercial entities and child contacts so invoices/payments posted on
    either the parent company or a contact are reported under the mapped legacy
    account.
    """
    account_ids = [account_id for account_id in account_ids if account_id]
    if not account_ids:
        return []

    partner_domain = [("pr_ledger_account_id", "in", account_ids)]
    if company_id:
        partner_domain = expression.AND([
            partner_domain,
            ["|", ("company_id", "=", False), ("company_id", "=", company_id)],
        ])

    partners = env["res.partner"].sudo().search(partner_domain)
    if not partners:
        return []

    commercial_partners = partners.mapped("commercial_partner_id") | partners
    related_partners = env["res.partner"].sudo().search([
        ("commercial_partner_id", "in", commercial_partners.ids),
    ])
    return (partners | commercial_partners | related_partners).ids


def build_ledger_move_line_domain(
    company_id,
    account_ids,
    partner_ids=None,
    date_start=None,
    date_end=None,
    analytic_ids=None,
    opening=False,
):
    """Build the account ledger domain including partner-mapped move lines."""
    account_ids = [account_id for account_id in account_ids if account_id]
    partner_ids = [partner_id for partner_id in (partner_ids or []) if partner_id]
    analytic_ids = [analytic_id for analytic_id in (analytic_ids or []) if analytic_id]

    base_domain = [
        ("company_id", "=", company_id),
        ("move_id.state", "=", "posted"),
    ]

    if opening:
        base_domain.append(("date", "<", as_date(date_start)))
    else:
        base_domain.extend([
            ("date", ">=", as_date(date_start)),
            ("date", "<=", as_date(date_end)),
        ])

    for analytic_id in analytic_ids:
        base_domain.append(("analytic_distribution", "in", [int(analytic_id)]))

    account_domain = [("account_id", "in", account_ids)]
    if partner_ids:
        partner_domain = [
            ("partner_id", "in", partner_ids),
            ("account_id", "not in", account_ids),
        ]
        ledger_domain = expression.OR([account_domain, partner_domain])
    else:
        ledger_domain = account_domain

    return expression.AND([base_domain, ledger_domain])


def get_ledger_move_lines(env, company_id, account_ids, date_start, date_end, analytic_ids=None):
    partner_ids = get_mapped_partner_ids(env, account_ids, company_id)
    domain = build_ledger_move_line_domain(
        company_id,
        account_ids,
        partner_ids=partner_ids,
        date_start=date_start,
        date_end=date_end,
        analytic_ids=analytic_ids,
    )
    return env["account.move.line"].search(domain, order="date asc, id asc")


def get_opening_balance(env, company_id, account_ids, date_start, analytic_ids=None):
    partner_ids = get_mapped_partner_ids(env, account_ids, company_id)
    domain = build_ledger_move_line_domain(
        company_id,
        account_ids,
        partner_ids=partner_ids,
        date_start=date_start,
        analytic_ids=analytic_ids,
        opening=True,
    )
    result = env["account.move.line"].read_group(domain, ["balance:sum"], [])
    return result[0].get("balance", 0.0) if result else 0.0
