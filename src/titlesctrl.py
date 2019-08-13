import web
from aux import logger_instance, debug_mode, strtolist, require_params_or_fail
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
        logger.debug("Data: %s" % (web.data().decode('utf-8')))

        data    = json.loads(web.data().decode('utf-8'))
        title   = data.get('title')
        work_id = data.get('UUID') or data.get('uuid')

        titles = strtolist(title)
        require_params_or_fail([work_id], "a (work) UUID")
        require_params_or_fail([titles], "at least a title")

        work = Work.find_or_fail(work_id, titles=titles)
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

        require_params_or_fail([title, work_id], "(work) UUID and title")

        try:
            work = Work(work_id, title=[title])
            assert work.exists()
        except Exception:
            raise Error(BADPARAMS, msg="Unknown work '%s'" % (work_id))

        work.delete_titles()
        work.load_titles()
        work.load_identifiers()

        return [work.__dict__]
