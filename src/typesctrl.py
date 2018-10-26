import re
import web
from api import logging, json_response, api_response, check_token, \
    results_to_work_types
from errors import Error, NOTALLOWED, NORESULT, BADFILTERS
from models import WorkType

logger = logging.getLogger(__name__)


class TypesController(object):
    """Handles work types related actions"""

    @json_response
    @api_response
    @check_token
    def GET(self, name):
        """List all work types"""
        logger.debug("Query: %s" % (web.input()))

        sort = web.input().get('sort')
        order = web.input().get('order', 'asc')
        try:
            if sort:
                assert sort in ["work_type"]
                assert order in ["asc", "desc"]
        except Exception:
            raise Error(BADFILTERS,
                        msg="Unknown sort '%s' '%s'" % (sort, order))
        results = WorkType.get_all()

        try:
            assert results
        except AssertionError:
            raise Error(NORESULT)

        data = results_to_work_types(results)

        if sort:
            reverse = order == "desc"
            return sorted(data,
                          key=lambda x: re.sub('[^A-Za-z]+', '', x[sort][0]),
                          reverse=reverse)
        return data

    @json_response
    @api_response
    @check_token
    def POST(self, name):
        raise Error(NOTALLOWED)

    @json_response
    @api_response
    @check_token
    def PUT(self, name):
        raise Error(NOTALLOWED)

    @json_response
    @api_response
    @check_token
    def DELETE(self, name):
        raise Error(NOTALLOWED)

    @json_response
    def OPTIONS(self, name):
        return
