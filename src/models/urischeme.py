import web
from aux import logger_instance, debug_mode
from api import db
from .unarytable import UnaryTable

logger = logger_instance(__name__)
web.config.debug = debug_mode()


class UriScheme(UnaryTable):
    table_name = "uri_scheme"

    def __init__(self, uri_scheme):
        self.uri_scheme = uri_scheme

    @staticmethod
    def get_all():
        return db.select(UriScheme.table_name)
