import re
import web
from aux import logger_instance, debug_mode, strtolist
from api import json, json_response, api_response, check_token, build_parms
from errors import Error, NOTALLOWED, BADPARAMS, BADFILTERS, NORESULT
from models import Work, WorkType, Identifier, UriScheme, results_to_works

logger = logger_instance(__name__)
web.config.debug = debug_mode()


class WorksController(object):
    """Handles work related actions"""

    @json_response
    @api_response
    @check_token
    def GET(self, name):
        """List a work if UUID provided otherwise list all works"""
        logger.debug("Query: %s" % (web.input()))

        work_id = web.input().get('uuid') or web.input().get('UUID')

        if work_id:
            results = Work.get_from_work_id(work_id)
            sort = ""
        else:
            filters = web.input().get('filter')
            sort = web.input().get('sort')
            order = web.input().get('order', 'asc')
            clause, params = build_parms(filters)
            try:
                if sort:
                    assert sort in ["title"]
                    assert order in ["asc", "desc"]
            except AssertionError:
                raise Error(BADFILTERS,
                            msg="Unknown sort '%s' '%s'" % (sort, order))
            results = Work.get_all(clause, params)

        if not results:
            raise Error(NORESULT)

        include_relatives = work_id is not None
        data = results_to_works(results, include_relatives)

        if sort:
            reverse = order == "desc"
            # we sort by each work's (first) title, ignoring special chars
            return sorted(data,
                          key=lambda x: re.sub('[^A-Za-z]+', '', x[sort][0]),
                          reverse=reverse)
        return data

    @json_response
    @api_response
    @check_token
    def POST(self, name):
        """Create a work"""
        logger.debug("Data: %s" % (web.data().decode('utf-8')))

        data   = json.loads(web.data().decode('utf-8'))
        wtype  = data.get('type')
        title  = data.get('title')
        uri    = data.get('URI') or data.get('uri')
        parent = data.get('parent')
        child  = data.get('child')

        try:
            titles = strtolist(title)
            uris   = strtolist(uri)
            assert wtype and titles and uris
        except AssertionError as error:
            logger.debug(error)
            raise Error(BADPARAMS, msg="You must provide a (work) type"
                        ", a title, and at least one URI")

        try:
            assert WorkType(wtype).exists()
        except AssertionError:
            t = wtype if isinstance(wtype, str) else ""
            raise Error(BADPARAMS, msg="Unknown work type '%s'" % (t))

        for i in uris:
            # attempt to get scheme from URI
            try:
                ident = i.get('URI') or i.get('uri')
                scheme, value = Identifier.split_uri(ident)
                try:
                    i['canonical'] = i['canonical'] in (True, "true", "True")
                except Exception:
                    i['canonical'] = False
            except Exception:
                identifier = ident if ident else ''
                raise Error(BADPARAMS, msg="Invalid URI '%s'" % (identifier))

            # check whether the URI scheme exists in the database
            try:
                assert UriScheme(scheme).exists()
            except AssertionError:
                raise Error(BADPARAMS,
                            msg="Unknown URI scheme '%s'" % (scheme))

        uuid = Work.generate_uuid()
        work = Work(uuid, wtype, titles, uris)

        if parent:
            parents = strtolist(parent)
            for p in parents:
                try:
                    assert Work.is_uuid(p)
                    assert Work.uuid_exists(p)
                except AssertionError as error:
                    logger.debug(error)
                    raise Error(BADPARAMS, msg="Invalid parent UUID provided.")
            work.set_parents(parents)

        if child:
            children = strtolist(child)
            for c in children:
                try:
                    assert Work.is_uuid(c)
                    assert Work.uuid_exists(c)
                except AssertionError as error:
                    logger.debug(error)
                    raise Error(BADPARAMS, msg="Invalid child UUID provided.")
            work.set_children(children)

        work.save()

        return [work.__dict__]

    @json_response
    @api_response
    @check_token
    def PUT(self, name):
        """Update a work"""
        raise Error(NOTALLOWED)

    @json_response
    @api_response
    @check_token
    def DELETE(self, name):
        """Delete a work"""
        logger.debug("Data: %s" % (web.input()))

        work_id = web.input().get('UUID') or web.input().get('uuid')

        try:
            if not work_id:
                raise AssertionError
        except AssertionError as error:
            logger.debug(error)
            raise Error(BADPARAMS, msg="You must provide a (work) UUID")

        try:
            work = Work(work_id)
            if not work.exists():
                raise AssertionError
        except AssertionError:
            raise Error(BADPARAMS, msg="Unknown work '%s'" % (work_id))

        work.delete()
        return []

    @json_response
    def OPTIONS(self, name):
        return
