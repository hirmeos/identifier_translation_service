import web
from api import json, logging, json_response, api_response, check_token
from errors import Error, NOTALLOWED, BADPARAMS
from models import Work, Identifier, UriScheme

logger = logging.getLogger(__name__)


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
        logger.debug("Data: %s" % (web.data()))

        data      = json.loads(web.data())
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

        try:
            work = Work(work_id, uris=uris)
            assert work.exists()
        except AssertionError:
            raise Error(BADPARAMS, msg="Unknown work '%s'" % (work_id))

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

        try:
            work = Work(work_id, uris=uris)
            assert work.exists()
        except AssertionError:
            raise Error(BADPARAMS, msg="Unknown work '%s'" % (work_id))

        work.delete_uris()
        work.load_identifiers()

        return [work.__dict__]
