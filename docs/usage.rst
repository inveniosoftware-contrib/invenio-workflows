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


Usage
=====

This module allows you to easily push your data through one or several
functions, in a specified order, while keeping a persistent state of the data
along the way which allows the execution to be stopped and resumed
at a later time.


Create callbacks
----------------

The functions in the workflow are called callbacks (or tasks). Each callback
must *at least* allow two arguments:

.. code-block:: python

    def halt_if_higher_than_20(obj, eng):
        """Check if current data is more than than 20."""
        if obj.data > 20:
            eng.halt("Data higher than 20.")


`obj` (`WorkflowObject`)
    **is the current object being worked on**

    `obj` adds extra functionality by wrapping around your data and
    provide utilities to interface with, e.g. in the Holding Pen
    (invenio-workflow-ui) interface.

`eng` (`WorkflowEngine`)
    **is the current instance of the workflow engine**

    `eng` give you access to manipulating the workflow execution itself and
    to retrieve all the objects being processed.

Pass additional arguments
~~~~~~~~~~~~~~~~~~~~~~~~~

To allow arguments being passed to the task from the workflow definition,
simply wrap your task in a closure:

.. code-block:: python

    def add_data(data_param):
        """Add data_param to the obj.data."""
        def _add_data(obj, eng):
            data = data_param
            obj.data += data

        return _add_data

It can then be called from the workflow definition as `add_data(20)`,
returning the inner function.


Create and register a workflow
------------------------------

With the callbacks ready, you can now design a workflow using them. In the same
file as the callbacks add a class definition:

.. code-block:: python

    class MyWorkflow(object):
        """Add 20 to data and halt if higher."""
        workflow = [add_data(20),
                    halt_if_higher_than_20]


Save it as a new file in your Invenio 3 overlay. For example at
`youroverlay/workflows.py`.

The `workflow` attribute of ``MyWorkflow`` should be a list of functions
(or even list of lists of tasks) as per the requirements of the
underlying `workflows-module`_ this library is built upon.

Next, register the workflow to be used with `invenio-workflows` API via
`entry_points` in your ``setup.py`` inside the overlay.

.. code-block:: python

    entry_points={
        ...,
        'invenio_workflows.workflows': [
            'MyWorkflow = youroverlay.workflows:MyWorkflow',
        ],
        ...
    }

This workflow is now referred to later as `MyWorkflow`.


.. sidebar:: Holding Pen (invenio-workflow-ui)

    The Python library ``invenio-workflow-ui`` provides "Holding Pen" which is
    a web interface showing all the data objects that ran through a workflow.

    This interface you can customize for your data objects and
    interact with the workflows and data directly in a convenient matter.


Run a workflow
--------------

Finally, to run your workflow you there are mainly two use-cases:

    * run it **immediately** in the same process, or
    * delay execution asynchronously with `Celery`_

Generally, which method you apply depends on your use case, but
usually heavy workflows are better run asynchronously as they can then be
queued and run in a distributed manner.


Run workflows synchronously
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from invenio_workflows import start
    eng_uuid = start("MyWorkflow", data=10)


Once the workflow completes it will return the UUID of the
``WorkflowEngine`` that ran it.

Your data (and much more) is contained inside a
``WorkflowObject`` instance that you can
get from the engine instance in the following way:

.. code-block:: python

    from invenio_workflow import WorkflowEngine
    engine = WorkflowEngine.from_uuid(eng_uuid)
    engine.objects


Finally, to get the data, simply lookup the `data` attribute of the
``WorkflowObject``:

.. code-block:: python

    engine.objects[0].data   # returns the new data. E.g. 30


Pass multiple data objects
~~~~~~~~~~~~~~~~~~~~~~~~~~

To run several objects through the same workflow, simply pass a list of data
items:

.. code-block:: python

    from invenio_workflows import start
    eng_uuid = start("MyWorkflow", data=[5, 10])


As usual, the ``invenio_workflows.start`` function returns the UUID
of the engine that ran the workflow. You can query this object to retrieve the
data you sent in:

.. code-block:: python

    from invenio_workflow import WorkflowEngine
    engine = WorkflowEngine.from_uuid(eng_uuid)
    len(engine.objects)  # E.g. 2, since two data items was given


.. sidebar:: State machine

    The data you pass to the workflows API is wrapped in a
    ``WorkflowObject``.

    This object have a `status` property which tells you the state of object.
    For example, if the object is currently *HALTED* in the middle of a
    workflow, or if it has *COMPLETED*.



Moreover, to retrieve the data from the first object, you can use
`data` as with single objects:

.. code-block:: python

    engine.objects[0].data   # E.g. 25


Run workflows asynchronously
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

So far we have been running our workflows in the current process. However,
for long running processes we might not want to wait for the workflow to finish
before continuing the processing.

Since ``invenio-workflows`` is based on `Celery`_, we simply use the Celery
options added to the API functions. In the case of ``start``, the function
``delay`` has been added by Celery to queue the execution of the function:

.. code-block:: python

    from invenio_workflows import start
    async_result = start.delay("MyWorkflow", data=10)

The delayed API returns a ``AsyncResult`` class where you check the status
of the task, and if you want to wait for the task to finish you can call
the ``AsyncResult.get`` function:

.. code-block:: python

    from invenio_workflow import WorkflowEngine
    eng_uuid = async_result.get()  # Will wait until task has completed

    engine = WorkflowEngine.from_uuid()
    engine.objects[0].data  # E.g. 30


.. warning::

    To use this functionality you need to make sure you are running a `Celery`_
    worker that will run the workflow in a separate process. Otherwise
    ``AsyncResult.get`` will never return.


Working with extra data
-----------------------

If you need to add some extra data to the
``WorkflowObject`` that is
not suitable to add to the ``obj.data`` attribute, you can make use if the
``obj.extra_data`` attribute.

The extra_data attribute is basically a normal dictionary that you can fill.
However, it might contain some additional information by default. This
information is used by the ``WorkflowObject``
to store some additional data related to the workflow execution and additional
data added by tasks.


.. _workflows-module: https://pypi.python.org/pypi/workflow/1.01
.. _Celery: http://www.celeryproject.org/
.. _RQ: http://python-rq.org/
