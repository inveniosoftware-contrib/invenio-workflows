# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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

from invenio.ext.sqlalchemy import db
from invenio_upgrader.api import op

from invenio_workflows.models import (
    CallbackPosType,
    ChoiceType,
    ObjectStatus,
    WorkflowStatus,
    _encoded_default_extra_data,
    _encoded_default_data,
    _decode,
    DbWorkflowObject
)

# Important: Below is only a best guess. You MUST validate which previous
# upgrade you depend on.
depends_on = [u'workflows_2015_06_05_resize_uuid_columns']


def info():
    """Info message."""
    return ""


def do_upgrade():
    """Implement your upgrades here."""

    # 1. <<< bwlWORKFLOW >>>

    # 1.1 KILL: counter_{initial,halted,error,finished} + current_object
    for column_name in ('counter_initial', 'counter_halted', 'counter_error',
                        'counter_finished', 'current_object'):
        op.drop_column('bwlWORKFLOW', column_name)

    # 2. <<< bwlOBJECT >>>
    op.drop_column('bwlOBJECT', 'status')

    # 2.1 version -> status (ChoiceType(ObjectStatus))
    op.alter_column('bwlOBJECT',
                    'version',
                    new_column_name='status',
                    existing_type=db.Integer,
                    existing_server_default='0',
                    existing_nullable=False)

    # 2.2 NEW: callback_pos (CallbackPosType)
    op.add_column('bwlOBJECT',
                  db.Column('callback_pos', CallbackPosType()))

    # 2.2 Data migration
    connection = op.get_bind()
    DbWorkflowObjectT = DbWorkflowObject.__table__  # pylint: disable=no-member
    for object_ in connection.execute(DbWorkflowObjectT.select()):
        extra_data = _decode(object_._extra_data)
        try:
            callback_pos = extra_data["_task_counter"]
            del extra_data["_task_counter"]
        except KeyError:
            # Assume old version of "task_counter"
            callback_pos = extra_data["task_counter"]
            del extra_data["task_counter"]
        connection.execute(
            DbWorkflowObjectT.update().where(
                DbWorkflowObjectT.c.id == object_.id
            ).values(
                callback_pos=callback_pos,
                _extra_data=extra_data,
            )
        )


def estimate():
    """Estimate running time of upgrade in seconds (optional)."""
    return 1


def pre_upgrade():
    """Run pre-upgrade checks (optional)."""
    # Example of raising errors:
    # raise RuntimeError("Description of error 1", "Description of error 2")


def post_upgrade():
    """Run post-upgrade checks (optional)."""
    # Example of issuing warnings:
    # warnings.warn("A continuable error occurred")
