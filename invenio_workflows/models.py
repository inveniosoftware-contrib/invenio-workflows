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

"""Models for workflow engine and objects."""

import base64
import uuid
from collections import Iterable, namedtuple
from datetime import datetime

from flask import current_app
from invenio_db import db
from six import callable, iteritems
from six.moves import cPickle
from sqlalchemy import desc
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_utils.types import ChoiceType, UUIDType
from workflow.engine_db import EnumLabel, WorkflowStatus
from workflow.errors import WorkflowAPIError
from workflow.utils import staticproperty

from .proxies import workflows
from .signals import workflow_object_after_save, workflow_object_before_save
from .utils import get_func_info


class ObjectStatus(EnumLabel):

    INITIAL = 0
    COMPLETED = 1
    HALTED = 2
    RUNNING = 3
    WAITING = 4
    ERROR = 5

    @staticproperty
    def labels():  # pylint: disable=no-method-argument
        return {
            0: "New",
            1: "Done",
            2: "Need action",
            3: "In process",
            4: "Waiting",
            5: "Error",
        }


class CallbackPosType(db.PickleType):

    def process_bind_param(self, value, dialect):
        if not isinstance(value, Iterable):
            raise TypeError("Task counter must be an iterable!")
        return self.type_impl.process_bind_param(value, dialect)  # noqa


def _decode(data):
    return cPickle.loads(base64.b64decode(data))


def _encode(data):
    return base64.b64encode(cPickle.dumps(data))


class Workflow(db.Model):
    """Represents a workflow instance storing the state of the workflow."""

    __tablename__ = "workflows_workflow"

    uuid = db.Column(UUIDType, primary_key=True,
                     nullable=False, default=uuid.uuid4())
    name = db.Column(db.String(255), default="Default workflow",
                     nullable=False)
    created = db.Column(db.DateTime, default=datetime.now, nullable=False)
    modified = db.Column(db.DateTime, default=datetime.now,
                         onupdate=datetime.now, nullable=False)
    id_user = db.Column(db.Integer, default=0, nullable=False)
    _extra_data = db.Column(db.LargeBinary,
                            nullable=False,
                            default=_encode({}))
    status = db.Column(ChoiceType(WorkflowStatus, impl=db.Integer()),
                       default=WorkflowStatus.NEW, nullable=False)
    objects = db.relationship("WorkflowObject",
                              backref='workflows_workflow',
                              cascade="all, delete-orphan")

    def __getattribute__(self, name):
        """Return `extra_data` user-facing storage representations.

        Initialize the one requested with default content if it is not yet
        loaded.

        Calling :py:func:`.save` is necessary to reflect any changes made to
        these objects in the model.
        """
        data_getter = {
            'extra_data': Mapping('_extra_data', _encode({})),
        }
        if name in data_getter and name not in self.__dict__:
            mapping = data_getter[name]
            if getattr(self, mapping.db_name) is None:
                # Object has not yet been intialized
                stored_data = mapping.default_x_data
            else:
                stored_data = getattr(self, mapping.db_name)
            setattr(self, name, _decode(stored_data))
        return object.__getattribute__(self, name)

    def __dir__(self):
        """Restore auto-completion for names found via `__getattribute__`."""
        dir_ = dir(type(self)) + list(self.__dict__.keys())
        dir_.extend(('extra_data',))
        return sorted(dir_)

    def __repr__(self):
        """Represent a workflow object."""
        return "<Workflow(name: %s, cre: %s, mod: %s," \
               "id_user: %s, status: %s)>" % \
               (str(self.name),  str(self.created), str(self.modified),
                str(self.id_user), str(self.status))

    @classmethod
    def get(cls, *criteria, **filters):
        """Wrapper to get a specified object.

        A wrapper for the filter and filter_by functions of sqlalchemy.
        Define a dict with which columns should be filtered by which values.

        .. code-block:: python

            Workflow.get(uuid=uuid)
            Workflow.get(Workflow.uuid != uuid)

        The function supports also "hybrid" arguments.

        .. code-block:: python

            Workflow.get(Workflow.module_name != 'i_hate_this_module',
                         user_id=user_id)

        See also SQLAlchemy BaseQuery's filter and filter_by documentation.
        """
        return cls.query.filter(*criteria).filter_by(**filters)

    @classmethod
    def get_status(cls, uuid=None):
        """Return the status of the workflow."""
        return cls.get(Workflow.uuid == uuid).one().status

    @classmethod
    def get_most_recent(cls, *criteria, **filters):
        """Return the most recently modified workflow."""
        most_recent = cls.get(*criteria, **filters). \
            order_by(desc(Workflow.modified)).first()
        if most_recent is None:
            raise NoResultFound
        else:
            return most_recent

    @classmethod
    def get_objects(cls, uuid=None):
        """Return the objects of the workflow."""
        return cls.get(Workflow.uuid == uuid).one().objects

    # Deprecated
    def get_extra_data(self, user_id=0, uuid=None, key=None, getter=None):
        """Get the extra_data for the object.

        Returns a JSON of the column extra_data or
        if any of the other arguments are defined,
        a specific value.

        You can define either the key or the getter function.

        :param key: the key to access the desirable value
        :param getter: callable that takes a dict as param and returns a value
        """
        if key:
            return self.extra_data[key]
        elif callable(getter):
            return getter(self.extra_data)
        elif not key:
            return self.extra_data

    # Deprecated
    def set_extra_data(self, user_id=0, uuid=None,
                       key=None, value=None, setter=None):
        """Replace extra_data.

        Modifies the JSON of the column extra_data or
        if any of the other arguments are defined, a specific value.
        You can define either the key, value or the setter function.

        :param key: the key to access the desirable value
        :param value: the new value
        :param setter: a callable that takes a dict as param and modifies it
        """
        if key is not None and value is not None:
            self.extra_data[key] = value
        elif callable(setter):
            setter(self.extra_data)

    @classmethod
    def delete(cls, uuid=None):
        """Delete a workflow."""
        uuid = uuid or cls.uuid
        db.session.delete(cls.get(Workflow.uuid == uuid).first())

    def save(self, status=None):
        """Save object to persistent storage."""
        with db.session.begin_nested():
            self.modified = datetime.now()
            if status is not None:
                self.status = status
            self._extra_data = _encode(self.extra_data)
            db.session.merge(self)


