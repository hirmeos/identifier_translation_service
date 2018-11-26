import uuid
import psycopg2
from aux import logger_instance
from api import db
from uri import URI
from errors import Error, FATAL

logger = logger_instance(__name__)


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
        return result.first()["work_type"]

    def get_titles(self):
        options = dict(uuid=self.UUID)
        titles = db.select('work_title', options,
                           what="title", where="work_id = $uuid")
        return [(x["title"]) for x in titles]

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
        c = self.get_children()
        self.set_children([(x["child_work_id"]) for x in c] if c else [])

    def load_parents(self):
        p = self.get_parents()
        self.set_parents([(x["parent_work_id"]) for x in p] if p else [])

    def set_children(self, children):
        self.set_attribute('child', children)

    def set_parents(self, parents):
        self.set_attribute('parent', parents)

    def save(self):
        try:
            with db.transaction():
                q = '''INSERT INTO work (work_id, work_type)
                       VALUES ($work_id, $work_type) ON CONFLICT DO NOTHING'''
                db.query(q, dict(work_id=self.UUID, work_type=self.type))
                assert self.exists()

                for title in self.title:
                    t = Title(title)
                    t.save_if_not_exists()
                    q = '''INSERT INTO work_title (work_id, title)
                           VALUES ($work_id, $title) ON CONFLICT DO NOTHING'''
                    db.query(q, dict(work_id=self.UUID, title=title))

                for i in self.URI:
                    uri = i['URI'] or i['uri']
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
        for i in self.URI:
            uri = i['URI'] or i['uri']
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
        try:
            q = '''SELECT DISTINCT(work.work_id), work_type, title, uri_scheme,
                          uri_value, canonical
                    FROM work LEFT JOIN work_uri USING(work_id)
                        LEFT JOIN work_title USING(work_id)
                    WHERE 1=1 ''' + clause + '''
                    ORDER BY work_id;'''
            result = db.query(q, params)
            return result
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(error)
            raise Error(FATAL)


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


class WorkType(object):
    def __init__(self, work_type):
        self.work_type = work_type

    def exists(self):
        try:
            options = dict(wtype=self.work_type)
            result = db.select('work_type', options,
                               where="work_type = $wtype")
            return result.first()["work_type"] == self.work_type
        except BaseException:
            return False

    @staticmethod
    def get_all():
        return db.select('work_type')


class UriScheme(object):
    def __init__(self, uri_scheme):
        self.uri_scheme = uri_scheme

    def exists(self):
        try:
            options = dict(scheme=self.uri_scheme)
            result = db.select('uri_scheme', options,
                               where="uri_scheme = $scheme")
            return result.first()["uri_scheme"] == self.uri_scheme
        except BaseException:
            return False

    @staticmethod
    def get_all():
        return db.select('uri_scheme')


