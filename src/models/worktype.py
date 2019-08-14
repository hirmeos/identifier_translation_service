import web
from aux import logger_instance, debug_mode
from api import db
from .unarytable import UnaryTable

logger = logger_instance(__name__)
web.config.debug = debug_mode()


class WorkType(UnaryTable):
    table_name = "work_type"

    def __init__(self, work_type):
        self.work_type = work_type

    @staticmethod
    def get_all():
        return db.select(WorkType.table_name)
