import web
from aux import logger_instance, debug_mode
from api import db
from errors import Error, BADPARAMS
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

    @staticmethod
    def find_or_fail(work_type):
        wtype = WorkType(work_type)
        if not wtype.exists():
            raise Error(BADPARAMS, msg="Unknown work type '%s'" % (work_type))
        return wtype
