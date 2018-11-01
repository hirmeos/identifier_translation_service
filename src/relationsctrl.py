import web
from aux import logger_instance, debug_mode
from api import json, json_response, api_response, check_token
from errors import Error, BADPARAMS, NOTALLOWED
from models import Work

logger = logger_instance(__name__)
web.config.debug = debug_mode()


class RelationsController(object):
    """Handles work_relation related actions"""

    @json_response
    @api_response
    @check_token
    def GET(self, name):
        raise Error(NOTALLOWED)

    @json_response
    @api_response
    @check_token
    def POST(self, name):
        """Create a work relation"""
        logger.debug("Data: %s" % (web.data()))

        data        = json.loads(web.data())
        parent_uuid = data.get('parent_UUID') or data.get('parent_uuid')
        child_uuid  = data.get('child_UUID') or data.get('child_uuid')

        try:
            assert parent_uuid and child_uuid
        except AssertionError as error:
            logger.debug(error)
            raise Error(BADPARAMS, msg="You must provide a parent and a child"
                        "UUID")

        try:
            parent = Work(parent_uuid)
            assert parent.exists()
        except AssertionError as error:
            logger.debug(error)
            raise Error(BADPARAMS, msg="Invalid parent UUID provided.")

        try:
            assert Work.is_uuid(child_uuid)
            assert Work.uuid_exists(child_uuid)
        except AssertionError as error:
            logger.debug(error)
            raise Error(BADPARAMS, msg="Invalid child UUID provided.")

        parent.set_children([child_uuid])
        parent.save()

        parent.load_titles()
        parent.load_identifiers()
        parent.load_children()
        parent.load_parents()

        return [parent.__dict__]

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
