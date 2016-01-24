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
    from demo_package.workflows.demo_workflow import demo_workflow
    app.extensions['invenio-workflows'].register_workflow(
        'demo_workflow', demo_workflow
    )
    # FIXME: Unknown why this is needed in only this case
    # app.extensions['flask-celeryext']\
    #    .celery.flask_app.extensions['invenio-workflows']\
    #    .register_workflow(
    #    'demo_workflow', demo_workflow
    # )
    return demo_workflow


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
        obj.data += 10

    def add_extra(obj, eng):
        obj.extra_data["test"] = "test"

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
        obj.data += 10

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
