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

"""Pytest configuration."""

from __future__ import absolute_import, print_function

import os
import shutil
import tempfile

import pytest
from flask import Flask
from flask_celeryext import FlaskCeleryExt
from flask_cli import FlaskCLI
from invenio_db import InvenioDB, db

from invenio_workflows import InvenioWorkflows


@pytest.fixture()
def app(request):
    """Flask application fixture."""
    instance_path = tempfile.mkdtemp()
    app = Flask(__name__, instance_path=instance_path)
    app.config.update(
        CELERY_ALWAYS_EAGER=True,
        CELERY_CACHE_BACKEND="memory",
        CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
        CELERY_RESULT_BACKEND="cache",
        SECRET_KEY="CHANGE_ME",
        SECURITY_PASSWORD_SALT="CHANGE_ME_ALSO",
        SQLALCHEMY_TRACK_MODIFICATIONS=True,
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI', 'sqlite:///test.db'),
        TESTING=True,
    )
    FlaskCLI(app)
    FlaskCeleryExt(app)
    InvenioDB(app)
    InvenioWorkflows(app)

    with app.app_context():
        db.create_all()

    def teardown():
        with app.app_context():
            db.drop_all()
        shutil.rmtree(instance_path)

    request.addfinalizer(teardown)
    return app


@pytest.fixture
def demo_workflow(app):
    def add(obj, eng):
        obj.data["x"] += 20

    def reduce(obj, eng):
        obj.data["x"] -= 2

    class DemoTest(object):
        workflow = [add, reduce]

    app.extensions['invenio-workflows'].register_workflow(
        'demo_workflow', DemoTest
    )
    return DemoTest


@pytest.fixture
def demo_halt_workflow(app):
    def add(obj, eng):
        obj.data["x"] += 20

    def reduce(obj, eng):
        obj.data["x"] -= 2

    def halt_condition(obj, eng):
        if obj.data["x"] < 10:
            eng.halt()

    class DemoTest(object):
        workflow = [add, halt_condition, reduce]

    app.extensions['invenio-workflows'].register_workflow(
        'demo_halt_workflow', DemoTest
    )
    return DemoTest


@pytest.fixture
def halt_workflow(app):
    def halt_engine(obj, eng):
        return eng.halt("Test")

    class HaltTest(object):
        workflow = [halt_engine]

    app.extensions['invenio-workflows'].register_workflow(
        'halttest', HaltTest
    )
    return HaltTest


@pytest.fixture
def restart_workflow(app):
    def halt_engine_action(obj, eng):
        return eng.halt("Test", action="foo")

    def add(obj, eng):
        if obj.data.get("title"):
            obj.data["title"] = {"value": "bar"}
        else:
            obj.data["title"] = "foo"

    def add_extra(obj, eng):
        obj.extra_data["test"] = "test"
        obj.data["title"]["source"] = "TEST"

    class RestartTest(object):
        workflow = [add, halt_engine_action, add_extra]

    app.extensions['invenio-workflows'].register_workflow(
        'restarttest', RestartTest
    )
    return RestartTest


@pytest.fixture
def error_workflow(app):
    def error_engine(obj, eng):
        raise ZeroDivisionError

    def add(obj, eng):
        obj.data["foo"] = "bar"

    def add_extra(obj, eng):
        obj.extra_data["test"] = "test"

    class ErrorTest(object):
        workflow = [add, error_engine, add_extra]

    app.extensions['invenio-workflows'].register_workflow(
        'errortest', ErrorTest
    )
    return ErrorTest


@pytest.fixture
def halt_workflow_conditional(app):
    from workflow.patterns import IF_ELSE

    def always_true(obj, eng):
        return True

    def halt_engine(obj, eng):
        return eng.halt("Test")

    class BranchTest(object):
        workflow = [
            IF_ELSE(always_true, [halt_engine], [halt_engine])
        ]

    app.extensions['invenio-workflows'].register_workflow(
        'halttestcond', BranchTest
    )
    return BranchTest
