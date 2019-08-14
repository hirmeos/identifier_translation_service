import web
from aux import logger_instance, debug_mode
from uri import URI
from .operations import do_query

logger = logger_instance(__name__)
web.config.debug = debug_mode()


class Identifier(object):
    def __init__(self, uri_scheme, uri_value, canonical, score, work={}):
        self.URI_parts = {'scheme': uri_scheme, 'value': uri_value}
        self.canonical = canonical
        self.score     = score
        self.URI       = self.full_uri()
        work_id = work.get('work_id', None)
        work_type = work.get('work_type', None)
        if work_id:
            from .work import Work
            self.work = Work(work_id, work_type).__dict__

    def is_canonical(self):
        return self.canonical

    def full_uri(self):
        return Identifier.rejoin_uri(self.URI_parts['scheme'],
                                     self.URI_parts['value'])

    @staticmethod
    def insert_if_not_exist(uri_scheme, uri_value):
        option = dict(sch=uri_scheme, val=uri_value)
        q = '''INSERT INTO uri VALUES($sch, $val) ON CONFLICT DO NOTHING'''
        return do_query(q, option)

    @staticmethod
    def split_uri(uri_str):
        """Get the scheme (+namespace if not a URL), and value from URI."""
        uri = URI(uri_str)
        if uri.scheme.name in ['http', 'https']:
            scheme = uri.scheme.name
            # we're replacing the scheme instead of using heirarchical
            # to preserve query strings
            value  = uri_str.replace(uri.scheme.name + '://', '', 1)
        else:
            # e.g. uri.heirarchical = 'doi:10.11647/obp.0130';
            # we are asumming the path only contains one colon
            namespace, value = uri.heirarchical.split(':', 1)
            scheme = ''.join([uri.scheme.name, ':', namespace])
            if namespace == "isbn":
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
        q = '''SELECT work_id, work_type, uri_scheme,
                        uri_value, canonical, 0 AS score
                FROM work_uri INNER JOIN work USING(work_id)
                WHERE work_id IN (SELECT work_id FROM work_uri
                                  WHERE uri_scheme = lower($inscheme)
                                  AND uri_value = lower($invalue))
                ''' + clause + '''
                ORDER BY canonical DESC;'''
        return do_query(q, options)

    @staticmethod
    def get_from_title(title, clause, params, scheme='', value=''):
        if scheme and value:
            uri_clause = ''' AND work_title.work_id IN
                              (SELECT work_id FROM work_uri WHERE
                               uri_scheme = $scheme AND uri_value = $value)'''
        else:
            uri_clause = ''
        options = {"title": title.lower(), "scheme": scheme, "value": value}
        options.update(params)
        q = '''SELECT * FROM (
            SELECT DISTINCT ON (work_id, uri_scheme, uri_value) work_id,
                    work_type, uri_scheme, uri_value, canonical, score
            FROM (
                SELECT work_title.work_id, work_type,uri_scheme, uri_value,
                        canonical, 0 AS score
                FROM work_title INNER JOIN work USING(work_id)
                INNER JOIN work_uri USING(work_id)
                WHERE lower(work_title.title)  = $title ''' + clause + '''
                      ''' + uri_clause + '''
                UNION
                SELECT work_title.work_id, work_type,uri_scheme, uri_value,
                        canonical, 1 AS score
                FROM work_title INNER JOIN work USING(work_id)
                INNER JOIN work_uri USING(work_id)
                WHERE substr(lower(work_title.title), 1, length($title))
                      = $title ''' + clause + uri_clause + '''
                UNION
                SELECT work_title.work_id, work_type,uri_scheme, uri_value,
                        canonical, 1 AS score
                FROM work_title INNER JOIN work USING(work_id)
                INNER JOIN work_uri USING(work_id)
                WHERE substr($title, 1, length(work_title.title))
                      = lower(work_title.title) ''' + clause + '''
                      ''' + uri_clause + '''
                UNION
                SELECT * FROM (
                    SELECT work_title.work_id, work_type, uri_scheme,
                          uri_value, canonical,
                          levenshtein(lower(work_title.title), $title)
                            as score
                    FROM work_title INNER JOIN work USING(work_id)
                    INNER JOIN work_uri USING(work_id)
                    WHERE pg_column_size(title) < 255 ''' + clause + '''
                          ''' + uri_clause + ''') q
                WHERE score <= ((length($title)/3)+1)
            ) query
            ORDER BY work_id,uri_scheme, uri_value, score, canonical
        ) result ORDER BY score ASC, canonical DESC;'''
        return do_query(q, options)
