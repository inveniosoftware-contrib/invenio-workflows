..
    This file is part of Invenio.
    Copyright (C) 2016 CERN.

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


.. automodule:: invenio_workflows

API Docs
========

Flask extension
---------------
.. automodule:: invenio_workflows.ext
   :members:
   :undoc-members:


Tasks API
---------
.. automodule:: invenio_workflows.tasks
   :members: start, resume, restart
   :undoc-members:
   :show-inheritance:
.. autotask:: invenio_workflows.tasks.start


Engine
------
.. automodule:: invenio_workflows.engine
   :members: ObjectStatus, WorkflowStatus, WorkflowEngine, InvenioProcessingFactory, InvenioActionMapper, InvenioTransitionAction
   :undoc-members:


Models
------
.. automodule:: invenio_workflows.models
   :members: ObjectStatus
   :undoc-members:


Errors
------
.. automodule:: invenio_workflows.errors
   :members:
   :undoc-members:

Signals
-------
.. automodule:: invenio_workflows.signals
   :members: workflow_finished, workflow_halted, workflow_started, workflow_error, workflow_object_before_save, workflow_object_after_save
   :undoc-members:
   :show-inheritance:
