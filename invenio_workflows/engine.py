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

"""The workflow engine extension of `workflow.DbWorkflowEngine`."""

from __future__ import absolute_import

import traceback

from datetime import datetime
from uuid import uuid1 as new_uuid

from flask import current_app
from invenio_db import db
from sqlalchemy.orm.attributes import flag_modified
from workflow.engine import ActionMapper, Break, Continue, ProcessingFactory, \
    TransitionActions
from workflow.engine import GenericWorkflowEngine
from workflow.engine_db import WorkflowStatus
from workflow.errors import WorkflowDefinitionError
from workflow.utils import staticproperty, classproperty

from .proxies import workflow_object_class
from .errors import WaitProcessing, WorkflowsMissingModel
from .models import ObjectStatus, Workflow, WorkflowObjectModel
from .utils import get_task_history


class WorkflowEngine(GenericWorkflowEngine):
    """Special engine for Invenio."""

    def __init__(self, model=None, name=None, id_user=None, **extra_data):
        """Handle special case of instantiation of engine."""
        # Super's __init__ clears extra_data, which we override to be
        # model.extra_data. We work around this by temporarily storing it
        # elsewhere.
        if not model:
            model = Workflow(
                name=name,
                id_user=id_user,
                uuid=new_uuid()
            )
            model.save(WorkflowStatus.NEW)
        self.model = model
        super(WorkflowEngine, self).__init__()
        self.set_workflow_by_name(self.model.name)

    @classmethod
    def with_name(cls, name, id_user=0, **extra_data):
        """Instantiate a WorkflowEngine given a name or UUID.

        :param name: name of workflow to run.
        :type name: str

        :param id_user: id of user to associate with workflow
        :type id_user: int

        :param module_name: label used to query groups of workflows.
        :type module_name: str
        """
        return cls(name=name, id_user=0, **extra_data)

    @classmethod
    def from_uuid(cls, uuid, **extra_data):
        """Load an existing workflow from the database given a UUID.

        :param uuid: pass a uuid to an existing workflow.
        :type uuid: str
        """
        model = Workflow.query.get(uuid)
        if model is None:
            raise LookupError(
                "No workflow with UUID {} was found".format(uuid)
            )
        instance = cls(model=model, **extra_data)
        instance.objects = WorkflowObjectModel.query.filter(
            WorkflowObjectModel.id_workflow == uuid,
            WorkflowObjectModel.id_parent == None,  # noqa
        ).all()
        return instance

    @property
    def db(self):
        """Return SQLAlchemy db."""
        return db

    @property
    def processed_objects(self):
        """Return SQLAlchemy db."""
        return [workflow_object_class(obj) for obj in self.objects]

    @staticproperty
    def object_status():  # pylint: disable=no-method-argument
        """Return ObjectStatus type."""
        return ObjectStatus

    @classproperty
    def known_statuses(cls):
        """Return WorkflowStatus type."""
        return WorkflowStatus

    @staticproperty
    def processing_factory():  # pylint: disable=no-method-argument
        """Provide a proccessing factory."""
        return InvenioProcessingFactory

    @property
    def uuid(self):
        """Return the uuid."""
        return self.model.uuid

    @property
    def name(self):
        """Return the name."""
        return self.model.name

    @property
    def status(self):
        """Return the status."""
        return self.model.status

    @property
    def id_user(self):
        """Return the user id."""
        return self.model.id_user

    @property
    def database_objects(self):
        """Return the objects associated with this workflow."""
        return self.model.objects

    @property
    def final_objects(self):
        """Return the objects associated with this workflow."""
        return [obj for obj in self.database_objects
                if obj.status in [obj.known_statuses.COMPLETED]]

    @property
    def halted_objects(self):
        """Return the objects associated with this workflow."""
        return [obj for obj in self.database_objects
                if obj.status in [obj.known_statuses.HALTED]]

    @property
    def running_objects(self):
        """Return the objects associated with this workflow."""
        return [obj for obj in self.database_objects
                if obj.status in [obj.known_statuses.RUNNING]]

    def save(self, status=None):
        """Save object to persistent storage."""
        if self.model is None:
            raise WorkflowsMissingModel()

        with db.session.begin_nested():
            self.model.modified = datetime.now()
            if status is not None:
                self.model.status = status

            if self.model.extra_data is None:
                self.model.extra_data = dict()
            flag_modified(self.model, 'extra_data')
            db.session.merge(self.model)

    def wait(self, msg=""):
        """Halt the workflow (stop also any parent `wfe`).

        Halts the currently running workflow by raising WaitProcessing.

        :param msg: message explaining the reason for halting.
        :type msg: str

        :raises: WaitProcessing
        """
        raise WaitProcessing(message=msg)

    def continue_object(self, workflow_object, restart_point='restart_task',
                        task_offset=1, stop_on_halt=False):
        """Continue workflow for one given object from "restart_point".

        :param object:
        :param stop_on_halt:
        :param restart_point: can be one of:
            * restart_prev: will restart from the previous task
            * continue_next: will continue to the next task
            * restart_task: will restart the current task

        You can use stop_on_error to raise exception's and stop the processing.
        Use stop_on_halt to stop processing the workflow if HaltProcessing is
        raised.
        """
        translate = {
            'restart_task': 'current',
            'continue_next': 'next',
            'restart_prev': 'prev',
        }
        self.state.callback_pos = workflow_object.callback_pos or [0]
        self.restart(task=translate[restart_point], obj='first',
                     objects=[workflow_object], stop_on_halt=stop_on_halt)

    def init_logger(self):
        """Return the appropriate logger instance."""
        return current_app.logger

    @property
    def has_completed(self):
        """Return True if workflow is fully completed."""
        objects_in_db = WorkflowObjectModel.query.filter(
            WorkflowObjectModel.id_workflow == self.uuid,
            WorkflowObjectModel.id_parent == None,  # noqa
        ).filter(WorkflowObjectModel.status.in_([
            workflow_object_class.known_statuses.COMPLETED
        ])).count()
        return objects_in_db == len(list(self.objects))

    def set_workflow_by_name(self, workflow_name):
        """Configure the workflow to run by the name of this one.

        Allows the modification of the workflow that the engine will run
        by looking in the registry the name passed in parameter.

        :param workflow_name: name of the workflow.
        :type workflow_name: str
        """
        from .proxies import workflows

        if workflow_name not in workflows:
            # No workflow with that name exists
            raise WorkflowDefinitionError("Workflow '%s' does not exist"
                                          % (workflow_name,),
                                          workflow_name=workflow_name)
        self.workflow_definition = workflows[workflow_name]
        self.callbacks.replace(self.workflow_definition.workflow)

    def get_default_data_type(self):
        """Return default data type from workflow definition."""
        return getattr(self.workflow_definition, "data_type", "")

    def reset_extra_data(self):
        """Reset extra data to defaults."""
        self.model.extra_data = {}

    def __repr__(self):
        """Allow to represent the WorkflowEngine."""
        return "<WorkflowEngine (name={0}, status={1})>".format(
            self.name, self.status
        )


