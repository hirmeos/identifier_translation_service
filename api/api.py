#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Identifier Translator JSON API prototype. Simple web.py based API to a PostgreSQL database that runs on port 8080.

usage: python api.py

(c) Javier Arias, Open Book Publishers, March 2018
Use of this software is governed by the terms of the MIT license

Dependencies:
  pbkdf2==1.3
  PyJWT==1.6.1
  psycopg2==2.6.1
  uri==2.0.0
  urllib3==1.20
  web.py==0.38
"""

import os
import web
import sys
import json
import logging
from errors import *

# Determine logging level
debug = os.environ['API_DEBUG'] == 'True'
level = logging.NOTSET if debug else logging.ERROR
logging.basicConfig(level=level)
logger = logging.getLogger(__name__)

# Get authentication configuration
SECRET_KEY = os.environ['SECRET_KEY']
TOKEN_LIFETIME = int(os.environ['TOKEN_LIFETIME'])
PBKDF2_ITERATIONS = int(os.environ['PBKDF2_ITERATIONS'])

# Define routes
urls = (
    "/translate(/?)", "translator.Translator",
    "/works(/?)", "worksctrl.WorksController",
    "/auth(/?)", "authctrl.AuthController",
    "(.*)", "NotFound",
)

try:
    db = web.database(dbn='postgres',
                      host=os.environ['IDENTIFIERSDB_HOST'],
                      user=os.environ['IDENTIFIERSDB_USER'],
                      pw=os.environ['IDENTIFIERSDB_PASS'],
                      db=os.environ['IDENTIFIERSDB_DB'])
    authdb = web.database(dbn='postgres',
                          host=os.environ['AUTHDB_HOST'],
                          user=os.environ['AUTHDB_USER'],
                          pw=os.environ['AUTHDB_PASS'],
                          db=os.environ['AUTHDB_DB'])
except Exception as error:
    logger.error(error)
    raise Error(FATAL)

def api_response(fn):
    """Decorator to provided consistency in all responses"""
    def response(self, *args, **kw):
        data  = fn(self, *args, **kw)
        count = len(data)
        if count > 0:
            return {'status': 'ok', 'count': count, 'data': data}
        else:
            raise Error(NORESULT)
    return response

def json_response(fn):
    """JSON decorator"""
    def response(self, *args, **kw):
        web.header('Content-Type', 'application/json;charset=UTF-8')
        return json.dumps(fn(self, *args, **kw), ensure_ascii=False)
    return response

def check_token(fn):
    """Decorator to act as middleware, checking authentication token"""
    def response(self, *args, **kw):
        intoken = get_token_from_header()
        token = Token(intoken)
        token.validate()
        return fn(self, *args, **kw)
    return response

def get_token_from_header():
    bearer = web.ctx.env.get('HTTP_AUTHORIZATION')
    return bearer.replace("Bearer ", "") if bearer else ""

def build_parms(filters):
    if not filters:
        return "", {}
    params  = filters.split(',')
    options = {}
    types   = []
    schemes = []
    clause  = ""
    for p in params:
        try:
            field, val = p.split(':', 1)
            if field == "work_type":
                types.append(val)
            elif field == "uri_scheme":
                schemes.append(val)
            else:
                raise Error(BADFILTERS)
        except:
            raise Error(BADFILTERS, msg = "Unknown filter '%s'" % (p))

    process = {"work_type": types, "uri_scheme": schemes}
    for key, values in process.items():
        if len(values) > 0:
            try:
                andclause, ops = build_clause(key, values)
                options.update(ops)
                clause = clause + andclause
            except:
                raise Error(BADFILTERS)

    return clause, options

def build_clause(attribute, values):
    params = {}
    clause = " AND " + attribute + " IN ("
    no = 1
    for v in values:
        params[attribute+str(no)] = v
        if no > 1:
            clause += ","
        clause += "$"+attribute+str(no)
        no += 1
    return [clause + ")", params]

def results_to_identifiers(results):
    data = []
    for e in results:
        data.append(result_to_identifier(e).__dict__)
    return data

def result_to_identifier(r):
    return Identifier(r["uri_scheme"], r["uri_value"], r["canonical"],
                      r["score"] if "score" in r else 0,
                      r["work_id"] if "work_id" in r else None,
                      r["work_type"] if "work_type" in r else None)

def results_to_works(results):
    """Iterate the results to get distinct works with associated identifiers.

    Without this method we would need to query the list of work_ids, then
    their titles and uris - iterating the full data set, filtering as needed,
    is a lot faster.
    """
    data     = [] # output
    titles   = [] # temporary array of work titles
    uris     = [] # temporary array of work URIs (strings, used for comparison)
    uris_fmt = [] # temporary array of work URIs (Identifier objects)
    last     = len(results)-1

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
            data.append(work.__dict__)
        i+=1
    return data

def result_to_work(r):
    work = Work(r["work_id"], r["work_type"] if "work_type" in r else None,
                r["titles"] if "titles" in r else [])
    return work

import translator
import worksctrl
import authctrl
from models import Identifier, Work, Token

if __name__ == "__main__":
    logger.info("Starting API...")
    app = web.application(urls, globals())
    web.config.debug = debug
    app.run()
