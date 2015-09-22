# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015 CERN.
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

"""Perform operations with workflows."""

from __future__ import print_function

import argparse
import sys

from flask import current_app

from invenio_ext.script import Manager

import six

from werkzeug.utils import import_string

from .api import (
    start as start_workflow,
    start_delayed
)

manager = Manager(description=__doc__)


def split_marcxml(source):
    """Split a MARCXML file using dojson MARC21 utils."""
    from dojson.contrib.marc21.utils import split_blob
    return [data for data in split_blob(source.read())]


@manager.option('name', help="Name of workflow to start.")
@manager.option('-i', '--input', type=argparse.FileType('r'),
                default=sys.stdin, help="Input file (defaults to STDIN).",
                dest='source')
@manager.option('-t', '--input-type', dest='input_type', default='json',
                help="Format of input file.")
@manager.option('--delayed', dest='delayed', action='store_true',
                help="Run workflows asynchronously.")
def start(name, source, input_type='json', delayed=False):
    """Run given workflow with data from file."""
    processor = current_app.config['WORKFLOWS_DATA_PROCESSORS'][input_type]
    if isinstance(processor, six.string_types):
        processor = import_string(processor)
    if delayed:
        start_delayed(name, processor(source))
    else:
        start_workflow(name, processor(source))


@manager.option('-v', '--verbose', dest='verbose', action='store_true',
                help="More verbose output.")
def list(verbose=False):
    """List available workflows."""
    from invenio_workflows.registry import workflows

    for workflow, obj in six.iteritems(workflows):
        if verbose:
            print('{0}:{1}'.format(obj.__module__, workflow))
        else:
            print(workflow)


def main():
    """Run manager."""
    from invenio_base.factory import create_app
    app = create_app()
    manager.app = app
    manager.run()

if __name__ == '__main__':
    main()
