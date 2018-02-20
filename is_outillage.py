# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta


def date_prochain_controle(rec):
    date_prochain_controle=False
    if rec.controle_ids:
        for row in rec.controle_ids:
            if row.operation_controle_id.code=='arret':
                date_prochain_controle=False
                break
            if row.operation_controle_id.code!='maintenance':
                date_controle=row.date_controle
                if date_controle:
                    date_controle = datetime.strptime(date_controle, "%Y-%m-%d")
                    periodicite=0
                    if rec.periodicite:
                        try:
                            periodicite = int(rec.periodicite)
                        except ValueError:
                            continue
                    date_prochain_controle = date_controle + relativedelta(months=periodicite)
                    date_prochain_controle = date_prochain_controle.strftime('%Y-%m-%d')
                    break
    rec.date_prochain_controle = date_prochain_controle




