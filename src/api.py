#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Identifier Translator JSON API. Simple web.py based API to a
PostgreSQL database that runs on port 8080.

usage: python api.py

(c) Javier Arias, Open Book Publishers, March 2018
Use of this software is governed by the terms of the MIT license

Dependencies:
  pbkdf2==1.3
  PyJWT==1.6.1
  psycopg2-binary==2.7.5
  uri==2.0.0
  urllib3==1.24.2
  web.py==0.39
"""

import re
import os
import web
import jwt
import json
from aux import logger_instance, debug_mode
from errors import (Error, NotFound, InternalError, NoMethod, Unauthorized,
                    Forbidden, NORESULT, BADFILTERS, UNAUTHORIZED,
                    FORBIDDEN, FATAL)

# get logging interface
logger = logger_instance(__name__)
web.config.debug = debug_mode()

# You may disable JWT auth. when implementing the API in a local network
JWT_DISABLED = os.getenv('JWT_DISABLED', 'false').lower() == 'true'
# Get secret key to check JWT
SECRET_KEY = os.getenv('SECRET_KEY')
if not JWT_DISABLED and not SECRET_KEY:
    logger.error("API authentication is not configured. "
                 "You must set JWT_DISABLED or SECRET_KEY")
    raise Error(FATAL)

# Define routes
urls = (
    "/translate(/?)", "translator.Translator",
    "/works(/?)", "worksctrl.WorksController",
    "/titles(/?)", "titlesctrl.TitlesController",
    "/uris(/?)", "urisctrl.UrisController",
    "/work_types(/?)", "typesctrl.TypesController",
    "/work_relations(/?)", "relationsctrl.RelationsController"
)

try:
    db = web.database(dbn='postgres',
                      host=os.environ['IDENTIFIERSDB_HOST'],
                      user=os.environ['IDENTIFIERSDB_USER'],
                      pw=os.environ['IDENTIFIERSDB_PASS'],
                      db=os.environ['IDENTIFIERSDB_DB'])
except Exception as error:
    logger.error(error)
    raise


def api_response(fn):
    """Decorator to provided consistency in all responses"""
    def response(self, *args, **kw):
        data  = fn(self, *args, **kw)
        count = len(data)
        if count > 0:
            return {'status': 'ok', 'code': 200, 'count': count, 'data': data}
        else:
            raise Error(NORESULT)
    return response


def json_response(fn):
    """JSON decorator"""
    def response(self, *args, **kw):
        web.header('Content-Type', 'application/json;charset=UTF-8')
        web.header('Access-Control-Allow-Origin',
                   '"'.join([os.environ['ALLOW_ORIGIN']]))
        web.header('Access-Control-Allow-Credentials', 'true')
        web.header('Access-Control-Allow-Headers',
                   'Authorization, x-test-header, Origin, '
                   'X-Requested-With, Content-Type, Accept')
        return json.dumps(fn(self, *args, **kw), ensure_ascii=False)
    return response


def check_token(fn):
    """Decorator to act as middleware, checking authentication token"""
    def response(self, *args, **kw):
        if not JWT_DISABLED:
            intoken = get_token_from_header()
            try:
                jwt.decode(intoken, SECRET_KEY)
            except jwt.exceptions.DecodeError:
                raise Error(FORBIDDEN)
            except jwt.ExpiredSignatureError:
                raise Error(UNAUTHORIZED, msg="Signature expired.")
            except jwt.InvalidTokenError:
                raise Error(UNAUTHORIZED, msg="Invalid token.")
        return fn(self, *args, **kw)
    return response


def get_token_from_header():
    bearer = web.ctx.env.get('HTTP_AUTHORIZATION')
    return bearer.replace("Bearer ", "") if bearer else ""


def build_parms(filters):
    if not filters:
        return "", {}
    # split by ',' except those preceeded by a top level domain, which will
    # be a tag URI scheme (e.g. tag:openbookpublishers.com,2009)
    params  = re.split(r"(?<!\.[a-z]{3}),", filters)
    options = {}
    types   = []
    schemes = []
    canoncl = []
    clause  = ""
    for p in params:
        try:
            field, val = p.split(':', 1)
            if field == "work_type":
                types.append(val)
            elif field == "uri_scheme":
                schemes.append(val)
            elif field == "canonical":
                canoncl.append(val in (True, "true", "True"))
            else:
                raise Error(BADFILTERS)
        except BaseException:
            raise Error(BADFILTERS, msg="Unknown filter '%s'" % (p))

    process = {"work_type": types, "uri_scheme": schemes, "canonical": canoncl}
    for key, values in list(process.items()):
        if len(values) > 0:
            try:
                andclause, ops = build_clause(key, values)
                options.update(ops)
                clause = clause + andclause
            except BaseException:
                raise Error(BADFILTERS)

    return clause, options


def build_clause(attribute, values):
    params = {}
    clause = " AND " + attribute + " IN ("
    no = 1
    for v in values:
        params[attribute + str(no)] = v
        if no > 1:
            clause += ","
        clause += "$" + attribute + str(no)
        no += 1
    return [clause + ")", params]


if __name__ == "__main__":
    logger.info("Starting API...")
    app = web.application(urls, globals())
    app.internalerror = InternalError
    app.notfound = NotFound
    app.nomethod = NoMethod
    app.unauthorized = Unauthorized
    app.forbidden = Forbidden
    app.run()
