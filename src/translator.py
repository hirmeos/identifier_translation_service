import web
import urllib
from api import build_parms, result_to_identifier, results_to_identifiers, \
    logging, json_response, api_response, check_token
from errors import Error, BADPARAMS, NORESULT, NOTALLOWED, \
    AMBIGUOUS, NONCANONICAL
from models import Identifier

logger = logging.getLogger(__name__)


class Translator(object):
    """Handles translation queries"""

    @json_response
    @api_response
    @check_token
    def GET(self, name):
        """ Get a matching ID in the desired format for a given object ID.

         1. get uri or title from request
            - if uri: get scheme and path lowecased
                - if isbn: remove hyphens
         2. get parameters from filters
         3. query by URI or title
         4. iterate through results and check them
           - if single: output
           - if multiple && strict: attempt to choose fittest result
           - if multiple && !strict: output all
        """
        logger.debug("Query: %s" % (web.input()))

        uri     = web.input().get('uri') or web.input().get('URI')
        title   = web.input().get('title')
        filters = web.input().get('filter')
        strict  = web.input().get('strict') in ("true", "True")

        try:
            if uri:
                assert not title
                scheme, value = Identifier.split_uri(uri)
                assert scheme, value
            elif title:
                assert not uri
                title = urllib.unquote(title)
                assert title
            else:
                raise Exception
        except BaseException:
            raise Error(BADPARAMS, msg="Invalid URI or title provided")

        clause, params = build_parms(filters)

        if uri:
            results = Identifier.get_from_uri(scheme, value, clause, params)
        elif title:
            results = Identifier.get_from_title(title, clause, params)

        if not results:
            raise Error(NORESULT)

        return self.process_results(results, strict)

    def POST(self, name):
        raise Error(NOTALLOWED)

    def PUT(self, name):
        raise Error(NOTALLOWED)

    def DELETE(self, name):
        raise Error(NOTALLOWED)

    def process_results(self, results, strict):
        """Convert results from query to objects.

        When strict mode is set and multiple results have been obtained
        we will attempt to output the best candidate
        """
        multiple = len(results) > 1
        if not multiple:
            # process single result
            logger.debug("Success: single result...")
            return [result_to_identifier(results[0]).__dict__]
        elif multiple and not strict:
            # process multiple results in indulgent mode
            logger.debug("Success: multiple results in indulgent mode...")
            return results_to_identifiers(results)
        elif multiple and strict:
            # process multiple results in strict mode
            logger.debug("Warning: multiple results in strict mode. "
                         "Choosing best candidate...")
            return [self.choose_best_candidate(results).__dict__]

    def choose_best_candidate(self, results):
        """Attempt to return a single result from the array provided.

        We assume the first result will always be the fittest candidate, then
        we iterate the results and compare the rest with the fittest to see
        if we cannot determine a unique result, this happens when either:
          (a) more than one work_id share the lowest score;
          (b) there is no canonical among multiple URIs of the fittest result.
        """
        best = result_to_identifier(results[0])
        # IterBetter does not support slices - so we convert results to list.
        # Pointer is already be at results[1], ergo the list won't include best
        for e in list(results):
            candidate  = result_to_identifier(e)
            same_score = candidate.score == best.score
            same_work  = candidate.work == best.work
            if not same_score:
                # we already have the lowest score (results are in ASC order)
                break
            elif same_score and not same_work:
                raise Error(AMBIGUOUS, data=results_to_identifiers(results))
            elif same_score and same_work and not best.is_canonical():
                raise Error(NONCANONICAL, data=results_to_identifiers(results))
            elif same_work and best.is_canonical():
                # we continue to see wether following results correspond to a
                # different work with the same score
                continue
        return best
