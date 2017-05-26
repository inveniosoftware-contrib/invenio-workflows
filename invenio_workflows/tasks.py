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

"""Tasks API for invenio-workflows."""

from __future__ import absolute_import, print_function

from celery import shared_task
from six import text_type

from .errors import WorkflowsMissingData, WorkflowsMissingObject


@shared_task
def start(workflow_name, data=None, object_id=None, **kwargs):
    """Start a workflow by given name for specified data.

    The name of the workflow to start is considered unique and it is
    equal to the name of a file containing the workflow definition.

    The data passed could be a list of Python standard data types such as
    strings, dict, integers etc. to run through the workflow. Inside the
    workflow tasks, this data is then available through ``obj.data``.

    Or alternatively, pass the WorkflowObject to work on via
    ``object_id`` parameter. NOTE: This will replace any value in ``data``.

    This is also a Celery (http://celeryproject.org) task, so you can
    access the ``start.delay`` function to enqueue the execution of the
    workflow asynchronously.

    :param workflow_name: the workflow name to run. Ex: "my_workflow".
    :type workflow_name: str

    :param data: the workflow name to run. Ex: "my_workflow" (optional if
        ``object_id`` provided).
    :type data: tuple

    :param object_id: id of ``WorkflowObject`` to run (optional).
    :type object_id: int

    :return: UUID of the workflow engine that ran the workflow.
    """
    from .proxies import workflow_object_class
    from .worker_engine import run_worker

    if data is None and object_id is None:
        raise WorkflowsMissingData("No data or object_id passed to task.ß")

    if object_id is not None:
        obj = workflow_object_class.get(object_id)
        if not obj:
            raise WorkflowsMissingObject(
                "Cannot find object: {0}".format(object_id)
            )
        data = [obj]
    else:
        if not isinstance(data, (list, tuple)):
            data = [data]

    return text_type(run_worker(workflow_name, data, **kwargs).uuid)


@shared_task
def resume(oid, restart_point="continue_next", **kwargs):
    """Continue workflow for given WorkflowObject id (oid).

    Depending on `start_point` it may start from previous, current or
    next task.

    Special custom keyword arguments can be given to the workflow engine
    in order to pass certain variables to the tasks in the workflow execution,
    such as a task-id from BibSched, the current user etc.

    :param oid: id of WorkflowObject to run.
    :type oid: str

    :param start_point: where should the workflow start from? One of:
        * restart_prev: will restart from the previous task
        * continue_next: will continue to the next task
        * restart_task: will restart the current task
    :type start_point: str

    :return: UUID of the workflow engine that ran the workflow.
    """
    from .worker_engine import continue_worker
    return text_type(continue_worker(oid, restart_point, **kwargs).uuid)


@shared_task
def restart(uuid, **kwargs):
    """Restart the workflow from a given workflow engine UUID."""
    from .worker_engine import restart_worker
    return text_type(restart_worker(uuid, **kwargs).uuid)
