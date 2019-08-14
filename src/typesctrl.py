import web
from aux import (logger_instance, debug_mode, sort_alphabetically,
                 validate_sorting_or_fail)
from api import json_response, api_response, check_token
from errors import Error, NORESULT
from models.worktype import WorkType
from models.operations import results_to_work_types

logger = logger_instance(__name__)
web.config.debug = debug_mode()


class TypesController():
    """Handles work types related actions"""

    @json_response
    @api_response
    @check_token
    def GET(self, name):
        """List all work types"""
        logger.debug("Query: %s" % (web.input()))

        sort = web.input().get('sort')
        order = web.input().get('order', 'asc')
        if sort:
            validate_sorting_or_fail(["work_type"], sort, order)
        results = WorkType.get_all()

        if not results:
            raise Error(NORESULT)

        data = results_to_work_types(results)

        if sort:
            return sort_alphabetically(data, sort, order)
        return data

    @json_response
    def OPTIONS(self, name):
        return
