import web
from aux import logger_instance, debug_mode, strtolist
from api import json, json_response, api_response, check_token
from errors import Error, BADPARAMS, NOTALLOWED
from models import Work, Title, results_to_titles

logger = logger_instance(__name__)
web.config.debug = debug_mode()


class TitlesController(object):
    """Handles title related actions"""

    @json_response
    @api_response
    @check_token
    def GET(self, name):
        """List all titles"""
        results = Title.get_all()
        return results_to_titles(results)

    @json_response
    @api_response
    @check_token
    def POST(self, name):
        """Add titles to an existing work"""
        logger.debug("Data: %s" % (web.data()))

        data    = json.loads(web.data())
        title   = data.get('title')
        work_id = data.get('UUID') or data.get('uuid')

        try:
            titles = strtolist(title)
            assert titles and work_id
        except AssertionError as error:
            logger.debug(error)
            raise Error(BADPARAMS, msg="You must provide a (work) UUID"
                        " and at least a title")

        try:
            work = Work(work_id, titles=titles)
            assert work.exists()
        except Exception:
            raise Error(BADPARAMS, msg="Unknown work '%s'" % (work_id))

        work.save()
        work.load_titles()
        work.load_identifiers()

        return [work.__dict__]

    @json_response
    @api_response
    @check_token
    def PUT(self, name):
        """Update a title"""
        raise Error(NOTALLOWED)

    @json_response
    @api_response
    @check_token
    def DELETE(self, name):
        """Delete a title"""
        logger.debug("Data: %s" % (web.input()))

        work_id = web.input().get('UUID') or web.input().get('uuid')
        title   = web.input().get('title')

        try:
            assert title and work_id
        except AssertionError as error:
            logger.debug(error)
            raise Error(BADPARAMS, msg="You must provide a (work) UUID"
                        " and a title")

        try:
            work = Work(work_id, title=[title])
            assert work.exists()
        except Exception:
            raise Error(BADPARAMS, msg="Unknown work '%s'" % (work_id))

        work.delete_titles()
        work.load_titles()
        work.load_identifiers()

        return [work.__dict__]
