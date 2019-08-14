import web
import uuid
import psycopg2
from aux import logger_instance, debug_mode
from api import db
from errors import Error, FATAL, BADPARAMS
from .operations import results_to_identifiers, do_query

logger = logger_instance(__name__)
web.config.debug = debug_mode()


class Work(object):
    def __init__(self, work_id, work_type=None, titles=[], uris=[]):
        self.UUID   = work_id
        self.type   = work_type if work_type else self.get_type()
        self.URI    = uris
        self.title  = titles if titles else self.get_titles()

    def get_type(self):
        options = dict(uuid=self.UUID)
        result = db.select('work', options,
                           what="work_type", where="work_id = $uuid")
        return result.first()["work_type"] if result else None

    def get_titles(self):
        options = dict(uuid=self.UUID)
        titles = db.select('work_title', options,
                           what="title", where="work_id = $uuid")
        return [(x["title"]) for x in titles] if titles else []

    def get_identifiers(self):
        options = dict(uuid=self.UUID)
        uris = db.select('work_uri', options,
                         what="uri_scheme, uri_value, canonical",
                         where="work_id = $uuid")
        return results_to_identifiers(uris)

    def get_children(self):
        options = dict(uuid=self.UUID)
        return db.select('work_relation', options, what="child_work_id",
                         where="parent_work_id=$uuid")

    def get_parents(self):
        options = dict(uuid=self.UUID)
        return db.select('work_relation', options, what="parent_work_id",
                         where="child_work_id=$uuid")

    def load_identifiers(self):
        self.URI = self.get_identifiers()

    def load_titles(self):
        self.title = self.get_titles()

    def set_attribute(self, attribute, value):
        self.__dict__.update({attribute: value})

    def load_children(self):
        self.load_relatives('child_work_id')

    def load_parents(self):
        self.load_relatives('parent_work_id')

    def load_relatives(self, key):
        data = self.get_children() if key == 'child_work_id' \
            else self.get_parents()
        ids = [(x[key]) for x in data] if data else []
        self.set_relatives(key, ids)

    def set_relatives(self, key, ids):
        if key == 'child_work_id':
            self.set_children(ids)
        else:
            self.set_parents(ids)

    def set_children(self, children):
        self.set_attribute('child', children)

    def set_parents(self, parents):
        self.set_attribute('parent', parents)

    def save(self):
        from .title import Title
        from .identifier import Identifier
        try:
            with db.transaction():
                q = '''INSERT INTO work (work_id, work_type)
                       VALUES ($work_id, $work_type) ON CONFLICT DO NOTHING'''
                db.query(q, dict(work_id=self.UUID, work_type=self.type))
                if not self.exists():
                    logger.error('Could not save record.')
                    raise Error(FATAL)

                for title in self.title:
                    t = Title(title)
                    t.save_if_not_exists()
                    q = '''INSERT INTO work_title (work_id, title)
                           VALUES ($work_id, $title) ON CONFLICT DO NOTHING'''
                    db.query(q, dict(work_id=self.UUID, title=title))

                for i in self.URI:
                    uri = i.get('URI') or i.get('uri')
                    is_canonical = i['canonical']
                    scheme, value = Identifier.split_uri(uri)
                    Identifier.insert_if_not_exist(scheme, value)
                    q = '''INSERT INTO work_uri (work_id, uri_scheme, uri_value,
                           canonical) VALUES
                           ($work_id, $uri_scheme, $uri_value, $canonical)
                           ON CONFLICT DO NOTHING'''
                    db.query(q, dict(work_id=self.UUID, uri_scheme=scheme,
                                     uri_value=value, canonical=is_canonical))

                try:
                    for c in self.child:
                        db.insert('work_relation', parent_work_id=self.UUID,
                                  child_work_id=c)
                except AttributeError:
                    pass
                try:
                    for p in self.parent:
                        db.insert('work_relation', parent_work_id=p,
                                  child_work_id=self.UUID)
                except AttributeError:
                    pass
        except (Exception, psycopg2.DatabaseError) as error:
            logger.debug(error)
            raise Error(FATAL)

    def exists(self):
        try:
            options = dict(uuid=self.UUID)
            result = db.select('work', options, where="work_id = $uuid")
            return result.first()["work_id"] == self.UUID
        except BaseException:
            return False

    def delete_uris(self):
        from .identifier import Identifier
        for i in self.URI:
            uri = i.get('URI') or i.get('uri')
            scheme, value = Identifier.split_uri(uri)
            q = '''DELETE FROM work_uri WHERE work_id = $work_id
                    AND uri_scheme = $scheme AND uri_value = $value'''
            db.query(q, dict(work_id=self.UUID, scheme=scheme, value=value))
            # now we delete the URI if it's not linked to other work
            q = '''DELETE FROM uri WHERE
                    uri_scheme = $scheme AND uri_value = $value'''
            try:
                db.query(q, dict(scheme=scheme, value=value))
            except BaseException:
                pass

    def delete_titles(self):
        for title in self.title:
            q = '''DELETE FROM work_title WHERE work_id = $work_id
                    AND title = $title'''
            db.query(q, dict(work_id=self.UUID, title=title))
            # now we delete the title if it's not linked to other work
            try:
                db.delete('title', dict(title=title), where="title=$title")
            except BaseException:
                pass

    def delete(self):
        q = '''DELETE FROM work WHERE work_id = $work_id'''
        db.query(q, dict(work_id=self.UUID))

    @staticmethod
    def generate_uuid():
        return str(uuid.uuid4())

    @staticmethod
    def is_uuid(input_uuid):
        try:
            uuid.UUID(input_uuid)
            return True
        except ValueError:
            return False

    @staticmethod
    def uuid_exists(work_id):
        try:
            options = dict(work_id=work_id)
            result = db.select('work', options, what="work_id",
                               where="work_id = $work_id")
            return result.first()["work_id"] == work_id
        except BaseException:
            return False

    @staticmethod
    def get_from_work_id(work_id):
        params = dict(uuid=work_id)
        clause = "AND work_id = $uuid"
        return Work.get_all(clause, params)

    @staticmethod
    def get_all(clause, params):
        q = '''SELECT DISTINCT(work.work_id), work_type, title, uri_scheme,
                      uri_value, canonical
                FROM work LEFT JOIN work_uri USING(work_id)
                    LEFT JOIN work_title USING(work_id)
                WHERE 1=1 ''' + clause + '''
                ORDER BY work_id;'''
        return do_query(q, params)

    @staticmethod
    def find_or_fail(work_id, wtype=None, titles=[], uris=[]):
        work = Work(work_id, work_type=wtype, titles=titles, uris=uris)
        if not work.exists():
            raise Error(BADPARAMS, msg="Unknown work '%s'" % (work_id))
        return work
