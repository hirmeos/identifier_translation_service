import web
from aux import logger_instance, debug_mode
from api import json, json_response, api_response, check_token
from errors import Error, NOTALLOWED, BADPARAMS
from models import Work, Identifier, UriScheme

logger = logger_instance(__name__)
web.config.debug = debug_mode()


class UrisController(object):
    """Handles URI related actions"""

    @json_response
    @api_response
    @check_token
    def GET(self, name):
        raise Error(NOTALLOWED)

    @json_response
    @api_response
    @check_token
    def POST(self, name):
        """Add identifiers to an existing work"""
        logger.debug("Data: %s" % (web.data().decode('utf-8')))

        data      = json.loads(web.data().decode('utf-8'))
        uri       = data.get('URI') or data.get('uri')
        canonical = data.get('canonical') in (True, "true", "True")
        work_id   = data.get('UUID') or data.get('uuid')

        try:
            assert uri and work_id
        except AssertionError as error:
            logger.debug(error)
            raise Error(BADPARAMS, msg="You must provide a (work) UUID"
                        " and a URI")

        try:
            scheme, value = Identifier.split_uri(uri)
            uris = [{'URI': uri, 'canonical': canonical}]
        except Exception:
            raise Error(BADPARAMS, msg="Invalid URI '%s'" % (uri))

        try:
            assert UriScheme(scheme).exists()
        except AssertionError:
            raise Error(BADPARAMS, msg="Unknown URI scheme '%s'" % (scheme))

        work = Work.find_or_fail(work_id, uris=uris)
        work.save()
        work.load_identifiers()

        return [work.__dict__]

    @json_response
    @api_response
    @check_token
    def PUT(self, name):
        """Update an identifier"""
        raise Error(NOTALLOWED)

    @json_response
    @api_response
    @check_token
    def DELETE(self, name):
        """Delete an identifier"""
        logger.debug("Data: %s" % (web.input()))

        work_id = web.input().get('UUID') or web.input().get('uuid')
        uri     = web.input().get('URI') or web.input().get('uri')

        try:
            assert uri and work_id
        except AssertionError as error:
            logger.debug(error)
            raise Error(BADPARAMS, msg="You must provide a (work) UUID"
                        " and a URI")

        try:
            scheme, value = Identifier.split_uri(uri)
            uris = [{'URI': uri}]
        except Exception:
            raise Error(BADPARAMS, msg="Invalid URI '%s'" % (uri))

        work = Work.find_or_fail(work_id, uris)

        work.delete_uris()
        work.load_identifiers()

        return [work.__dict__]
