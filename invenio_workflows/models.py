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

import uuid

from datetime import datetime

from invenio_db import db

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy_utils.types import ChoiceType, UUIDType, JSONType
from workflow.engine_db import EnumLabel, WorkflowStatus
from workflow.utils import staticproperty


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
    extra_data = db.Column(
        JSONType().with_variant(
            postgresql.JSON(none_as_null=True),
            'postgresql',
        ),
        default=lambda: dict(),
        nullable=False
    )
    status = db.Column(ChoiceType(WorkflowStatus, impl=db.Integer()),
                       default=WorkflowStatus.NEW, nullable=False)
    objects = db.relationship("WorkflowObjectModel",
                              backref='workflows_workflow',
                              cascade="all, delete-orphan")

    def __repr__(self):
        """Represent a workflow object."""
        return "<Workflow(name: %s, cre: %s, mod: %s," \
               "id_user: %s, status: %s)>" % \
               (str(self.name),  str(self.created), str(self.modified),
                str(self.id_user), str(self.status))

    @classmethod
    def delete(cls, uuid=None):
        """Delete a workflow."""
        uuid = uuid or cls.uuid
        db.session.delete(Workflow.query.get(uuid))

    def save(self, status=None):
        """Save object to persistent storage."""
        with db.session.begin_nested():
            self.modified = datetime.now()
            if status is not None:
                self.status = status
            if self.extra_data is None:
                self.extra_data = dict()
            flag_modified(self, 'extra_data')
            db.session.merge(self)


class WorkflowObjectModel(db.Model):
    """Data model for wrapping data being run in the workflows.

    Main object being passed around in the workflows module
    when using the workflows API.

    It can be instantiated like this:

    .. code-block:: python

        obj = WorkflowObject.create(data={"title": "Of the foo and bar"})


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

    data = db.Column(
        JSONType().with_variant(
            postgresql.JSON(none_as_null=True),
            'postgresql',
        ),
        default=lambda: dict(),
        nullable=False
    )

    extra_data = db.Column(
        JSONType().with_variant(
            postgresql.JSON(none_as_null=True),
            'postgresql',
        ),
        default=lambda: dict(),
        nullable=False
    )

    _id_workflow = db.Column(UUIDType,
                             db.ForeignKey("workflows_workflow.uuid",
                                           ondelete='CASCADE'),
                             nullable=True, name="id_workflow", index=True)

    status = db.Column(ChoiceType(ObjectStatus, impl=db.Integer()),
                       default=ObjectStatus.INITIAL, nullable=False,
                       index=True)

    id_parent = db.Column(db.Integer, db.ForeignKey("workflows_object.id",
                                                    ondelete='CASCADE'),
                          default=None, index=True)

    child_objects = db.relationship("WorkflowObjectModel",
                                    remote_side=[id_parent])

    created = db.Column(db.DateTime, default=datetime.now, nullable=False)

    modified = db.Column(db.DateTime, default=datetime.now,
                         onupdate=datetime.now, nullable=False)

    data_type = db.Column(db.String(150), default="",
                          nullable=True, index=True)

    id_user = db.Column(db.Integer, default=0, nullable=False)

    callback_pos = db.Column(
        JSONType().with_variant(
            postgresql.JSON(none_as_null=True),
            'postgresql',
        ),
        default=lambda: list(),
        nullable=True
    )

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

    def __repr__(self):
        """Represent a WorkflowObject."""
        return "<WorkflowObject(id = %s, id_workflow = %s, " \
               "status = %s, id_parent = %s, created = %s, )" \
               % (str(self.id), str(self.id_workflow), str(self.status),
                  str(self.id_parent), str(self.created))


__all__ = ('Workflow', 'WorkflowObjectModel')
