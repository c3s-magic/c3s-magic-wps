.. _processes:

Processes
=========

.. contents::
    :local:
    :depth: 1


Data Availability
-----------------

A special *Meta* process in the Magic WPS is available to automatically determine the available cmip5 model data by reading the available files from the data folder. As CMIP5 data is structured according to the DRS this can be done automatically. The format used to pass this information is the json output of the `linux tree command`_. If configured correctly, the WPS processes will automatically find the data

.. code-block:: bash

        tree -J -l -d -L 8 /group_workspaces/jasmin2/cp4cds1/data/c3s-cmip5

.. _linux tree command: http://mama.indstate.edu/users/ice/tree/

Metrics
-------

This is a list of metrics available as processes in the MAGIC WPS.

The list of Models, Experiments, and Ensembles is created automatically when the server is started, and shown as "None" here.

.. automodule:: c3s_magic_wps.processes
   :members:
   :undoc-members:
   :show-inheritance:
