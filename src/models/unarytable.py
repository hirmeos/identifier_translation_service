import web
from aux import logger_instance, debug_mode
from api import db

logger = logger_instance(__name__)
web.config.debug = debug_mode()


class UnaryTable(object):
    table_name = ""

    def exists(self):
        try:
            where = "%s = $%s" % (self.table_name, self.table_name)
            result = db.select(self.table_name, self.__dict__, where=where)
            candidate = self.__dict__[self.table_name]
            return result.first()[self.table_name] == candidate
        except BaseException:
            return False
