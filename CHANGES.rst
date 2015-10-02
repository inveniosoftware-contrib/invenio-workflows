..
    This file is part of Invenio.
    Copyright (C) 2015 CERN.

    Invenio is free software; you can redistribute it
    and/or modify it under the terms of the GNU General Public License as
    published by the Free Software Foundation; either version 2 of the
    License, or (at your option) any later version.

    Invenio is distributed in the hope that it will be
    useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Invenio; if not, write to the
    Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
    MA 02111-1307, USA.

    In applying this license, CERN does not
    waive the privileges and immunities granted to it by virtue of its status
    as an Intergovernmental Organization or submit itself to any jurisdiction.

Changes
=======

Version 0.1.2 (released 2015-10-02)
-----------------------------------

Incompatible changes
~~~~~~~~~~~~~~~~~~~~

- Removes legacy sample workflows, tasks and definitions. (#14)

New features
~~~~~~~~~~~~

- Adds a simplistic manager to easily start workflows with data from
  files.

Bug fixes
~~~~~~~~~

- Fixes some PEP8 issues across the codebase. (#2)
- Upgrades the minimum version of invenio-base to 0.3.0.
- Removes dependencies to invenio.testsuite and replaces them with
  invenio_testing.
- Removes dependencies to invenio.celery and replaces them with
  invenio_celery.
- Removes dependencies to invenio.utils and replaces them with
  invenio_utils.
- Removes dependencies to invenio.ext and replaces them with
  invenio_ext.
- Removes calls to PluginManager consider_setuptools_entrypoints()
  removed in PyTest 2.8.0.
- Adds missing `invenio_base` dependency.
- Safely stores only strings in the task_history, avoiding potential
  serialization issues.

Notes
~~~~~

- Temporarily adds PEP8 ignore of E501 to some files in CI to be less
  disruptive to upcoming refactoring of this module.

Version 0.1.1 (released 2015-08-25)
-----------------------------------

- Adds missing 'invenio-upgrader' dependency and ammends imports.

Version 0.1.0 (released 2015-08-13)
-----------------------------------

- Initial public release.
