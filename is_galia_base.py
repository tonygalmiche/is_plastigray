# -*- coding: utf-8 -*-

from openerp import models,fields,api
from openerp.tools.translate import _
import datetime
import pytz


class is_galia_base(models.Model):
    _name='is.galia.base'
    _order='num_eti desc'

    num_eti       = fields.Integer(u"N°Étiquette", select=True)
    soc           = fields.Integer(u"Société"    , select=True)
    type_eti      = fields.Char(u"Type étiquette", select=True)
    num_of        = fields.Char(u"N°OF"          , select=True)
    num_carton    = fields.Integer(u"N°Carton"   , select=True)
    qt_pieces     = fields.Integer(u"Qt Pièces")
    date_creation = fields.Datetime(u"Date de création")
    login         = fields.Char(u"Login")

