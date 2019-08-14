import web
import psycopg2
from aux import logger_instance, debug_mode
from api import db
from errors import Error, FATAL

logger = logger_instance(__name__)
web.config.debug = debug_mode()


def results_to_identifiers(results):
    return [(result_to_identifier(e).__dict__) for e in results]


def result_to_identifier(r):
    from .identifier import Identifier
    return Identifier(r["uri_scheme"], r["uri_value"], r["canonical"],
                      r["score"] if "score" in r else 0,
                      r["work_id"] if "work_id" in r else None,
                      r["work_type"] if "work_type" in r else None)


def result_to_work(r):
    from .work import Work
    work = Work(r["work_id"], r["work_type"] if "work_type" in r else None,
                r["titles"] if "titles" in r else [])
    return work


def results_to_titles(results):
    return [(result_to_title(e).__dict__) for e in results]


def result_to_title(r):
    from .title import Title
    return Title(r["title"])


def results_to_work_types(results):
    return [(result_to_work_type(e).__dict__) for e in results]


def result_to_work_type(r):
    from .worktype import WorkType
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

    for i, e in enumerate(results):
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
    try:
        cur["titles"] = titles
        cur["URI"] = uris_fmt
        work = result_to_work(cur)
        work.URI = results_to_identifiers(cur["URI"])
        if include_relatives:
            work.load_children()
            work.load_parents()
        data.append(work.__dict__)
    except NameError:
        # we need to run the above with the last element of IterBetter, if it
        # fails it means that no results were iterated
        pass
    return data


def do_query(query, params):
    try:
        return db.query(query, params)
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(error)
        raise Error(FATAL)
