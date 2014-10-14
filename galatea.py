#This file is part galatea module for Tryton.
#The COPYRIGHT file at the top level of this repository contains 
#the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from email import Utils
from email.header import Header
from email.mime.text import MIMEText

import pytz
import random
import string

try:
    import hashlib
except ImportError:
    hashlib = None
    import sha

__all__ = ['GalateaWebSite', 'GalateaWebsiteCountry', 'GalateaWebsiteCurrency',
    'GalateaUser', 'GalateaUserWebSite', 'GalateaSendPasswordStart',
    'GalateaSendPasswordResult', 'GalateaSendPassword']
__metaclass__ = PoolMeta


class GalateaWebSite(ModelSQL, ModelView):
    'Galatea Web Site'
    __name__ = "galatea.website"
    name = fields.Char('Name', required=True, select=True)
    uri = fields.Char('Uri', required=True,
        help='Base Uri Site (with "/")')
    folder = fields.Char('Folder', required=True,
        help='Flask App directory')
    static_folder = fields.Char('Static Folder', required=True,
        help='Flask Static directory')
    company = fields.Many2One('company.company', 'Company', required=True)
    active = fields.Boolean('Active')
    registration = fields.Boolean('Registration',
        help='Add website in users when users do a new registration')
    countries = fields.Many2Many(
        'galatea.website-country.country', 'website', 'country',
        'Countries Available')
    currency = fields.Many2One('currency.currency', 'Currency', required=True)
    timezone = fields.Selection(
        [(x, x) for x in pytz.common_timezones], 'Timezone', translate=False
        )
    smtp_server = fields.Many2One('smtp.server', 'SMTP Server',
        domain=[('state', '=', 'done')], required=True)

    @classmethod
    def __setup__(cls):
        super(GalateaWebSite, cls).__setup__()
        cls._sql_constraints = [
            ('name_uniq', 'UNIQUE(name)',
             'Another site with the same name already exists!')
            ]
        cls._error_messages.update({
                'smtp_error': 'Wrong connection to SMTP server. Not send email.',
                })

    @staticmethod
    def default_timezone():
        return 'UTC'

    @staticmethod
    def default_active():
        return True

    @staticmethod
    def default_registration():
        return True

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def send_email(server, recipients, subject, body):
        Website = Pool().get('galatea.website')
        SMTP = Pool().get('smtp.server')

        from_ = server.smtp_email
        if server.smtp_use_email:
            from_ = server.smtp_email

        msg = MIMEText(body, _charset='utf-8')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = from_
        msg['To'] = ', '.join(recipients)
        msg['Reply-to'] = server.smtp_email
        # msg['Date']     = Utils.formatdate(localtime = 1)
        msg['Message-ID'] = Utils.make_msgid()

        try:
            server = SMTP.get_smtp_server(server)
            server.sendmail(from_, recipients, msg.as_string())
            server.quit()
        except:
            Website.raise_user_error('smtp_error')


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
    password = fields.Char('Password')
    salt = fields.Char('Salt', size=8)
    activation_code = fields.Char('Unique Activation Code')
    company = fields.Many2One('company.company', 'Company', required=True)
    timezone = fields.Selection(
        [(x, x) for x in pytz.common_timezones], 'Timezone', translate=False
        )
    manager = fields.Boolean('Manager', help='Allow user in manager sections')
    active = fields.Boolean('Active', help='Allow login users')
    websites = fields.Many2Many('galatea.user-galatea.website', 
        'user', 'website', 'Websites',
        help='Users will be available this websites to login')

    @staticmethod
    def default_timezone():
        return "UTC"

    @staticmethod
    def default_active():
        return True

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_websites():
        Website = Pool().get('galatea.website')
        return [p.id for p in Website.search([('registration','=',True)])]

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
        if values.get('password'):
            values['salt'] = ''.join(random.sample(
                string.ascii_letters + string.digits, 8))
            password = values['password'] + values['salt']
            if hashlib:
                digest = hashlib.sha1(password).hexdigest()
            else:
                digest = sha.new(password).hexdigest()
            values['password'] = digest

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


class GalateaUserWebSite(ModelSQL):
    'Galatea User - Website'
    __name__ = 'galatea.user-galatea.website'
    _table = 'galatea_user_galatea_website'
    user = fields.Many2One('galatea.user', 'User', ondelete='CASCADE',
            select=True, required=True)
    website = fields.Many2One('galatea.website', 'Website', ondelete='RESTRICT',
            select=True, required=True)


class GalateaSendPasswordStart(ModelView):
    'Galatea User Start'
    __name__ = 'galatea.send.password.start'
    password = fields.Char('Password', required=True)
    website = fields.Many2One('galatea.website', 'Website', required=True,
        help='Select shop will be export this product.')

    @classmethod
    def default_website(cls):
        Website = Pool().get('galatea.website')
        websites = Website.search([('active', '=', True)])
        if len(websites) >= 1:
            return websites[0].id


class GalateaSendPasswordResult(ModelView):
    'Galatea Use Result'
    __name__ = 'galatea.send.password.result'
    info = fields.Text('Info', readonly=True)


class GalateaSendPassword(Wizard):
    'Send Password by email'
    __name__ = "galatea.send.password"
    start = StateView('galatea.send.password.start',
        'galatea.galatea_send_password_start', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Send', 'send', 'tryton-ok', default=True),
            ])
    send = StateTransition()
    result = StateView('galatea.send.password.result',
        'galatea.galatea_send_password_result', [
            Button('Close', 'end', 'tryton-close'),
            ])

    @classmethod
    def __setup__(cls):
        super(GalateaSendPassword, cls).__setup__()
        cls._error_messages.update({
                'send_info': 'Send new password to %s',
                'email_subject': '%s. New password reset',
                'email_text': 'Hello %s\n' \
                    'New password reset for your user account %s: %s\n\n' \
                    '%s\n\n' \
                    'You could drop this email.\n' \
                    'Don\'t repply this email. It\'s was generated automatically'
                })

    def transition_send(self):
        pool = Pool()
        Website = pool.get('galatea.website')
        User = pool.get('galatea.user')

        password = self.start.password
        website = self.start.website

        users = User.search([('id', 'in', Transaction().context['active_ids'])])

        for user in users:
            recipients = [user.email]
            sites = []
            for site in user.websites:
                sites.append(site.uri)
            subject = self.raise_user_error('email_subject',
                (website.name),
                raise_exception=False)
            body = self.raise_user_error('email_text',
                (user.display_name, user.email, password, "\n".join(sites)),
                raise_exception=False)

            Website.send_email(website.smtp_server, recipients, subject, body)

        User.write(users, {'password': password})

        self.result.info = self.raise_user_error('send_info',
                (','.join(str(u.email) for u in users)),
                raise_exception=False)
        return 'result'

    def default_result(self, fields):
        info_ = self.result.info
        return {
            'info': info_,
            }
