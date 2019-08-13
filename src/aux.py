#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging


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


def sort_results(results, sort, order='asc'):
    reverse = order == "desc"
    # we sort alphabetically, ignoring special characters
    return sorted(data, key=lambda x: re.sub('[^A-Za-z]+', '', x[sort][0]),
                  reverse=reverse)
