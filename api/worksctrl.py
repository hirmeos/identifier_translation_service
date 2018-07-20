import re
import web
import urllib
from api import *
from errors import *
from models import Work, WorkType, Identifier, UriScheme

logger = logging.getLogger(__name__)

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
            except:
                raise Error(BADFILTERS,
                            msg = "Unknown sort '%s' '%s'" % (sort, order))
            results = Work.get_all(clause, params)

        if not results:
            raise Error(NORESULT)
        data = results_to_works(results)

        if sort:
            reverse = order == "desc"
            # we sort by each work's (first) title, ignoring special chars
            return sorted(data,
                  key=lambda x: re.sub('[^A-Za-z0-9]+', '', x[sort][0]),
                  reverse=reverse)
        return data

    @json_response
    @api_response
    @check_token
    def POST(self, name):
        """Create a work"""
        logger.debug("Data: %s" % (web.data()))

        data   = json.loads(web.data())
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
                                        + ", a title, and at least one URI")

        try:
            assert WorkType(wtype).exists()
        except:
            raise Error(BADPARAMS, msg="Unknown work type '%s'" % (wtype))

        for i in uris:
            # attempt to get scheme from URI
            try:
                ident = i['URI'] or i['uri']
                scheme, value = Identifier.split_uri(ident)
            except:
                raise Error(BADPARAMS, msg="Invalid URI '%s'" % (ident))

            # check whether the URI scheme exists in the database
            try:
                assert UriScheme(scheme).exists()
            except:
                raise Error(BADPARAMS, msg="Unknown URI scheme '%s'" % (scheme))

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
            work.parent = parents

        if child:
            children = strtolist(child)
            for c in children:
                try:
                    assert Work.is_uuid(c)
                    assert Work.uuid_exists(c)
                except AssertionError as error:
                    logger.debug(error)
                    raise Error(BADPARAMS, msg="Invalid child UUID provided.")
            work.child = children

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
        raise Error(NOTALLOWED)