class InvenioActionMapper(ActionMapper):
    """Map workflow engine callbacks to functions."""

    @staticmethod
    def before_each_callback(eng, callback_func, obj):
        """Take action before every WF callback."""
        eng.log.info("Executing callback %s" % (repr(callback_func),))

    @staticmethod
    def after_each_callback(eng, callback_func, obj):
        """Take action after every WF callback."""
        obj.callback_pos = eng.state.callback_pos
        obj.extra_data["_last_task_name"] = callback_func.__name__
        task_history = get_task_history(callback_func)
        if "_task_history" not in obj.extra_data:
            obj.extra_data["_task_history"] = [task_history]
        else:
            obj.extra_data["_task_history"].append(task_history)


class InvenioProcessingFactory(ProcessingFactory):
    """Map workflow processing callbacks to functions."""

    @staticproperty
    def transition_exception_mapper():  # pylint: disable=no-method-argument
        """Define our for handling transition exceptions."""
        return InvenioTransitionAction

    @staticproperty
    def action_mapper():  # pylint: disable=no-method-argument
        """Set a mapper for actions while processing."""
        return InvenioActionMapper

    @staticmethod
    def before_object(eng, objects, obj):
        """Take action before the processing of an object begins."""
        super(InvenioProcessingFactory, InvenioProcessingFactory)\
            .before_object(
            eng, objects, obj
        )
        if "_error_msg" in obj.extra_data:
            del obj.extra_data["_error_msg"]
        db.session.commit()

    @staticmethod
    def after_object(eng, objects, obj):
        """Take action once the proccessing of an object completes."""
        # We save each object once it is fully run through
        super(InvenioProcessingFactory, InvenioProcessingFactory)\
            .after_object(eng, objects, obj)
        obj.save(
            status=obj.known_statuses.COMPLETED,
            id_workflow=eng.model.uuid
        )
        db.session.commit()

    @staticmethod
    def before_processing(eng, objects):
        """Execute before processing the workflow."""
        super(InvenioProcessingFactory, InvenioProcessingFactory)\
            .before_processing(eng, objects)
        eng.save(WorkflowStatus.RUNNING)
        db.session.commit()

    @staticmethod
    def after_processing(eng, objects):
        """Process to update status."""
        super(InvenioProcessingFactory, InvenioProcessingFactory)\
            .after_processing(eng, objects)
        if eng.has_completed:
            eng.save(WorkflowStatus.COMPLETED)
        else:
            eng.save(WorkflowStatus.HALTED)
        db.session.commit()


