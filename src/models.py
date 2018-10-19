import jwt
import uuid
import datetime
import psycopg2
from api import *
from uri import *
from errors import *
from pbkdf2 import crypt

logger = logging.getLogger(__name__)

class Work(object):
    def __init__(self, work_id, work_type = None, titles = [], uris = []):
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
        except:
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
            except:
                pass

    def delete_titles(self):
        for title in self.title:
            q = '''DELETE FROM work_title WHERE work_id = $work_id
                    AND title = $title'''
            db.query(q, dict(work_id=self.UUID, title=title))
            # now we delete the title if it's not linked to other work
            try:
                db.delete('title', dict(title=title), where="title=$title")
            except:
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
        except:
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
            result = db.select('work_type', options, where="work_type = $wtype")
            return result.first()["work_type"] == self.work_type
        except:
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
        except:
            return False

    @staticmethod
    def get_all():
        return db.select('uri_scheme')

class Identifier(object):
    def __init__(self, uri_scheme, uri_value, canonical, score, work_id = None, work_type = None):
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
            q = '''INSERT INTO uri VALUES ($sch, $val) ON CONFLICT DO NOTHING'''
            return db.query(q, option)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(error)
            raise Error(FATAL)

    @staticmethod
    def split_uri(uri_str):
        """Get the scheme (+namespace if not a URL), and value from URI."""
        uri = URI(uri_str)
        if uri.scheme.name in ['http','https']:
            scheme = uri.scheme.name
            value  = heirarchical
        else:
            # e.g. heirarchical = 'doi:10.11647/obp.0130';
            # we are asumming the path only contains one colon
            namespace, value = heirarchical.split(':', 1)
            scheme = ''.join([uri.scheme.name,':', namespace])
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
                    SELECT work_title.work_id, work_type,uri_scheme, uri_value,                            canonical, 0 AS score
                    FROM work_title INNER JOIN work USING(work_id)
                    INNER JOIN work_uri USING(work_id)
                    WHERE lower(work_title.title)  = $title '''+ clause +'''
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
                        WHERE 1 = 1 ''' + clause + ''') q
                    WHERE score <= ((length($title)/3)+1)
                ) query
                ORDER BY work_id,uri_scheme, uri_value, score, canonical
            ) result ORDER BY score ASC, canonical DESC;'''
            result = db.query(q, options)
            return result
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(error)
            raise Error(FATAL)

class Account(object):
    """API authentication accounts"""
    def __init__(self, email, password, name = '', surname ='', auth = 'user'):
        self.email     = email
        self.id        = "acct:"+email
        self.password  = password
        self.name      = name
        self.surname   = surname
        self.authority = auth

    def save(self):
        try:
            assert self.hash
        except AttributeError:
            self.hash_password()

        try:
            authdb.insert('account', account_id=self.id, email=self.email,
                          password=self.hash, authority=self.authority,
                          name=self.name, surname=self.surname)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(error)
            raise Error(FATAL)

    def hash_password(self):
        self.hash = crypt(self.password, iterations=PBKDF2_ITERATIONS)

    def renew_token(self):
        try:
            token = Token(sub=self.id)
            self.token = token.encoded().decode()
            if self.token:
                token.clear_previous()
                token.save()
            return self.token;
        except Exception as e:
            logger.error(e)
            raise Error(FATAL)

    def is_valid(self):
        options = dict(email=self.email)
        result = authdb.select('account', options, where="email = $email")
        if not result:
            return False
        res = result.first()
        self.hash = res["password"]
        self.authority = res["authority"]
        self.name = res["name"]
        self.surname = res["surname"]
        return self.is_password_correct()

    def is_password_correct(self):
        return self.hash == crypt(self.password, self.hash)

    @staticmethod
    def get_from_token(token):
        params = {'token': token}
        q = '''SELECT * FROM account WHERE account_id =
                 (SELECT account_id FROM account_token WHERE token = $token);'''
        try:
            return authdb.query(q, params)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(error)
            raise Error(FATAL)

class Token(object):
    """API tokens"""
    def __init__(self, token=None, sub=None, exp=None, iat=None):
        self.token = token
        self.sub = sub
        self.iat = iat if exp else datetime.datetime.utcnow()
        self.exp = exp if exp else self.iat + datetime.timedelta(
                      seconds=TOKEN_LIFETIME)
        self.load_payload()

    def load_payload(self):
        self.payload = {'exp': self.exp, 'iat': self.iat, 'sub': self.sub}

    def update_from_payload(self, payload):
        self.sub = payload['sub']
        self.iat = payload['iat']
        self.exp = payload['exp']
        self.load_payload()

    def encoded(self):
        if not self.token:
            self.token = jwt.encode(self.payload, SECRET_KEY, algorithm='HS256')
        return self.token

    def validate(self):
        try:
            payload = jwt.decode(self.token, SECRET_KEY)
            self.update_from_payload(payload)
            if not self.is_valid():
                raise jwt.InvalidTokenError()
            return self.sub
        except jwt.exceptions.DecodeError:
            raise Error(FORBIDDEN)
        except jwt.ExpiredSignatureError:
            raise Error(UNAUTHORIZED, msg="Signature expired.")
        except jwt.InvalidTokenError:
            raise Error(UNAUTHORIZED, msg="Invalid token.")

    def is_valid(self):
        result = authdb.select('account_token',
            where={'token': self.token, 'account_id': self.sub})
        return result and "token" in result.first()

    def clear_previous(self):
        options = {"id": self.sub}
        q = '''DELETE FROM token WHERE token =
                 (SELECT token FROM account_token WHERE account_id = $id);'''
        try:
            return authdb.query(q, options)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(error)
            raise Error(FATAL)

    def save(self):
        try:
            authdb.insert('token', token=self.token,
                          timestamp=self.iat.strftime('%Y-%m-%dT%H:%M:%S%z'),
                          expiry=self.exp.strftime('%Y-%m-%dT%H:%M:%S%z'))
            authdb.insert('account_token', account_id=self.sub,
                          token=self.token)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(error)
            raise Error(FATAL)

