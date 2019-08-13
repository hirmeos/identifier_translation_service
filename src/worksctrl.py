import web
from aux import (logger_instance, debug_mode, strtolist, sort_alphabetically,
                 validate_sorting_or_fail, require_params_or_fail)
from api import json, json_response, api_response, check_token, build_parms
from errors import Error, NOTALLOWED, BADPARAMS, NORESULT
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
            if sort:
                validate_sorting_or_fail(["title"], sort, order)
            results = Work.get_all(clause, params)

        if not results:
            raise Error(NORESULT)

        include_relatives = work_id is not None
        data = results_to_works(results, include_relatives)

        if sort:
            # we sort by each work's (first) title
            return sort_alphabetically(data, sort, order)
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

        titles = strtolist(title)
        uris   = strtolist(uri)
        require_params_or_fail([wtype], 'a (work) type')
        require_params_or_fail(titles, 'at least one title')
        require_params_or_fail(uris, 'at least one URI')

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

        # instantiate a new work with the input data
        uuid = Work.generate_uuid()
        work = Work(uuid, wtype, titles, uris)

        # check relatives and associate them with the work
        set_relatives(work, parent, child)

        relatives = {'parent': parent, 'child': child}
        for name, group in relatives.items():
            if group:
                elements = strtolist(group)
                for e in elements:
                    try:
                        assert Work.is_uuid(e)
                        assert Work.uuid_exists(e)
                    except AssertionError as error:
                        logger.debug(error)
                        m = "Invalid %s UUID provided." % (name)
                        raise Error(BADPARAMS, m)
                if name == 'parent':
                    work.set_parents(elements)
                else:
                    work.set_children(elements)

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

        require_params_or_fail([work_id], 'a (work) UUID')

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


def set_relatives(work, parent=[], child=[]):
    relatives = {'parent': parent, 'child': child}
    for name, group in relatives.items():
        if group:
            elements = strtolist(group)
            for e in elements:
                try:
                    assert Work.is_uuid(e)
                    assert Work.uuid_exists(e)
                except AssertionError as error:
                    logger.debug(error)
                    m = "Invalid %s UUID provided." % (name)
                    raise Error(BADPARAMS, msg=m)
            if name == 'parent':
                work.set_parents(elements)
            else:
                work.set_children(elements)
