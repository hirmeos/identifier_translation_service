import re
import web
import urllib
from api import *
from errors import *
from models import Account

logger = logging.getLogger(__name__)

class AuthController(object):
    """Handles authentication tokens"""

    @json_response
    @api_response
    def POST(self, name):
        """Login - obtain a token"""
        logger.debug(web.input())
        email  = web.input().get('email')
        passwd = web.input().get('password')

        try:
            assert email
            assert passwd
        except Exception:
            raise Error(BADAUTH)

        AuthController.validate_email(email)

        try:
            account = Account(email, passwd)
            if not account.is_valid():
                raise Error(BADAUTH)
        except Exception as e:
            logger.debug(e)
            raise Error(BADAUTH)

        result = account.__dict__
        result['token'] = account.renew_token()
        del result['password']
        del result['hash']
        return [result]

    @staticmethod
    def validate_email(email):
        if not AuthController.is_valid_email(email):
            raise Error(BADPARAMS, msg="Invalid email provided.")

    @staticmethod
    def is_valid_email(email):
        check_email = re.compile(r"[^@]+@[^@]+\.[^@]+")
        return check_email.match(email) is not None

    @staticmethod
    def create_account(email, password, name, surname, authority = 'user'):
        """No API endpoint calls this method - it's meant to be used via CLI"""
        AuthController.validate_email(email)
        try:
            account = Account(email, password, name, surname, authority)
            account.save()
        except Exception as e:
            logger.error(e)
            raise Error(FATAL)

    def GET(self, name):
        raise Error(NOTALLOWED)

    def PUT(self, name):
        raise Error(NOTALLOWED)

    def DELETE(self, name):
        raise Error(NOTALLOWED)

    @json_response
    def OPTIONS(self, name):
        return
