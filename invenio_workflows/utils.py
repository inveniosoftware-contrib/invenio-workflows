# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2012, 2013, 2014, 2015, 2016 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Various utility functions for use across the workflows module."""

from six import text_type, string_types

from werkzeug import import_string


def get_task_history(last_task):
    """Append last task to task history."""
    if hasattr(last_task, 'branch') and last_task.branch:
        return
    elif hasattr(last_task, 'hide') and last_task.hide:
        return
    else:
        return get_func_info(last_task)


def get_func_info(func):
    """Retrieve a function's information."""
    name = func.__name__
    doc = func.__doc__ or ""
    try:
        nicename = func.description
    except AttributeError:
        if doc:
            nicename = doc.split('\n')[0]
            if len(nicename) > 80:
                nicename = name
        else:
            nicename = name
    parameters = []
    try:
        closure = func.func_closure
    except AttributeError:
        closure = func.__closure__
    try:
        varnames = func.func_code.co_freevars
    except AttributeError:
        varnames = func.__code__.co_freevars

    if closure:
        for index, arg in enumerate(closure):
            if not callable(arg.cell_contents):
                parameters.append((varnames[index],
                                   text_type(arg.cell_contents)))
    return ({
        "nicename": nicename,
        "doc": doc,
        "parameters": parameters,
        "name": name
    })


def get_workflow_info(func_list):
    """Return function info, go through lists recursively."""
    funcs = []
    for item in func_list:
        if item is None:
            continue
        if isinstance(item, list):
            funcs.append(get_workflow_info(item))
        else:
            funcs.append(get_func_info(item))
    return funcs


def obj_or_import_string(value, default=None):
    """Import string or return object."""
    if isinstance(value, string_types):
        return import_string(value)
    elif value:
        return value
    return default
