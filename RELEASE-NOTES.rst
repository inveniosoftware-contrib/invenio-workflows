==========================
 Invenio-Workflows v0.1.2
==========================

Invenio-Workflows v0.1.2 was released on October 2, 2015.

About
-----

Invenio module for running persistent workflows.

*This is an experimental development preview release.*

Incompatible changes
--------------------

- Removes legacy sample workflows, tasks and definitions. (#14)

New features
------------

- Adds a simplistic manager to easily start workflows with data from
  files.

Bug fixes
---------

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
-----

- Temporarily adds PEP8 ignore of E501 to some files in CI to be less
  disruptive to upcoming refactoring of this module.

Installation
------------

   $ pip install invenio-workflows==0.1.2

Documentation
-------------

   http://invenio-workflows.readthedocs.org/en/v0.1.2

Happy hacking and thanks for flying Invenio-Workflows.

| Invenio Development Team
|   Email: info@inveniosoftware.org
|   IRC: #invenio on irc.freenode.net
|   Twitter: http://twitter.com/inveniosoftware
|   GitHub: https://github.com/inveniosoftware/invenio-workflows
|   URL: http://inveniosoftware.org
