import web
from aux import logger_instance, debug_mode, require_params_or_fail
from api import json, json_response, api_response, check_token
from errors import Error, BADPARAMS
from models.work import Work
from models.identifier import Identifier
from models.urischeme import UriScheme

logger = logger_instance(__name__)
web.config.debug = debug_mode()


class UrisController():
    """Handles URI related actions"""

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

        require_params_or_fail([uri, work_id], "a (work) UUID and a URI")

        try:
            scheme, value = Identifier.split_uri(uri)
            uris = [{'URI': uri, 'canonical': canonical}]
        except Exception:
            raise Error(BADPARAMS, msg="Invalid URI '%s'" % (uri))

        UriScheme.find_or_fail(scheme)

        work = Work.find_or_fail(work_id, uris=uris)
        work.save()
        work.load_identifiers()

        return [work.__dict__]

    @json_response
    @api_response
    @check_token
    def DELETE(self, name):
        """Delete an identifier"""
        logger.debug("Data: %s" % (web.input()))

        work_id = web.input().get('UUID') or web.input().get('uuid')
        uri     = web.input().get('URI') or web.input().get('uri')

        require_params_or_fail([uri, work_id], "a (work) UUID and a URI")

        try:
            scheme, value = Identifier.split_uri(uri)
            uris = [{'URI': uri}]
        except Exception:
            raise Error(BADPARAMS, msg="Invalid URI '%s'" % (uri))

        work = Work.find_or_fail(work_id, uris)

        work.delete_uris()
        work.load_identifiers()

        return [work.__dict__]
