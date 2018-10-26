import re
import web
from api import json, logging, json_response, api_response
from errors import Error, BADPARAMS, NOTALLOWED, \
    BADAUTH, FATAL
from models import Account, Token

logger = logging.getLogger(__name__)


class AuthController(object):
    """Handles authentication tokens"""

    @json_response
    @api_response
    def GET(self, name):
        """Check a token"""
        logger.debug("Query: %s" % (web.input()))

        intoken = web.input().get('token')
        token = Token(intoken)
        token.validate()

        try:
            user = Account.get_from_token(token.token).first()
            logger.debug(user)
            account = Account(user['email'], user['password'], user['name'],
                              user['surname'], user['authority'])
        except Exception as e:
            logger.debug(e)
            raise Error(BADAUTH)

        result = account.__dict__
        result['token'] = token.token
        del result['password']
        return [result]

    @json_response
    @api_response
    def POST(self, name):
        """Login - obtain a token"""
        logger.debug(web.data())

        data   = json.loads(web.data())
        email  = data.get('email')
        passwd = data.get('password')

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
    def create_account(email, password, name, surname, authority='user'):
        """No API endpoint calls this method - it's meant to be used via CLI"""
        AuthController.validate_email(email)
        try:
            account = Account(email, password, name, surname, authority)
            account.save()
        except Exception as e:
            logger.error(e)
            raise Error(FATAL)

    def PUT(self, name):
        raise Error(NOTALLOWED)

    def DELETE(self, name):
        raise Error(NOTALLOWED)

    @json_response
    def OPTIONS(self, name):
        return
