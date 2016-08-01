# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2014, 2015, 2016 CERN.
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

"""Test for delayed workflows."""

from __future__ import absolute_import

from workflow.engine_db import WorkflowStatus

from invenio_workflows import WorkflowEngine, WorkflowObject, resume, start


def test_delayed_execution(app, halt_workflow):
    """Test continue object task."""
    with app.app_context():
        data = [{'foo': 'bar'}]

        async_result = start.delay('halttest', data)

        eng = WorkflowEngine.from_uuid(async_result.get())
        obj = eng.processed_objects[0]

        assert obj.known_statuses.WAITING == obj.status
        assert WorkflowStatus.HALTED == eng.status

        obj_id = obj.id
        obj.continue_workflow(delayed=True)

        obj = WorkflowObject.get(obj_id)
        assert obj.known_statuses.COMPLETED == obj.status


def test_delayed_execution_api(app, halt_workflow):
    """Test continue object task."""
    with app.app_context():
        data = [{'foo': 'bar'}]

        async_result = start.delay('halttest', data)

        eng = WorkflowEngine.from_uuid(async_result.get())
        obj = eng.processed_objects[0]

        assert obj.known_statuses.WAITING == obj.status
        assert WorkflowStatus.HALTED == eng.status

        obj_id = obj.id
        resume.delay(obj_id)

        obj = WorkflowObject.get(obj_id)
        assert obj.known_statuses.COMPLETED == obj.status
