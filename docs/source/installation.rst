.. _installation:

Installation
============

.. contents::
    :local:
    :depth: 1

Install from Conda
------------------
*Note: These installation instructions assume you have* `Anaconda <https://docs.anaconda.com/anaconda/install/>`_ *installed.*

.. warning::

   TODO: Prepare Conda package.

Install from GitHub
-------------------

*Note: These installation instructions assume you have* `Anaconda <https://docs.anaconda.com/anaconda/install/>`_ *installed.*

Check out code from the c3s magic wps GitHub repo and create a conda environment:

.. code-block:: sh

   $ git clone https://github.com/c3s-magic/c3s-magic-wps.git
   $ cd c3s-magic-wps
   $ conda env create -f environment.yml
   $ source activate c3s_magic_wps

Download ESMValTool add dependencies to your conda environment

.. code-block:: sh

   $ git clone -b version2_master https://github.com/ESMValGroup/ESMValTool.git ../esmvaltool
   $ cd ../esmvaltool
   $ conda env update -n c3s_magic_wps -f environment.yml

Install ESMValTool:

*Note: this step assumes you have* `Julia <https://julialang.org/downloads/>`_ *and* `Rscript <https://www.r-project.org/>`_ *installed*

.. code-block:: sh

   $ pip install -e
   $ Rscript esmvaltool/install/R/setup.R
   $ julia esmvaltool/install/Julia/setup.jl

Finally install the WPS:

.. code-block:: sh

   $ cd ../c3s-magic-wps
   $ python setup.py develop

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

*Note: Remember the process ID (PID) so you can stop the service with* ``kill PID``.

The deployed WPS service is by default available on:

http://localhost:5000/wps?service=WPS&version=1.0.0&request=GetCapabilities

You can find which process uses a given port using the following command (here for port 5000):

.. code-block:: sh

   $ netstat -nlp | grep :5000

Check the log files for errors:

.. code-block:: sh

   $ tail -f  pywps.log

Run c3s magic wps as Docker container
-------------------------------------

*Note: These installation instructions assume you have* `Docker <https://docs.docker.com/install/>`_ *installed.*

You can also choose to run c3s magic wps from a Docker container.

Download c3s-magic-wps, build the docker container and run it:  

.. code-block:: sh

   $ git clone https://github.com/c3s-magic/c3s-magic-wps.git
   $ cd c3s-magic-wps
   $ docker-compose build              
   $ docker-compose up

By default the WPS service should be available on port 5000:

 http://localhost:5000/wps?service=wps&request=GetCapabilities

Run docker exec to watch logs:

.. code-block:: sh

   $ docker ps     # find container name
   container_name
   $ docker exec container_name tail -f /opt/wps/pywps.log

Use docker-compose to stop the containers:

.. code-block:: sh

   $ docker-compose down

Use Ansible to deploy c3s magic wps on your System
--------------------------------------------------

Use the `Ansible playbook`_ for PyWPS to deploy c3s magic wps on your system.

.. _Ansible playbook: http://ansible-wps-playbook.readthedocs.io/en/latest/index.html
