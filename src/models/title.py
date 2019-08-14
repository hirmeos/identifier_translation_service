import web
import psycopg2
from aux import logger_instance, debug_mode
from api import db
from errors import Error, FATAL

logger = logger_instance(__name__)
web.config.debug = debug_mode()


class Title(object):
    def __init__(self, title):
        self.title = title

    def save_if_not_exists(self):
        try:
            option = dict(title=self.title)
            q = '''INSERT INTO title VALUES ($title) ON CONFLICT DO NOTHING'''
            return db.query(q, option)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(error)
            raise Error(FATAL)

    @staticmethod
    def get_all():
        return db.select('title')