class Identifier(object):
    def __init__(self, uri_scheme, uri_value, canonical, score,
                 work_id=None, work_type=None):
        self.URI_parts = {'scheme': uri_scheme, 'value': uri_value}
        self.canonical = canonical
        self.score     = score
        self.URI       = self.full_uri()
        if work_id:
            self.work  = Work(work_id, work_type).__dict__

    def is_canonical(self):
        return self.canonical

    def full_uri(self):
        return Identifier.rejoin_uri(self.URI_parts['scheme'],
                                     self.URI_parts['value'])

    @staticmethod
    def insert_if_not_exist(uri_scheme, uri_value):
        try:
            option = dict(sch=uri_scheme, val=uri_value)
            q = '''INSERT INTO uri VALUES($sch, $val) ON CONFLICT DO NOTHING'''
            return db.query(q, option)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(error)
            raise Error(FATAL)

    @staticmethod
    def split_uri(uri_str):
        """Get the scheme (+namespace if not a URL), and value from URI."""
        uri = URI(uri_str)
        if uri.scheme.name in ['http', 'https']:
            scheme = uri.scheme.name
            value  = uri.heirarchical
        else:
            # e.g. uri.heirarchical = 'doi:10.11647/obp.0130';
            # we are asumming the path only contains one colon
            namespace, value = uri.heirarchical.split(':', 1)
            scheme = ''.join([uri.scheme.name, ':', namespace])
            if namespace is "isbn":
                # we store hyphenless isbn numbers - remove hyphens from input
                value = value.replace("-", "")
        # we store lowercased URIs - let's lower input
        return [scheme.lower(), value.lower()]

    @staticmethod
    def rejoin_uri(scheme, value):
        """Construct a full URI joining the scheme and value"""
        uri = URI()
        uri.scheme = scheme
        uri.path = value
        return str(uri)

    @staticmethod
    def get_from_uri(input_scheme, input_value, clause, params):
        options = {"inscheme": input_scheme, "invalue": input_value}
        options.update(params)
        try:
            q = '''SELECT work_id, work_type, uri_scheme,
                           uri_value, canonical, 0 AS score
                    FROM work_uri INNER JOIN work USING(work_id)
                    WHERE work_id IN (SELECT work_id FROM work_uri
                                      WHERE uri_scheme = $inscheme
                                      AND uri_value = $invalue)
                    ''' + clause + '''
                    ORDER BY canonical DESC;'''
            result = db.query(q, options)
            return result
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(error)
            raise Error(FATAL)

    @staticmethod
    def get_from_title(title, clause, params):
        options = {"title": title.lower()}
        options.update(params)
        try:
            q = '''SELECT * FROM (
                SELECT DISTINCT ON (work_id, uri_scheme, uri_value) work_id,
                       work_type, uri_scheme, uri_value, canonical, score
                FROM (
                    SELECT work_title.work_id, work_type,uri_scheme, uri_value,
                           canonical, 0 AS score
                    FROM work_title INNER JOIN work USING(work_id)
                    INNER JOIN work_uri USING(work_id)
                    WHERE lower(work_title.title)  = $title ''' + clause + '''
                    UNION
                    SELECT work_title.work_id, work_type,uri_scheme, uri_value,
                            canonical, 1 AS score
                    FROM work_title INNER JOIN work USING(work_id)
                    INNER JOIN work_uri USING(work_id)
                    WHERE substr(lower(work_title.title), 1, length($title))
                          = $title ''' + clause + '''
                    UNION
                    SELECT work_title.work_id, work_type,uri_scheme, uri_value,
                           canonical, 1 AS score
                    FROM work_title INNER JOIN work USING(work_id)
                    INNER JOIN work_uri USING(work_id)
                    WHERE substr($title, 1, length(work_title.title))
                          = lower(work_title.title) ''' + clause + '''
                    UNION
                    SELECT * FROM (
                        SELECT work_title.work_id, work_type, uri_scheme,
                              uri_value, canonical,
                              levenshtein(lower(work_title.title), $title)
                                as score
                        FROM work_title INNER JOIN work USING(work_id)
                        INNER JOIN work_uri USING(work_id)
                        WHERE pg_column_size(title) < 255 ''' + clause + ''') q
                    WHERE score <= ((length($title)/3)+1)
                ) query
                ORDER BY work_id,uri_scheme, uri_value, score, canonical
            ) result ORDER BY score ASC, canonical DESC;'''
            result = db.query(q, options)
            return result
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(error)
            raise Error(FATAL)


def results_to_identifiers(results):
    return [(result_to_identifier(e).__dict__) for e in results]


def result_to_identifier(r):
    return Identifier(r["uri_scheme"], r["uri_value"], r["canonical"],
                      r["score"] if "score" in r else 0,
                      r["work_id"] if "work_id" in r else None,
                      r["work_type"] if "work_type" in r else None)


def result_to_work(r):
    work = Work(r["work_id"], r["work_type"] if "work_type" in r else None,
                r["titles"] if "titles" in r else [])
    return work


def results_to_titles(results):
    return [(result_to_title(e).__dict__) for e in results]


def result_to_title(r):
    return Title(r["title"])


def results_to_work_types(results):
    return [(result_to_work_type(e).__dict__) for e in results]


def result_to_work_type(r):
    return WorkType(r["work_type"])


def results_to_works(results, include_relatives=False):
    """Iterate the results to get distinct works with associated identifiers.

    Without this method we would need to query the list of work_ids, then
    their titles and uris - iterating the full data set, filtering as needed,
    is a lot faster.
    """
    data     = []  # output
    titles   = []  # temporary array of work titles
    uris     = []  # temp array of work URIs (strings, used for comparison)
    uris_fmt = []  # temporary array of work URIs (Identifier objects)
    last     = len(results) - 1

    i = 0
    for e in results:
        if i == 0:
            # we can't do cur=results[0] outsise--it moves IterBetter's pointer
            cur = e
        if e["work_id"] != cur["work_id"]:
            cur["titles"] = titles
            cur["URI"] = uris_fmt
            work = result_to_work(cur)
            work.URI = results_to_identifiers(cur["URI"])
            if include_relatives:
                work.load_children()
                work.load_parents()
            data.append(work.__dict__)
            titles = []
            uris = []
            uris_fmt = []
            cur = e

        if e["title"] not in titles:
            titles.append(e["title"])
        if [e["uri_scheme"], e["uri_value"], e["canonical"]] not in uris:
            uris.append([e["uri_scheme"], e["uri_value"], e["canonical"]])
            uris_fmt.append({"uri_scheme": e["uri_scheme"],
                             "uri_value": e["uri_value"],
                             "canonical": e["canonical"]})
        if i == last:
            cur["titles"] = titles
            cur["URI"] = uris_fmt
            work = result_to_work(cur)
            work.URI = results_to_identifiers(cur["URI"])
            if include_relatives:
                work.load_children()
                work.load_parents()
            data.append(work.__dict__)
        i += 1
    return data
