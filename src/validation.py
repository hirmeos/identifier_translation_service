#!/usr/bin/env python
# -*- coding: utf-8 -*-

from errors import Error, BADFILTERS, BADPARAMS


def validate_sorting_or_fail(valid_sorting, sort, order):
    if sort not in valid_sorting or order not in ["asc", "desc"]:
        raise Error(BADFILTERS, msg="Unknown sort '%s' '%s'" % (sort, order))


def require_params_or_fail(parameters, msg):
    if not all(parameters):
        raise Error(BADPARAMS, msg="You must provide %s" % (msg))
