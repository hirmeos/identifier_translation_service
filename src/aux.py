#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import logging
from errors import Error, BADFILTERS


def debug_mode():
    trues = ('True', 'true', True, 1)
    return 'API_DEBUG' in os.environ and os.environ['API_DEBUG'] in trues


def logger_instance(name):
    level = logging.NOTSET if debug_mode() else logging.ERROR
    logging.basicConfig(level=level)
    return logging.getLogger(name)


def strtolist(data):
    if isinstance(data, str) or isinstance(data, dict):
        return [data]
    elif isinstance(data, list):
        return data


def sort_alphabetically(data, sort, order='asc'):
    reverse = order == "desc"
    # we sort alphabetically, ignoring special characters
    return sorted(data, key=lambda x: re.sub('[^A-Za-z]+', '', x[sort][0]),
                  reverse=reverse)


def validate_sorting_or_fail(valid_sorting, sort, order):
    if sort not in valid_sorting or order not in ["asc", "desc"]:
        raise Error(BADFILTERS, msg="Unknown sort '%s' '%s'" % (sort, order))


def require_params_or_fail(parameters, msg):
    if not all(parameters):
        raise Error(BADPARAMS, msg="You must provide %s" % (msg)
