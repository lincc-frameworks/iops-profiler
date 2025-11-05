Installation
============

Requirements
------------

- Python 3.10 or higher
- IPython/Jupyter Notebook or JupyterLab
- Operating System: Linux, macOS, or Windows

Dependencies
~~~~~~~~~~~~

The following packages will be installed automatically:

- ``ipython``: For magic command integration
- ``psutil``: For I/O tracking on Linux and Windows
- ``matplotlib``: For histogram visualization
- ``numpy``: For data processing in histograms

Installing from PyPI
--------------------

The easiest way to install iops-profiler is from PyPI using pip:

.. code-block:: console

   >> pip install iops-profiler

Installing from Source
----------------------

To install the latest development version from GitHub:

.. code-block:: console

   >> git clone https://github.com/lincc-frameworks/iops-profiler.git
   >> cd iops-profiler
   >> pip install -e .

Development Installation
~~~~~~~~~~~~~~~~~~~~~~~~

If you want to contribute to iops-profiler, install with development dependencies:

.. code-block:: console

   >> pip install -e '.[dev]'
   >> pre-commit install

This installs additional tools for testing, linting, and pre-commit hooks.

Platform-Specific Setup
-----------------------

**Linux:** No additional setup required.

**macOS:** Each time you run ``%iops`` or ``%%iops``, you will be prompted for your password (``fs_usage`` requires elevated privileges).

**Windows:** No additional setup required.

For detailed platform information, see :doc:`platform_notes`.

Verifying Installation
----------------------

To verify that iops-profiler is installed correctly, start Python or a Jupyter notebook and run:

.. code-block:: python

   import iops_profiler
   print(iops_profiler.__version__)

Then load the extension:

.. code-block:: python

   %load_ext iops_profiler

If there are no errors, the installation is successful!

Quick Test
~~~~~~~~~~

Run a simple test to ensure everything works:

.. code-block:: python

   %load_ext iops_profiler
   
   %%iops
   with open('test.txt', 'w') as f:
       f.write('Hello, IOPS!')

You should see a results table with I/O metrics.

Next Steps
----------

Now that you have iops-profiler installed:

- Read the :doc:`user_guide` for detailed usage instructions  
- Try the :doc:`notebooks/index` for hands-on examples
- Learn about :doc:`platform_notes` for platform-specific tips
