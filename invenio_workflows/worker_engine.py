# -*- coding: utf-8 -*-
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

"""Mediator between API and workers responsible for running the workflows."""

from invenio_db import db

from .engine import WorkflowEngine
from .models import Workflow
from .proxies import workflow_object_class


def run_worker(wname, data, **kwargs):
    """Run a workflow by name with list of data objects.

    The list of data can also contain WorkflowObjects.

    ``**kwargs`` can be used to pass custom arguments to the engine/object.

    :param wname: name of workflow to run.
    :type wname: str

    :param data: objects to run through the workflow.
    :type data: list

    :return: WorkflowEngine instance
    """
    if 'stop_on_halt' not in kwargs:
        kwargs['stop_on_halt'] = False

    engine = WorkflowEngine.with_name(wname, **kwargs)
    engine.save()
    objects = get_workflow_object_instances(data, engine)

    db.session.commit()

    engine.process(objects, **kwargs)
    return engine


def restart_worker(uuid, **kwargs):
    """Restart workflow from beginning with given engine UUID and any data.

    ``**kwargs`` can be used to pass custom arguments to the engine/object such
    as ``data``. If ``data`` is not specified then it will load all
    initial data for the data objects.

    Data can be specified as list of objects or single id of
    WorkflowObjects.

    :param uuid: workflow id (uuid) of the ``WorkflowEngine`` to be restarted
    :type uuid: str

    :return: ``WorkflowEngine`` instance
    """
    if 'stop_on_halt' not in kwargs:
        kwargs['stop_on_halt'] = False

    engine = WorkflowEngine.from_uuid(uuid=uuid, **kwargs)

    if "data" not in kwargs:
        objects = workflow_object_class.query(id_workflow=uuid)
    else:
        data = kwargs.pop("data")
        if not isinstance(data, (list, tuple)):
            data = [data]
        objects = get_workflow_object_instances(data, engine)

    db.session.commit()
    engine.process(objects, **kwargs)
    return engine


def continue_worker(oid, restart_point="continue_next", **kwargs):
    """Restart workflow with given id (uuid) at given point.

    By providing the ``restart_point`` you can change the
    point of which the workflow will continue from.

    * restart_prev: will restart from the previous task
    * continue_next: will continue to the next task (default)
    * restart_task: will restart the current task

    ``**kwargs`` can be used to pass custom arguments to the engine/object.

    :param oid: object id of the object to process
    :type oid: int

    :param restart_point: point to continue from
    :type restart_point: str

    :return: WorkflowEngine instance
    """
    if 'stop_on_halt' not in kwargs:
        kwargs['stop_on_halt'] = False

    workflow_object = workflow_object_class.get(oid)
    workflow = Workflow.query.get(workflow_object.id_workflow)

    engine = WorkflowEngine(workflow, **kwargs)
    engine.save()

    db.session.commit()
    engine.continue_object(
        workflow_object,
        restart_point=restart_point,
        **kwargs
    )
    return engine


def get_workflow_object_instances(data, engine):
    """Analyze data and create corresponding WorkflowObjects.

    Wrap each item in the given list of data objects into WorkflowObject
    instances - creating appropriate status of objects in the database and
    returning a list of these objects.

    This process is necessary to save an initial status of the data before
    running it (and potentially changing it) in the workflow.

    This function also takes into account if given data objects are already
    WorkflowObject instances.

    :param data: list of data objects to wrap
    :type data: list

    :param engine: instance of WorkflowEngine
    :type engine: py:class:`.engine.WorkflowEngine`

    :return: list of WorkflowObject
    """
    workflow_objects = []
    data_type = engine.get_default_data_type()

    for data_object in data:
        if isinstance(
            data_object, workflow_object_class._get_current_object()
        ):
            data_object.data_type = data_type

            if data_object.id:
                data_object.log.debug("Existing workflow object found for "
                                      "this object.")
                if data_object.status == data_object.known_statuses.COMPLETED:
                    data_object.status = data_object.known_statuses.INITIAL

            workflow_objects.append(data_object)
        else:
            # Data is not already a WorkflowObject, we then
            # add the running object to run through the workflow.
            current_obj = create_data_object_from_data(
                data_object,
                engine,
                data_type
            )
            workflow_objects.append(current_obj)

    return workflow_objects


def create_data_object_from_data(data_object, engine, data_type):
    """Create a new WorkflowObject from given data and return it.

    Returns a data object wrapped around data_object given.

    :param data_object: object containing the data
    :type data_object: object

    :param engine: Instance of Workflow that is currently running.
    :type engine: py:class:`.engine.WorkflowEngine`

    :param data_type: type of the data given as taken from workflow definition.
    :type data_type: str

    :returns: new WorkflowObject
    """
    # Data is not already a WorkflowObject, we first
    # create an initial object for each data object.
    return workflow_object_class.create(
        data=data_object,
        id_workflow=engine.uuid,
        status=workflow_object_class.known_statuses.INITIAL,
        data_type=data_type,
    )
