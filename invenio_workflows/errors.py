# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2012, 2013, 2014, 2015 CERN.
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

"""Custom exceptions for invenio-workflows."""

from __future__ import absolute_import, print_function

from workflow.errors import HaltProcessing, with_str


class WorkflowsError(Exception):
    """Base exception for invenio-workflows."""


class WorkflowsMissingModel(WorkflowsError):
    """Model missing for invenio-workflows API."""


class WorkflowsMissingData(WorkflowsError):
    """No data available for workflow."""


class WorkflowsMissingObject(WorkflowsError):
    """Requested object not found."""


@with_str(('message', ('action', 'payload')))
class WaitProcessing(HaltProcessing, WorkflowsError):
    """Custom WaitProcessing handling."""

    def __init__(self, message="", action=None, payload=None):
        """Add required parameters to WaitProcessing."""
        super(WaitProcessing, self).__init__(
            message=message,
            action=action,
            payload=payload
        )


@with_str(('message', ('worker_name', 'payload')))
class WorkflowWorkerError(WorkflowsError):
    """Raised when there is a problem with workflow workers."""

    def __init__(self, message, worker_name="No Name Given", payload=None):
        """Instanciate a WorkflowWorkerError object."""
        super(WorkflowWorkerError, self).__init__()
        self.message = message
        self.worker_name = worker_name
        self.payload = payload
