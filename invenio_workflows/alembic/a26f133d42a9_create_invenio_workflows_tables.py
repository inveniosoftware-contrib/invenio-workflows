# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017 CERN.
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

"""Create invenio_workflows tables."""

from __future__ import absolute_import, print_function

import uuid

from alembic import op
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy_utils.types import ChoiceType, UUIDType, JSONType
from workflow.engine_db import WorkflowStatus
from invenio_workflows.models import ObjectStatus

# revision identifiers, used by Alembic.
revision = 'a26f133d42a9'
down_revision = '720ddf51e24b'
branch_labels = ()
depends_on = None


def upgrade():
    """Upgrade database."""
    op.create_table(
        'workflows_workflow',
        sa.Column(
            'uuid',
            UUIDType,
            primary_key=True,
            nullable=False,
            default=uuid.uuid4()
        ),
        sa.Column(
            'name',
            sa.String(255),
            default='Default workflow',
            nullable=False
        ),
        sa.Column(
            'created',
            sa.DateTime,
            default=datetime.now,
            nullable=False
        ),
        sa.Column(
            'modified',
            sa.DateTime,
            default=datetime.now,
            onupdate=datetime.now,
            nullable=False
        ),
        sa.Column('id_user', sa.Integer, default=0, nullable=False),
        sa.Column(
            'extra_data',
            JSONType().with_variant(
                postgresql.JSON(none_as_null=True),
                'postgresql',
            ),
            default=lambda: dict(),
            nullable=False
        ),
        sa.Column(
            'status',
            ChoiceType(WorkflowStatus, impl=sa.Integer()),
            default=WorkflowStatus.NEW,
            nullable=False
        )
    )

    op.create_table(
        'workflows_object',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column(
            'data',
            JSONType().with_variant(
                postgresql.JSON(none_as_null=True),
                'postgresql',
            ),
            default=lambda: dict(),
            nullable=False
        ),
        sa.Column(
            'extra_data',
            JSONType().with_variant(
                postgresql.JSON(none_as_null=True),
                'postgresql',
            ),
            default=lambda: dict(),
            nullable=False
        ),
        sa.Column(
            'id_workflow',
            UUIDType,
            sa.ForeignKey('workflows_workflow.uuid', ondelete='CASCADE'),
            nullable=True,
            index=True
        ),
        sa.Column(
            'status',
            ChoiceType(ObjectStatus, impl=sa.Integer()),
            default=ObjectStatus.INITIAL,
            nullable=False,
            index=True
        ),
        sa.Column(
            'id_parent',
            sa.Integer,
            sa.ForeignKey('workflows_object.id', ondelete='CASCADE'),
            default=None,
            index=True
        ),
        sa.Column('id_user', sa.Integer, default=0, nullable=False),
        sa.Column(
            'created',
            sa.DateTime,
            default=datetime.now,
            nullable=False
        ),
        sa.Column(
            'modified',
            sa.DateTime,
            default=datetime.now,
            onupdate=datetime.now,
            nullable=False
        ),
        sa.Column(
            'data_type',
            sa.String(150),
            default='',
            nullable=True,
            index=True
        ),
        sa.Column('id_user', sa.Integer, default=0, nullable=False),
        sa.Column(
            'callback_pos',
            JSONType().with_variant(
                postgresql.JSON(none_as_null=True),
                'postgresql',
            ),
            default=lambda: list(),
            nullable=True
        )
    )


def downgrade():
    """Downgrade database."""
    op.drop_table('workflows_object')
    op.drop_table('workflows_workflow')
