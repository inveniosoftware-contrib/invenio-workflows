# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""API for invenio-workflows."""

from __future__ import absolute_import, print_function

from datetime import datetime

from flask import current_app
from invenio_db import db
from six import callable

from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm.exc import NoResultFound
from workflow.errors import WorkflowAPIError
from workflow.utils import staticproperty

from .errors import WorkflowsMissingObject, WorkflowsMissingModel
from .proxies import workflows
from .signals import workflow_object_after_save, workflow_object_before_save
from .utils import get_func_info
from .models import ObjectStatus, WorkflowObjectModel


class WorkflowObject(object):
    """Main entity for the workflow module."""

    def __init__(self, model=None):
        """Instantiate class."""
        self.model = model

    @staticproperty
    def known_statuses():  # pylint: disable=no-method-argument
        """Get type for object status."""
        return ObjectStatus

    @staticproperty
    def known_columns():  # pylint: disable=no-method-argument
        """Get type for object status."""
        return WorkflowObjectModel.__table__.columns.keys()

    @staticproperty
    def dbmodel():  # pylint: disable=no-method-argument
        """Get type for dbmodel."""
        return WorkflowObjectModel

    @property
    def workflow(self):
        """Get type for object status."""
        return self.model.workflow

    @property
    def log(self):
        """Access logger object for this instance."""
        return current_app.logger

    def __getattr__(self, name):
        """Wrap attribute access.

        To allow accessing the columns from the model as python attributes.
        """
        if name in self.known_columns:
            return getattr(self.model, name)
        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        """Wrap attribute set.

        To allow setting the rows of the model as python if they were python
        attributes.
        """
        if name in self.known_columns:
            return setattr(self.model, name, value)
        return object.__setattr__(self, name, value)

    def save(self, status=None, callback_pos=None, id_workflow=None):
        """Save object to persistent storage."""
        if self.model is None:
            raise WorkflowsMissingModel()

        with db.session.begin_nested():
            workflow_object_before_save.send(self)

            self.model.modified = datetime.now()
            if status is not None:
                self.model.status = status

            if id_workflow is not None:
                self.model.id_workflow = id_workflow

            # Special handling of JSON fields to mark update
            if self.model.callback_pos is None:
                self.model.callback_pos = list()
            elif callback_pos is not None:
                self.model.callback_pos = callback_pos
            flag_modified(self.model, 'callback_pos')

            if self.model.data is None:
                self.model.data = dict()
            flag_modified(self.model, 'data')

            if self.model.extra_data is None:
                self.model.extra_data = dict()
            flag_modified(self.model, 'extra_data')

            db.session.merge(self.model)

            if self.id is not None:
                self.log.debug("Saved object: {id} at {callback_pos}".format(
                    id=self.model.id or "new",
                    callback_pos=self.model.callback_pos
                ))
        workflow_object_after_save.send(self)

    @classmethod
    def create(cls, data, **kwargs):
        """Create a new Workflow Object with given content."""
        with db.session.begin_nested():
            model = cls.dbmodel(**kwargs)
            model.data = data
            obj = cls(model)
            db.session.add(obj.model)
        return obj

    @classmethod
    def get(cls, id_):
        """Return a workflow object from id."""
        with db.session.no_autoflush:
            query = cls.dbmodel.query.filter_by(id=id_)
            try:
                model = query.one()
            except NoResultFound:
                raise WorkflowsMissingObject("No object for for id {0}".format(
                    id_
                ))
            return cls(model)

    @classmethod
    def query(cls, *criteria, **filters):
        """Wrap sqlalchemy query methods.

        A wrapper for the filter and filter_by functions of sqlalchemy.
        Define a dict with which columns should be filtered by which values.

        .. codeblock:: python

            WorkflowObject.query(id=123)
            WorkflowObject.query(status=ObjectStatus.COMPLETED)

        The function supports also "hybrid" arguments using WorkflowObjectModel
        indirectly.

        .. codeblock:: python

            WorkflowObject.query(
                WorkflowObject.dbmodel.status == ObjectStatus.COMPLETED,
                user_id=user_id
            )

        See also SQLAlchemy BaseQuery's filter and filter_by documentation.
        """
        query = cls.dbmodel.query.filter(
            *criteria).filter_by(**filters)
        return [cls(obj) for obj in query.all()]

    def delete(self, force=False):
        """Delete a workflow object.

        If `force` is ``False``, the record is soft-deleted, i.e. the record
        stays in the database. This ensures e.g. that the same record
        identifier cannot be used twice, and that you can still retrieve the
        history of an object. If `force` is True, the record is completely
        removed from the database.

        :param force: Completely remove record from database.
        """
        if self.model is None:
            raise WorkflowsMissingModel()

        with db.session.begin_nested():
            db.session.delete(self.model)

        return self

    def __repr__(self):
        """Represent a WorkflowObject."""
        if self.model:
            return self.model.__repr__()

    def __eq__(self, other):
        """Enable equal operators on WorkflowObjects."""
        if isinstance(other, WorkflowObject):
            if self.data == other.data and \
                    self.extra_data == other.extra_data and \
                    self.id_workflow == other.id_workflow and \
                    self.status == other.status and \
                    self.id_parent == other.id_parent and \
                    isinstance(self.created, datetime) and \
                    isinstance(self.modified, datetime):
                return True
            else:
                return False
        return NotImplemented

    def __ne__(self, other):
        """Enable equal operators on WorkflowObjects."""
        return not self.__eq__(other)

    def set_action(self, action, message):
        """Set the action to be taken for this object.

        Assign an special "action" to this object to be taken
        in consideration in Holding Pen. The widget is referred to
        by a string with the filename minus extension.

        A message is also needed to tell the user the action
        required in a textual way.

        :param action: name of the action to add (i.e. "approval")
        :type action: string

        :param message: message to show to the user
        :type message: string
        """
        self.extra_data["_action"] = action
        self.extra_data["_message"] = message

    def get_action(self):
        """Retrieve the currently assigned action, if any.

        :return: name of action assigned as string, or None
        """
        return self.model.extra_data.get("_action")

    def get_action_message(self):
        """Retrieve the currently assigned widget, if any."""
        return self.model.extra_data.get("_message")

    def remove_action(self):
        """Remove the currently assigned action."""
        self.model.extra_data["_action"] = None
        self.model.extra_data["_message"] = ""

    def restart_current(self, **kwargs):
        """Restart workflow from current task."""
        return self.continue_workflow("restart_task", **kwargs)

    def restart_previous(self, **kwargs):
        """Restart workflow from previous task."""
        return self.continue_workflow("restart_prev", **kwargs)

    def restart_next(self, **kwargs):
        """Restart workflow from next task, skipping current."""
        return self.continue_workflow("continue_next", **kwargs)

    def start_workflow(self, workflow_name, delayed=False, **kwargs):
        """Run the workflow specified on the object.

        :param workflow_name: name of workflow to run
        :type workflow_name: str

        :param delayed: should the workflow run asynchronously?
        :type delayed: bool

        :return: UUID of WorkflowEngine (or AsyncResult).
        """
        from .tasks import start

        if delayed:
            self.save()
            db.session.commit()
            return start.delay(workflow_name, object_id=self.id, **kwargs)
        else:
            return start(workflow_name, data=[self], **kwargs)

    def continue_workflow(self, start_point="continue_next",
                          delayed=False, **kwargs):
        """Continue the workflow for this object.

        The parameter `start_point` allows you to specify the point of where
        the workflow shall continue:

        * restart_prev: will restart from the previous task

        * continue_next: will continue to the next task

        * restart_task: will restart the current task

        :param start_point: where should the workflow start from?
        :type start_point: str

        :param delayed: should the workflow run asynchronously?
        :type delayed: bool

        :return: UUID of WorkflowEngine (or AsyncResult).
        """
        from .tasks import resume

        self.save()
        if not self.id_workflow:
            raise WorkflowAPIError("No workflow associated with object: %r"
                                   % (repr(self),))
        if delayed:
            db.session.commit()
            return resume.delay(self.id, start_point, **kwargs)
        else:
            return resume(self.id, start_point, **kwargs)

    def get_current_task_info(self):
        """Return dictionary of current task function info for this object."""
        name = self.model.workflow.name
        if not name:
            return

        current_task = workflows[name].workflow
        for step in self.callback_pos:
            current_task = current_task[step]
            if callable(current_task):
                return get_func_info(current_task)
