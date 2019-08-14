import web
from aux import logger_instance, debug_mode
from validation import require_params_or_fail
from api import json, json_response, api_response, check_token
from models.work import Work

logger = logger_instance(__name__)
web.config.debug = debug_mode()


class RelationsController():
    """Handles work_relation related actions"""

    @json_response
    @api_response
    @check_token
    def POST(self, name):
        """Create a work relation"""
        data = json.loads(web.data().decode('utf-8'))
        parent_uuid = data.get('parent_UUID') or data.get('parent_uuid')
        child_uuid = data.get('child_UUID') or data.get('child_uuid')

        require_params_or_fail([parent_uuid, child_uuid],
                               'a parent and a child UUID')

        parent = Work.find_or_fail(parent_uuid)
        child = Work.find_or_fail(child_uuid)

        parent.set_children([child.UUID])
        parent.save()

        parent.load_titles()
        parent.load_identifiers()
        parent.load_children()
        parent.load_parents()

        return [parent.__dict__]

    @json_response
    def OPTIONS(self, name):
        return
