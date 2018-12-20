# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class AccountJournalInherit(models.Model):
    _inherit = "account.journal"

    is_giro = fields.Boolean(string='Giro Account', index=True)
    linked_bank_account = fields.Many2one('account.journal', string="Linked Bank Account", ondelete='restrict', copy=False)


class AccountPaymentGiro(models.Model):
    _inherit = "account.payment"

    @api.depends('journal_id', 'linked_giro_id')
    def _compute_is_giro_payment(self):
        for payment in self:
            if payment.journal_id.is_giro == True and not payment.linked_giro_id:
                payment.is_giro_payment = True
            else:
                payment.is_giro_payment = False

    is_giro_payment = fields.Boolean(compute='_compute_is_giro_payment', string='Giro Payment', readonly=True, store=True, index=True)
    is_giro_cleared = fields.Boolean(string='Is Cleared', readonly=True, store=True, index=True)
    due_date = fields.Datetime(string='Due Date', index=True,
        states={'posted': [('readonly', True)], 'reconciled': [('readonly', True)]})
    numbering = fields.Char('Giro Number', index=False,
        states={'posted': [('readonly', True)], 'reconciled': [('readonly', True)]})
    linked_giro_id = fields.Many2one('account.payment', string="Linked Giro ID", ondelete='restrict', readonly=True, store=True, copy=False)

    @api.multi
    def post(self):
        res=super(AccountPaymentGiro,self).post()
        for rec in self:
            if rec.linked_giro_id:
                rec.linked_giro_id.update({
                    'is_giro_cleared':True,
                })
        return res

    @api.multi
    def force_clear(self):
        for rec in self:
            rec.update({
                'is_giro_cleared':True,
            })
        return True

    @api.multi
    def giro_clearing(self):
        self.ensure_one()
        for rec in self:
            if rec.state != 'posted':
                raise UserError(_("Only a posted payment can be cleared. Trying to clear a payment in state %s.") % rec.state)
            if rec.payment_type == 'outbound':
                source_journal = rec.journal_id.linked_bank_account
                destination_journal = rec.journal_id
            elif rec.payment_type == 'inbound':
                source_journal = rec.journal_id
                destination_journal = rec.journal_id.linked_bank_account
            else:
                raise UserError(_("Giro can not be transferred internally. Wrong payment method was chosen.") % rec.state)
        return {
            'name': 'Check/Giro Clearing',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'flags': {'form': {'action_buttons':False}},
            'res_model': 'account.payment',
            'view_id': self.env.ref('check_payment.view_account_payment_invoice_form_check_payment_clearing').id,
            'type': 'ir.actions.act_window',
            'context': {'default_payment_type':'transfer',
                        'default_partner_type':self.partner_type,
                        'default_partner_id':self.partner_id.id,
                        'default_journal_id':source_journal.id,
                        'default_destination_journal_id':destination_journal.id,
                        'default_communication':self.communication,
                        'default_numbering':self.numbering,
                        'default_amount':self.amount,
                        'default_linked_giro_id':self.id},
        }


class account_register_payments_inherited(models.TransientModel):
    _inherit = 'account.register.payments'

    is_giro_payment = fields.Boolean(related="journal_id.is_giro", string='Giro Payment', readonly=True, index=True)
    due_date = fields.Datetime(string='Due Date', index=True,
        states={'posted': [('readonly', True)], 'reconciled': [('readonly', True)]})
    numbering = fields.Char('Giro Number', index=False,
        states={'posted': [('readonly', True)], 'reconciled': [('readonly', True)]})

    def get_payment_vals(self):
        res=super(account_register_payments_inherited,self).get_payment_vals()
        res.update({
            'due_date':self.due_date,
            'numbering':self.numbering,
        })
        return res