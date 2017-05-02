# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2013, 2014, 2015, 2016 CERN.
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

"""Unit tests for workflows models."""

from __future__ import absolute_import

import pytest

from invenio_db import db
from invenio_workflows import WorkflowObject, start
from invenio_workflows.errors import WorkflowsMissingObject


def test_api(app, demo_halt_workflow):
    """Test WorkflowObject api function."""
    with app.app_context():
        # Test WorkflowObject.(create|query|get)
        # ======================================
        obj = WorkflowObject.create({"x": 22})
        db.session.commit()

        ident = obj.id

        obj = WorkflowObject.get(ident)
        obj.start_workflow("demo_halt_workflow")

        # Fetch object via query API
        objects = WorkflowObject.query(id=ident)
        assert len(objects) == 1
        obj = objects[0]

        # Workflow should have completed as x was always > 10
        # x = 22 + 20 - 2 = 40
        assert obj.data == {"x": 40}
        assert obj.status == obj.known_statuses.COMPLETED

        # Test WorkflowObject.restart_previous
        # ====================================
        # Workflow should now halt as x will be less than 10
        obj = WorkflowObject.create({"x": -20})
        db.session.commit()

        ident = obj.id

        obj.start_workflow("demo_halt_workflow", delayed=True)
        obj = WorkflowObject.get(ident)

        # x = -20 + 20 = 0
        assert obj.data == {"x": 0}
        # No action associated, so it should be waiting
        assert obj.status == obj.known_statuses.WAITING

        # To add 20 to x, we now restart previous task and now it should
        # not halt and complete fully
        obj.restart_previous()
        obj = WorkflowObject.get(ident)

        # x = 0 + 20 - 2 = 18
        assert obj.data == {"x": 18}
        assert obj.status == obj.known_statuses.COMPLETED

        # Test WorkflowObject.restart_next
        # ================================
        obj = WorkflowObject.create({"x": -100})
        db.session.commit()

        ident = obj.id

        obj.start_workflow("demo_halt_workflow")
        obj = WorkflowObject.get(ident)

        # x = -100 + 20 = -80
        assert obj.data == {"x": -80}
        assert obj.status == obj.known_statuses.WAITING

        obj.restart_next()
        obj = WorkflowObject.get(ident)

        # x = -80 - 2 = -82
        assert obj.data == {"x": -82}
        assert obj.status == obj.known_statuses.COMPLETED

        # Test WorkflowObject.restart_current
        # ===================================
        obj = WorkflowObject.create({"x": -100})
        db.session.commit()

        ident = obj.id

        obj.start_workflow("demo_halt_workflow")
        obj = WorkflowObject.get(ident)

        # x = -100 + 20 = -80
        assert obj.data == {"x": -80}
        assert obj.status == obj.known_statuses.WAITING

        obj.restart_current()
        obj = WorkflowObject.get(ident)

        # x = -80 - 2 = -82
        assert obj.data == {"x": -80}
        assert obj.status == obj.known_statuses.WAITING

        # Test WorkflowObject.delete
        # ==========================
        obj.delete()
        with pytest.raises(WorkflowsMissingObject):
            WorkflowObject.get(ident)


def test_task_info(app, halt_workflow):
    """Test WorkflowObject comparison functions."""
    with app.app_context():
        obj = WorkflowObject.create({"x": 22})
        start("halttest", obj)
        ident = obj.id
        obj = WorkflowObject.get(ident)
        task_info = obj.get_current_task_info()
        assert task_info["name"] == "halt_engine"


def test_equality(app, halt_workflow):
    """Test WorkflowObject comparison functions."""
    with app.app_context():
        obj1 = WorkflowObject.create({"x": 22})
        obj2 = WorkflowObject.create({"x": 22})
        start("halttest", [obj1, obj2])

        ident1 = obj1.id
        ident2 = obj2.id

        obj1 = WorkflowObject.get(ident1)
        obj2 = WorkflowObject.get(ident2)
        assert obj1 == obj2

        obj3 = WorkflowObject.create({"x": 22})
        obj4 = WorkflowObject.create({"x": 2})
        assert obj4 != obj3


def test_create_with_default_extra_data(app):
    """Test that the extra data dictionary is not shared between
    workflow instances."""
    with app.app_context():
        obj1 = WorkflowObject.create({"x": 22})
        obj1.extra_data['foo'] = 'bar'

        obj2 = WorkflowObject.create({"x": 22})
        assert obj2.extra_data is not obj1.extra_data