class InvenioTransitionAction(TransitionActions):
    """Map workflow processing exception handlers to functions."""

    @staticmethod
    def Exception(obj, eng, callbacks, exc_info):
        """Handle general exceptions in workflow, saving states."""
        exception_repr = ''.join(traceback.format_exception(*exc_info))
        msg = "Error:\n%s" % (exception_repr)
        eng.log.error(msg)
        if obj:
            # Sets an error message as a tuple (title, details)
            obj.extra_data['_error_msg'] = exception_repr
            obj.save(
                status=obj.known_statuses.ERROR,
                callback_pos=eng.state.callback_pos,
                id_workflow=eng.uuid
            )
        eng.save(WorkflowStatus.ERROR)
        db.session.commit()

        # Call super which will reraise
        super(InvenioTransitionAction, InvenioTransitionAction).Exception(
            obj, eng, callbacks, exc_info
        )

    @staticmethod
    def WaitProcessing(obj, eng, callbacks, exc_info):
        """Take actions when WaitProcessing is raised.

        ..note::
            We're essentially doing HaltProcessing, plus `obj.set_action` and
            object status `WAITING` instead of `HALTED`.

            This is not present in TransitionActions so that's why it is not
            calling super in this case.
        """
        e = exc_info[1]
        obj.set_action(e.action, e.message)
        obj.save(status=eng.object_status.WAITING,
                 callback_pos=eng.state.callback_pos,
                 id_workflow=eng.uuid)
        eng.save(WorkflowStatus.HALTED)
        eng.log.warning("Workflow '%s' waiting at task %s with message: %s",
                        eng.name, eng.current_taskname or "Unknown", e.message)
        db.session.commit()

        # Call super which will reraise
        TransitionActions.HaltProcessing(
            obj, eng, callbacks, exc_info
        )

    @staticmethod
    def HaltProcessing(obj, eng, callbacks, exc_info):
        """Handle halted exception in workflow, saving states."""
        e = exc_info[1]
        if e.action:
            obj.set_action(e.action, e.message)
            obj.save(status=eng.object_status.HALTED,
                     callback_pos=eng.state.callback_pos,
                     id_workflow=eng.uuid)
            eng.save(WorkflowStatus.HALTED)
            obj.log.warning(
                "Workflow '%s' halted at task %s with message: %s",
                eng.name, eng.current_taskname or "Unknown", e.message
            )
            db.session.commit()

            # Call super which will reraise
            TransitionActions.HaltProcessing(
                obj, eng, callbacks, exc_info
            )
        else:
            InvenioTransitionAction.WaitProcessing(
                obj, eng, callbacks, exc_info
            )

    @staticmethod
    def StopProcessing(obj, eng, callbacks, exc_info):
        """Stop the engne and mark the workflow as completed."""
        e = exc_info[1]
        obj.save(status=eng.object_status.COMPLETED,
                 id_workflow=eng.uuid)
        eng.save(WorkflowStatus.COMPLETED)
        obj.log.warning(
            "Workflow '%s' stopped at task %s with message: %s",
            eng.name, eng.current_taskname or "Unknown", e.message
        )
        db.session.commit()

        super(InvenioTransitionAction, InvenioTransitionAction).StopProcessing(
            obj, eng, callbacks, exc_info
        )

    @staticmethod
    def SkipToken(obj, eng, callbacks, exc_info):
        """Take action when SkipToken is raised."""
        msg = "Skipped running this object: {0}".format(obj.id)
        eng.log.debug(msg)
        raise Continue

    @staticmethod
    def AbortProcessing(obj, eng, callbacks, exc_info):
        """Take action when AbortProcessing is raised."""
        msg = "Processing was aborted for object: {0}".format(obj.id)
        eng.log.debug(msg)
        raise Break
