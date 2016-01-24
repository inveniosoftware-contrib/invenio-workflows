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

"""Contain signals emitted from workflows module."""

from flask.signals import Namespace
from workflow.signals import workflow_error, workflow_finished, \
    workflow_halted, workflow_started

_signals = Namespace()

workflow_object_before_save = _signals.signal('workflow_object_before_save')
"""This signal is sent when a workflow object is saved."""

workflow_object_after_save = _signals.signal('workflow_object_after_save')
"""This signal is sent when a workflow object is saved."""

__all__ = (
    'workflow_finished',
    'workflow_halted',
    'workflow_started',
    'workflow_error',
    'workflow_object_after_save',
    'workflow_object_before_save'
)
