import re
import web
import urllib
from api import *
from errors import *
from models import Work, WorkType, Identifier, UriScheme

logger = logging.getLogger(__name__)

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
                                        + " and at least a title")

        try:
            work = Work(work_id, titles=titles)
            assert work.exists()
        except:
            raise Error(BADPARAMS, msg="Unknown work '%s'" % (work_id))

        work.save()
        work.load_titles()
        work.load_identifiers()

        return [work.__dict__]

    @json_response
    @api_response
    @check_token
    def PUT(self, name):
        """Update a work"""
        raise Error(NOTALLOWED)

    @json_response
    @api_response
    @check_token
    def DELETE(self, name):
        """Delete a work"""
        raise Error(NOTALLOWED)

