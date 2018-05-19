# -*- coding: utf-8 -*-

from openerp import models,fields,api,tools
from openerp.tools.translate import _
from datetime import datetime
import time
import pytz
from pytz import timezone


def utc2local(d):
    utc = pytz.utc
    d1=datetime.strptime(d, '%Y-%m-%d %H:%M:%S').replace(tzinfo=utc)
    europe = timezone('Europe/Paris')
    d2 = d1.astimezone(europe)
    d3=d2.strftime('%d/%m/%Y %H:%M:%S')
    return unicode(d3)


class is_badge(models.Model):
    _name='is.badge'
    _order='employee'

    _sql_constraints = [('name_uniq','UNIQUE(name)', u'Ce badge existe déjà')]

    name     = fields.Char("Code",size=20,required=True, select=True)
    employee = fields.Many2one('hr.employee', 'Employé', required=False, ondelete='set null', help="Sélectionnez un employé")


class is_jour_ferie(models.Model):
    _name='is.jour.ferie'
    _order='date'

    name      = fields.Char("Intitulé",size=100,help='Intitulé du jour férié (ex : Pâques)', required=True, select=True)
    date      = fields.Date("Date",required=True)
    jour_fixe = fields.Boolean('jour férié fixe',  help="Cocher pour préciser que ce jour férié est valable tous les ans")


class is_pointage_commentaire(models.Model):
    _name='is.pointage.commentaire'
    _order='name desc'

    name        = fields.Date("Date",required=True,default=lambda *a: time)
    employee    = fields.Many2one('hr.employee', 'Employé', required=True, ondelete='set null', help="Sélectionnez un employé", select=True)
    commentaire = fields.Char('Commentaire', size=40, help="Mettre un commentaire court sur 40 caractères maximum")


class is_pointage(models.Model):
    _name='is.pointage'
    _order='name desc'

    name=fields.Datetime("Date Heure",required=True, default=lambda *a: time)
    employee=fields.Many2one('hr.employee', 'Employé', required=True, ondelete='set null', help="Sélectionnez un employé", select=True)
    entree_sortie=fields.Selection([("E", "Entrée"), ("S", "Sortie")], "Entrée/Sortie", required=True)
    pointeuse=fields.Char('Pointeuse', help='Adresse IP du lecteur de badges', required=False)
    note=fields.Char('Commentaire', size=20, help="Mettre un commentaire court sur 20 caractères maximum")
    commentaire=fields.Text('Traçabilité')


    def id2employee(self, cr, uid, id):
        employee_obj = self.pool.get('hr.employee')
        employee = employee_obj.browse(cr, uid, id)
        return employee.name


    def write(self, cr, uid, ids, vals, context=None):
        now = datetime.now(timezone('Europe/Berlin'))
        user_obj = self.pool.get('res.users')
        user = user_obj.browse(cr, uid, uid, context=context)
        this = self.pool.get(str(self))
        doc = this.browse(cr, uid, ids, context=context)
        commentaire=[]
        n=unicode(now.strftime('%d/%m/%Y'))+u" à "+unicode(now.strftime('%H:%M:%S'))
        if 'name' in vals:
            d1=utc2local(doc.name)
            d2=utc2local(vals["name"])
            commentaire.append(u"le " + n + u" par " + user.name + u" : Date Heure " + d1 + u" => " + d2)
        if 'employee' in vals:
            e1=doc.employee.name
            e2=self.id2employee(cr, uid, vals["employee"])
            commentaire.append(u"le " + n + u" par " + user.name + u" : Employé " + e1 + u" => " + e2)
        if 'entree_sortie' in vals:
            es1=doc.entree_sortie
            es2=vals["entree_sortie"]
            commentaire.append(u"le " + n + u" par " + user.name + u" : Entrée/Sortie " + es1 + u" => " + es2)
        if 'name' in vals or 'employee' in vals or 'entree_sortie' in vals :
            if doc.commentaire:
                commentaire.append(doc.commentaire)
            vals.update({'commentaire': '\n'.join(commentaire)})
        return super(is_pointage, self).write(cr, uid, ids, vals, context=context)


