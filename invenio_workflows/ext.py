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

"""Invenio module for running workflows."""

from __future__ import absolute_import, print_function

import pkg_resources

from werkzeug.utils import cached_property

from .utils import obj_or_import_string


class _WorkflowState(object):
    """State of registered workflows."""

    def __init__(self, app, entry_point_group=None, cache=None):
        """Initialize state."""
        self.app = app
        self.workflows = {}
        if entry_point_group:
            self.load_entry_point_group(entry_point_group)

    @cached_property
    def workflow_object_class(self):
        return obj_or_import_string(
            self.app.config.get('WORKFLOWS_OBJECT_CLASS')
        )

    def register_workflow(self, name, workflow):
        """Register an workflow to be showed in the workflows list."""
        assert name not in self.workflows
        self.workflows[name] = workflow

    def load_entry_point_group(self, entry_point_group):
        """Load workflows from an entry point group."""
        for ep in pkg_resources.iter_entry_points(group=entry_point_group):
            self.register_workflow(ep.name, ep.load())


class InvenioWorkflows(object):
    """invenio-workflows extension."""

    def __init__(self, app=None, **kwargs):
        """Extension initialization."""
        if app:
            self._state = self.init_app(app, **kwargs)

    def init_app(self, app,
                 entry_point_group='invenio_workflows.workflows',
                 **kwargs):
        """Flask application initialization."""
        app.config.setdefault(
            "WORKFLOWS_OBJECT_CLASS",
            "invenio_workflows.api.WorkflowObject"
        )
        state = _WorkflowState(
            app, entry_point_group=entry_point_group, **kwargs
        )
        app.extensions['invenio-workflows'] = state
        return state

    def __getattr__(self, name):
        """Proxy to state object."""
        return getattr(self._state, name, None)
