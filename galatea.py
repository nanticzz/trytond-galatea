#This file is part galatea module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import PoolMeta
from trytond.transaction import Transaction

import pytz
import random
import string

__all__ = ['GalateaWebSite', 'GalateaWebsiteCountry', 'GalateaWebsiteCurrency',
    'GalateaUser']
__metaclass__ = PoolMeta


class GalateaWebSite(ModelSQL, ModelView):
    'Galatea Web Site'
    __name__ = "galatea.website"
    name = fields.Char('Name', required=True, select=True)
    company = fields.Many2One('company.company', 'Company', required=True)
    active = fields.Boolean('Active')
    countries = fields.Many2Many(
        'galatea.website-country.country', 'website', 'country',
        'Countries Available')
    currencies = fields.Many2Many(
        'galatea.website-currency.currency',
        'website', 'currency', 'Currencies Available')
    timezone = fields.Selection(
        [(x, x) for x in pytz.common_timezones], 'Timezone', translate=False
        )
    smtp_server = fields.Many2One('smtp.server', 'SMTP Server',
        domain=[('state', '=', 'done')], required=True)
    login = fields.Boolean('Login',
        help='Allow login users')
    registration = fields.Boolean('Registration',
        help='Allow registration users')

    @staticmethod
    def default_timezone():
        return 'UTC'

    @staticmethod
    def default_active():
        return True

    @staticmethod
    def default_login():
        return True

    @staticmethod
    def default_registration():
        return True

    @classmethod
    def __setup__(cls):
        super(GalateaWebSite, cls).__setup__()
        cls._sql_constraints = [
            ('name_uniq', 'UNIQUE(name)',
             'Another site with the same name already exists!')
        ]


class GalateaWebsiteCountry(ModelSQL):
    "Website Country Relations"
    __name__ = 'galatea.website-country.country'
    website = fields.Many2One('galatea.website', 'Website')
    country = fields.Many2One('country.country', 'Country')


class GalateaWebsiteCurrency(ModelSQL):
    "Currencies to be made available on website"
    __name__ = 'galatea.website-currency.currency'
    _table = 'website_currency_rel'
    website = fields.Many2One(
        'galatea.website', 'Website',
        ondelete='CASCADE', select=1, required=True)
    currency = fields.Many2One(
        'currency.currency', 'Currency',
        ondelete='CASCADE', select=1, required=True)


class GalateaUser(ModelSQL, ModelView):
    """Galatea Users"""
    __name__ = "galatea.user"
    _rec_name = 'display_name'

    party = fields.Many2One('party.party', 'Party', required=True,
        ondelete='CASCADE')
    display_name = fields.Char('Display Name', required=True)
    email = fields.Char("e-Mail", required=True)
    password = fields.Sha('Password')
    salt = fields.Char('Salt', size=8)
    activation_code = fields.Char('Unique Activation Code')
    company = fields.Many2One('company.company', 'Company', required=True)
    timezone = fields.Selection(
        [(x, x) for x in pytz.common_timezones], 'Timezone', translate=False
        )

    @staticmethod
    def default_timezone():
        return "UTC"

    @staticmethod
    def default_company():
        return Transaction().context.get('company') or False

    @classmethod
    def __setup__(cls):
        super(GalateaUser, cls).__setup__()
        cls._sql_constraints += [
            ('unique_email_company', 'UNIQUE(email, company)',
                'Email must be unique in a company'),
        ]

    @staticmethod
    def _convert_values(values):
        """
        A helper method which looks if the password is specified in the values.
        If it is, then the salt is also made and added

        :param values: A dictionary of field: value pairs
        """
        if 'password' in values and values['password']:
            values['salt'] = ''.join(random.sample(
                string.ascii_letters + string.digits, 8))
            values['password'] += values['salt']

        return values

    @classmethod
    def create(cls, vlist):
        "Add salt before saving"
        vlist = [cls._convert_values(vals.copy()) for vals in vlist]
        return super(GalateaUser, cls).create(vlist)

    @classmethod
    def write(cls, users, values):
        "Update salt before saving"
        return super(GalateaUser, cls).write(users, cls._convert_values(values))
