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

from __future__ import absolute_import, print_function

import pytest
from sqlalchemy import inspect

from invenio_db.utils import drop_alembic_version_table


def test_alembic_revision_a26f133d42a9(app, db):
    ext = app.extensions['invenio-db']

    if db.engine.name == 'sqlite':
        raise pytest.skip('Upgrades are not supported on SQLite.')

    db.drop_all()
    drop_alembic_version_table()

    with app.app_context():
        inspector = inspect(db.engine)
        assert 'workflows_workflow' not in inspector.get_table_names()
        assert 'workflows_object' not in inspector.get_table_names()

    ext.alembic.upgrade(target='a26f133d42a9')
    with app.app_context():
        inspector = inspect(db.engine)
        assert 'workflows_workflow' in inspector.get_table_names()
        assert 'workflows_object' in inspector.get_table_names()

    ext.alembic.downgrade(target='720ddf51e24b')
    with app.app_context():
        inspector = inspect(db.engine)
        assert 'workflows_workflow' not in inspector.get_table_names()
        assert 'workflows_object' not in inspector.get_table_names()

    drop_alembic_version_table()
