# -*- coding: utf-8 -*-
from . import models
from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def petroraq_sale_workflow_create_payment_terms(env, registry=None):
    """Post-init hook: create term lines for our payment terms in a
    version-compatible way by detecting the term line fields dynamically.

    The hook will:
    - detect which field on account.payment.term.line can hold the day offset
    - create a single 'balance' line per term using only fields that exist
    - log the chosen field name and any errors for diagnostics

    Compatible with Odoo versions that pass either a database cursor or an
    Environment to post-init hooks.
    """
    if not isinstance(env, api.Environment):
        env = api.Environment(env, SUPERUSER_ID, {})
    Term = env['account.payment.term']
    TermLine = env['account.payment.term.line']

    terms = {
        'petroraq_sale_workflow.payment_term_immediate': 0,
        'petroraq_sale_workflow.payment_term_15_days': 15,
        'petroraq_sale_workflow.payment_term_30_days': 30,
        'petroraq_sale_workflow.payment_term_45_days': 45,
        'petroraq_sale_workflow.payment_term_60_days': 60,
    }

    line_field_names = set(TermLine._fields.keys())

    # Common candidate names across versions/custom modules
    candidates = ['days', 'day', 'number_of_days', 'delay', 'day_count', 'term_days']
    chosen_field = next((f for f in candidates if f in line_field_names), None)

    if 'value' not in line_field_names:
        _logger.warning("petroraq_sale_workflow: account.payment.term.line has no 'value' field; skipping term line creation")
        return

    _logger.info("petroraq_sale_workflow: attempting to create payment term lines; chosen day field=%s", chosen_field)

    for xmlid, days in terms.items():
        try:
            term = env.ref(xmlid)
        except Exception:
            term = False
        if not term:
            _logger.debug("petroraq_sale_workflow: term %s not found, skipping", xmlid)
            continue
        if term.line_ids:
            _logger.debug("petroraq_sale_workflow: term %s already has lines, skipping", xmlid)
            continue

        # Build candidate line values, include only fields that exist
        line_vals = {'value': 'balance'}
        if chosen_field:
            line_vals[chosen_field] = days
        # ensure sequence present if it's available
        if 'sequence' in line_field_names and 'sequence' not in line_vals:
            line_vals['sequence'] = 1

        safe_line_vals = {k: v for k, v in line_vals.items() if k in line_field_names}

        try:
            TermLine.create({'payment_term_id': term.id, **safe_line_vals})
            _logger.info("petroraq_sale_workflow: created term line for %s => %s", xmlid, safe_line_vals)
        except Exception as e:
            _logger.exception("petroraq_sale_workflow: failed to create term line for %s: %s", xmlid, e)
            # continue to next term
            continue