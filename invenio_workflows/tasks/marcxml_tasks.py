# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2013, 2014, 2015 CERN.
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

"""Set of function for harvesting."""

import glob
import os
import traceback

from functools import wraps

from six import callable


def approve_record(obj, eng):
    """Will add the approval widget to the record.

    The workflow need to be halted to use the
    action in the holdingpen.
    :param obj: Bibworkflow Object to process
    :param eng: BibWorkflowEngine processing the object
    """
    try:
        eng.halt(action="approval",
                 msg='Record needs approval')
    except KeyError:
        # Log the error
        obj.extra_data["_error_msg"] = 'Could not assign action'


def was_approved(obj, eng):
    """Check if the record was approved."""
    extra_data = obj.get_extra_data()
    return extra_data.get("approved", False)


def convert_record_to_bibfield(model=None):
    """Convert to record from MARCXML.

    Expecting MARCXML, this task converts it using the current configuration to a
    SmartJSON object.

    :param obj: Bibworkflow Object to process
    :param eng: BibWorkflowEngine processing the object
    """
    @wraps(convert_record_to_bibfield)
    def _convert_record_to_bibfield(obj, eng):
        from invenio_workflows.utils import convert_marcxml_to_bibfield
        obj.data = convert_marcxml_to_bibfield(obj.data, model)
        eng.log.info("Field conversion succeeded")
    return _convert_record_to_bibfield


def get_files_list(path, parameter):
    """Function returning the list of file in a directory."""
    @wraps(get_files_list)
    def _get_files_list(obj, eng):
        if callable(parameter):
            unknown = parameter
            while callable(unknown):
                unknown = unknown(obj, eng)

        else:
            unknown = parameter
        result = glob.glob1(path, unknown)
        for i in range(0, len(result)):
            result[i] = path + os.sep + result[i]
        return result

    return _get_files_list


def set_obj_extra_data_key(key, value):
    """Task setting the value of an object extra data key."""
    @wraps(set_obj_extra_data_key)
    def _set_obj_extra_data_key(obj, eng):
        my_value = value
        my_key = key
        if callable(my_value):
            while callable(my_value):
                my_value = my_value(obj, eng)
        if callable(my_key):
            while callable(my_key):
                my_key = my_key(obj, eng)
        obj.extra_data[str(my_key)] = my_value

    return _set_obj_extra_data_key


def get_obj_extra_data_key(name):
    """Task returning the value of an object extra data key."""
    @wraps(get_obj_extra_data_key)
    def _get_obj_extra_data_key(obj, eng):
        return obj.extra_data[name]

    return _get_obj_extra_data_key


def get_eng_extra_data_key(name):
    """Task returning the value of an engine extra data key."""
    @wraps(get_eng_extra_data_key)
    def _get_eng_extra_data_key(obj, eng):
        return eng.extra_data[name]

    return _get_eng_extra_data_key


def get_data(obj, eng):
    """Task returning data of the object."""
    return obj.data


def convert_record(stylesheet="oaidc2marcxml.xsl"):
    """Convert the object data to marcxml using the given stylesheet.

    :param stylesheet: which stylesheet to use
    :return: function to convert record
    :raise WorkflowError:
    """
    @wraps(convert_record)
    def _convert_record(obj, eng):
        from invenio_workflows.errors import WorkflowError
        from invenio.legacy.bibconvert.xslt_engine import convert

        eng.log.info("Starting conversion using %s stylesheet" %
                     (stylesheet,))

        if not obj.data:
            obj.log.error("Not valid conversion data!")
            raise WorkflowError("Error: conversion data missing",
                                id_workflow=eng.uuid,
                                id_object=obj.id)

        try:
            obj.data = convert(obj.data, stylesheet)
        except Exception as e:
            msg = "Could not convert record: %s\n%s" % \
                  (str(e), traceback.format_exc())
            raise WorkflowError("Error: %s" % (msg,),
                                id_workflow=eng.uuid,
                                id_object=obj.id)

    _convert_record.description = 'Convert record'
    return _convert_record
