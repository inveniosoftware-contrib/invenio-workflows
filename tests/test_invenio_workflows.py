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


"""Module tests."""

from __future__ import absolute_import, print_function

import pytest
from demo_package.workflows.demo_workflow import demo_workflow
from flask import Flask
from invenio_db import db
from workflow.engine_db import WorkflowStatus
from workflow.errors import WorkflowDefinitionError

from invenio_workflows import InvenioWorkflows, WorkflowEngine, \
    WorkflowObject, restart, resume, start
from invenio_workflows.errors import WorkflowsMissingData, \
    WorkflowsMissingObject


def test_version():
    """Test version import."""
    from invenio_workflows import __version__
    assert __version__


def test_init():
    """Test extension initialization."""
    app = Flask('testapp')
    ext = InvenioWorkflows(app)
    assert 'invenio-workflows' in app.extensions
    ext.register_workflow('test_workflow', demo_workflow)
    assert 'test_workflow' in app.extensions['invenio-workflows'].workflows

    app = Flask('testapp')
    ext = InvenioWorkflows()
    assert 'invenio-workflows' not in app.extensions
    ext.init_app(app)
    assert 'invenio-workflows' in app.extensions


def test_halt(app, halt_workflow, halt_workflow_conditional):
    """Test halt task."""
    assert 'halttest' in app.extensions['invenio-workflows'].workflows
    assert 'halttestcond' in app.extensions['invenio-workflows'].workflows

    with app.app_context():
        data = [{'foo': 'bar'}]

        eng_uuid = start('halttest', data)

        eng = WorkflowEngine.from_uuid(eng_uuid)
        obj = list(eng.objects)[0]

        assert obj.known_statuses.WAITING == obj.status
        assert WorkflowStatus.HALTED == eng.status

        obj_id = obj.id
        obj.continue_workflow()

        obj = WorkflowObject.query.get(obj_id)
        assert obj.known_statuses.COMPLETED == obj.status

        # Check conditional workflows and pass data not as a list (to check).
        eng_uuid = start('halttestcond', data[0])
        eng = WorkflowEngine.from_uuid(eng_uuid)
        obj = list(eng.objects)[0]

        assert obj.known_statuses.WAITING == obj.status
        assert WorkflowStatus.HALTED == eng.status

        obj_id = obj.id
        obj.continue_workflow()

        obj = WorkflowObject.query.get(obj_id)
        assert obj.known_statuses.COMPLETED == obj.status


def test_restart(app, restart_workflow):
    """Test halt task."""
    assert 'restarttest' in app.extensions['invenio-workflows'].workflows

    with app.app_context():
        data = 0

        eng_uuid = start('restarttest', data)

        eng = WorkflowEngine.from_uuid(eng_uuid)
        obj = list(eng.objects)[0]

        assert obj.known_statuses.HALTED == obj.status
        assert WorkflowStatus.HALTED == eng.status
        assert obj.data == 10

        new_eng_uuid = restart(eng_uuid)

        assert new_eng_uuid == eng_uuid

        eng = WorkflowEngine.from_uuid(eng_uuid)
        obj = list(eng.objects)[0]

        assert obj.known_statuses.HALTED == obj.status
        assert WorkflowStatus.HALTED == eng.status
        assert obj.data == 20

        obj_id = obj.id

        resume(obj_id)

        obj = WorkflowObject.query.get(obj_id)
        assert obj.extra_data.get('test') == 'test'
        assert obj.known_statuses.COMPLETED == obj.status


def test_errors(app, error_workflow):
    """Test halt task."""
    assert 'errortest' in app.extensions['invenio-workflows'].workflows

    with app.app_context():
        with pytest.raises(WorkflowsMissingData):
            start('errortest')

        with pytest.raises(WorkflowDefinitionError):
            start('doesnotexist', 100)

        with pytest.raises(WorkflowsMissingObject):
            start('errortest', object_id=-1)

        obj = WorkflowObject.create_object()
        obj.data = 0
        obj.save()
        db.session.commit()

        obj_id = obj.id
        with pytest.raises(ZeroDivisionError):
            start('errortest', object_id=obj_id)

        obj = WorkflowObject.query.get(obj_id)

        assert obj.known_statuses.ERROR == obj.status
        assert obj.data == 10
