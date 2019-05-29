.. _installation:

Installation
============

.. contents::
    :local:
    :depth: 1

Install from Conda
------------------

.. warning::

   TODO: Prepare Conda package.

Install from GitHub
-------------------

Check out code from the c3s magic wps GitHub repo and start the installation:

.. code-block:: sh

   $ git clone https://github.com/c3s-magic/c3s-magic-wps.git
   $ cd c3s-magic-wps
   $ conda env create -f environment.yml
   $ source activate c3s_magic_wps
   $ python setup.py develop

... or do it the lazy way
+++++++++++++++++++++++++

The previous installation instructions assume you have Anaconda installed.
We provide also a ``Makefile`` to run this installation without additional steps:

.. code-block:: sh

   $ git clone https://github.com/c3s-magic/c3s-magic-wps.git
   $ cd c3s-magic-wps
   $ make clean    # cleans up a previous Conda environment
   $ make install  # installs Conda if necessary and runs the above installation steps

Start c3s magic wps PyWPS service
---------------------------------

After successful installation you can start the service using the ``c3s_magic_wps`` command-line.

.. code-block:: sh

   $ c3s_magic_wps --help # show help
   $ c3s_magic_wps start  # start service with default configuration

   OR

   $ c3s_magic_wps start --daemon # start service as daemon
   loading configuration
   forked process id: 42

The deployed WPS service is by default available on:

http://localhost:5000/wps?service=WPS&version=1.0.0&request=GetCapabilities.

.. NOTE:: Remember the process ID (PID) so you can stop the service with ``kill PID``.

You can find which process uses a given port using the following command (here for port 5000):

.. code-block:: sh

   $ netstat -nlp | grep :5000


Check the log files for errors:

.. code-block:: sh

   $ tail -f  pywps.log

... or do it the lazy way
+++++++++++++++++++++++++

You can also use the ``Makefile`` to start and stop the service:

.. code-block:: sh

  $ make start
  $ make status
  $ tail -f pywps.log
  $ make stop


Run c3s magic wps as Docker container
-------------------------------------

You can also choose to run c3s magic wps as a Docker container.


.. warning::

  TODO: Describe Docker container support.

Get docker images using docker-compose::

    $ docker-compose pull

Start the demo with docker-compose::

    $ docker-compose up -d  # runs with -d in the background
    $ docker-compose logs -f  # check the logs if running in background

By default the WPS service should be available on port 5000::

    $ firefox "http://localhost:5000/wps?service=wps&request=GetCapabilities"

Run docker exec to watch logs::

    $ docker ps     # find container name
    copernicus-wps-demo_copernicus_1
    $ docker exec copernicus-wps-demo_copernicus_1 tail -f /opt/wps/pywps.log

Use docker-compose to stop the containers::

    $ docker-compose down


Use Ansible to deploy c3s magic wps on your System
--------------------------------------------------

Use the `Ansible playbook`_ for PyWPS to deploy c3s magic wps on your system.


.. _Ansible playbook: http://ansible-wps-playbook.readthedocs.io/en/latest/index.html
