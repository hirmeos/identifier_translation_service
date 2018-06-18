import re
import web
import urllib
from api import *
from errors import *
from models import Work

logger = logging.getLogger(__name__)

class WorksController(object):
    """Handles work related actions"""

    @json_response
    @api_response
    @check_token
    def GET(self, name):
        """List a work if UUID provided otherwise list all works"""
        logger.debug("Query: %s" % (web.input()))

        work_id = web.input().get('uuid') or web.input().get('UUID')

        if work_id:
            results = Work.get_from_work_id(work_id)
            sort = ""
        else:
            filters = web.input().get('filter')
            sort = web.input().get('sort')
            order = web.input().get('order', 'asc')
            clause, params = build_parms(filters)
            try:
                if sort:
                    assert sort in ["title"]
                    assert order in ["asc", "desc"]
            except:
                raise Error(BADFILTERS,
                            msg = "Unknown sort '%s' '%s'" % (sort, order))
            results = Work.get_all(clause, params)

        if not results:
            raise Error(NORESULT)
        data = results_to_works(results)

        if sort:
            reverse = order == "desc"
            # we sort by each work's (first) title, ignoring special chars
            return sorted(data,
                  key=lambda x: re.sub('[^A-Za-z0-9]+', '', x[sort][0]),
                  reverse=reverse)
        return data

    @json_response
    @api_response
    @check_token
    def POST(self, name):
        """Create a work"""
        raise Error(NOTALLOWED)

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