Mapping = namedtuple('Mapping', ['db_name', 'default_x_data'])


class WorkflowObject(db.Model):
    """Data model for wrapping data being run in the workflows.

    Main object being passed around in the workflows module
    when using the workflows API.

    It can be instantiated like this:

    .. code-block:: python

        obj = WorkflowObject.create_object()


    WorkflowObject provides some handy functions such as:

    .. code-block:: python

        obj.data = "<xml ..... />"
        obj.data == "<xml ..... />"
        obj.extra_data = {"param": value}
        obj.extra_data == {"param": value}


    Then to finally save the object

    .. code-block:: python

        obj.save()
        db.session.commit()


    Now you can for example run it in a workflow:

    .. code-block:: python

        obj.start_workflow("sample_workflow")
    """

    __tablename__ = "workflows_object"

    id = db.Column(db.Integer, primary_key=True)

    # Our internal data column. Default is encoded dict.
    _data = db.Column(db.LargeBinary, nullable=False,
                      default=_encode({}))

    _extra_data = db.Column(db.LargeBinary, nullable=False,
                            default=_encode({}))

    _id_workflow = db.Column(UUIDType,
                             db.ForeignKey("workflows_workflow.uuid",
                                           ondelete='CASCADE'),
                             nullable=True, name="id_workflow")

    status = db.Column(ChoiceType(ObjectStatus, impl=db.Integer()),
                       default=ObjectStatus.INITIAL, nullable=False,
                       index=True)

    id_parent = db.Column(db.Integer, db.ForeignKey("workflows_object.id",
                                                    ondelete='CASCADE'),
                          default=None)

    child_objects = db.relationship("WorkflowObject",
                                    remote_side=[id_parent])

    created = db.Column(db.DateTime, default=datetime.now, nullable=False)

    modified = db.Column(db.DateTime, default=datetime.now,
                         onupdate=datetime.now, nullable=False)

    data_type = db.Column(db.String(150), default="",
                          nullable=True, index=True)

    id_user = db.Column(db.Integer, default=0, nullable=False)

    # Set blank comparator to update PickleType at all times
    # Ref: https://bitbucket.org/zzzeek/sqlalchemy/
    # issues/2994/pickletype-gets-not-updated-in-database-in
    callback_pos = db.Column(CallbackPosType(comparator=lambda *a: False),
                             default=[])

    workflow = db.relationship(
        Workflow, foreign_keys=[_id_workflow], remote_side=Workflow.uuid,
        post_update=True,
    )

    @hybrid_property
    def id_workflow(self):  # pylint: disable=method-hidden
        """Get id_workflow."""
        return self._id_workflow

    @id_workflow.setter
    def id_workflow(self, value):
        """Set id_workflow."""
        self._id_workflow = str(value) if value else None

    @staticproperty
    def known_statuses():  # pylint: disable=no-method-argument
        """Get type for object status."""
        return ObjectStatus

    def __getattribute__(self, name):
        """Return `data` and `extra_data` user-facing storage representations.

        Initialize the one requested with default content if it is not yet
        loaded.

        Calling :py:func:`.save` is necessary to reflect any changes made to
        these objects in the model.
        """
        data_getter = {
            'data': Mapping('_data', _encode({})),
            'extra_data': Mapping('_extra_data', _encode({})),
        }
        if name in data_getter and name not in self.__dict__:
            mapping = data_getter[name]
            if getattr(self, mapping.db_name) is None:
                # Object has not yet been intialized
                stored_data = mapping.default_x_data
            else:
                stored_data = getattr(self, mapping.db_name)
            setattr(self, name, _decode(stored_data))
        return object.__getattribute__(self, name)

    def __dir__(self):
        """Restore auto-completion for names found via `__getattribute__`."""
        dir_ = dir(type(self)) + list(self.__dict__.keys())
        dir_.extend(('data', 'extra_data',))
        return sorted(dir_)

    @property
    def log(self):
        """Access logger object for this instance."""
        return current_app.logger

    # Deprecated
    def get_data(self):
        """Get data saved in the object."""
        return self.data

    # Deprecated
    def set_data(self, value):
        """Save data to the object."""
        self.data = value

    # Deprecated
    def get_extra_data(self):
        """Get extra data saved to the object."""
        return self.extra_data

    # Deprecated
    def set_extra_data(self, value):
        """Save extra data to the object.

        :param value: what you want to replace extra_data with.
        :type value: dict
        """
        self.extra_data = value

    def get_workflow_name(self):
        """Return the workflow name for this object."""
        try:
            if self.id_workflow:
                return Workflow.query.get(self.id_workflow).name
        except AttributeError:
            # Workflow non-existent
            pass
        return

    def get_formatted_data(self, **kwargs):
        """Get the formatted representation for this object."""
        try:
            name = self.get_workflow_name()
            if not name:
                return "Did not find any way to format data."
            workflow_definition = workflows[name]
            formatted_data = workflow_definition.formatter(
                self,
                **kwargs
            )
        except (KeyError, AttributeError) as err:
            # Somehow the workflow or formatter does not exist
            formatted_data = "Error formatting record: {0}".format(err)
            current_app.logger.exception(err)
        return formatted_data

    def __repr__(self):
        """Represent a WorkflowObject."""
        return "<WorkflowObject(id = %s, id_workflow = %s, " \
               "status = %s, id_parent = %s, created = %s, )" \
               % (str(self.id), str(self.id_workflow), str(self.status),
                  str(self.id_parent), str(self.created))

    def __eq__(self, other):
        """Enable equal operators on WorkflowObjects."""
        if isinstance(other, WorkflowObject):
            if self._data == other._data and \
                    self._extra_data == other._extra_data and \
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
        return self.extra_data.get("_action")

    def get_action_message(self):
        """Retrieve the currently assigned widget, if any."""
        return self.extra_data.get("_message")

    def remove_action(self):
        """Remove the currently assigned action."""
        extra_data = self.extra_data
        extra_data["_action"] = None
        extra_data["_message"] = ""
        if "_widget" in extra_data:
            del extra_data["_widget"]
        self.set_extra_data(extra_data)

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

    # Deprecated
    def get_current_task(self):
        """Return the current task from the workflow engine for this object."""
        return self.callback_pos

    def get_current_task_info(self):
        """Return dictionary of current task function info for this object."""
        name = self.get_workflow_name()
        if not name:
            return

        current_task = workflows[name].workflow
        for step in self.callback_pos:
            current_task = current_task[step]
            if callable(current_task):
                return get_func_info(current_task)

    def copy(self, other):
        """Copy data and metadata except id and id_workflow."""
        for attr in ('status', 'id_parent', 'created',
                     'modified', 'status', 'data_type'):
            setattr(self, attr, getattr(other, attr))
        setattr(self, 'data', other.data)
        setattr(self, 'extra_data', other.extra_data)
        return self

    def save(self, status=None, callback_pos=None, id_workflow=None):
        """Save object to persistent storage."""
        with db.session.begin_nested():
            workflow_object_before_save.send(self)

            if callback_pos is not None:
                self.callback_pos = callback_pos  # Used by admins
            self.log.debug("Current callback pos: %s" % (self.callback_pos,))
            self._data = _encode(self.data)
            self._extra_data = _encode(self.extra_data)

            self.modified = datetime.now()
            if status is not None:
                self.status = status
            if id_workflow is not None:
                self.id_workflow = id_workflow
            db.session.merge(self)
            if self.id is not None:
                self.log.debug("Saved object: %s" % (self.id or "new",))
        workflow_object_after_save.send(self)

    @classmethod
    def create_object(cls, **kwargs):
        """Create a new Workflow Object with given content."""
        obj = WorkflowObject(**kwargs)
        with db.session.begin_nested():
            db.session.add(obj)
        return obj


__all__ = ('Workflow', 'WorkflowObject')
