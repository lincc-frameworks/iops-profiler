Troubleshooting
===============

This page covers common issues and their solutions.

Installation Issues
-------------------

"No module named 'iops_profiler'"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Python cannot find the iops_profiler module.

**Solutions:**

1. Verify the package is installed:

   .. code-block:: console

      >> pip list | grep iops

2. Check you're using the correct Python environment:

   .. code-block:: console

      >> which python
      >> which pip

3. In Jupyter, verify the kernel matches your environment:

   .. code-block:: python

      import sys
      print(sys.executable)

4. Reinstall the package:

   .. code-block:: console

      >> pip install --force-reinstall iops-profiler

Import Errors for Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Missing matplotlib, numpy, or other dependencies.

**Solution:**

.. code-block:: console

   >> pip install matplotlib numpy ipython psutil

If you still have issues, try reinstalling all dependencies:

.. code-block:: console

   >> pip install --upgrade iops-profiler[dev]

Extension Loading Issues
------------------------

"%load_ext iops_profiler" Fails
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Extension fails to load with an error.

**Check the error message:**

**"ModuleNotFoundError"**
   See installation issues above.

**"ImportError" mentioning psutil/matplotlib**
   Install the missing dependency:

   .. code-block:: console

      >> pip install psutil matplotlib numpy

**Other errors**
   Try restarting the kernel and reloading:

   .. code-block:: python

      %load_ext iops_profiler

Runtime Issues
--------------

No I/O Operations Detected
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** The profiler shows 0 operations even though your code performs I/O.

**Common causes:**

1. **Caching:** The OS cached your operations. Solution:

   .. code-block:: python

      # Close files properly
      with open('test.txt', 'w') as f:
          f.write('data')
      # File is automatically closed and flushed

2. **Buffering:** Python is buffering writes. Solution:

   .. code-block:: python

      # Flush explicitly
      f = open('test.txt', 'w')
      f.write('data')
      f.flush()  # Force write to disk
      f.close()

3. **Too fast:** Operations completed in < 1ms. Solution: Profile larger operations.

4. **Wrong platform:** Using Windows with very small operations. Solution: Test with larger files.

macOS-Specific Issues
---------------------

Password Prompt Doesn't Appear
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** No password dialog shows up on macOS.

**Solutions:**

1. Check System Preferences > Security & Privacy > Privacy > Accessibility
2. Ensure Terminal or Jupyter is allowed to control your computer
3. Try running the cell again - sometimes it takes a moment
4. Restart Jupyter and try again
5. If using JupyterLab, try classic Notebook

Permission Denied on macOS
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Error about lacking permissions to run fs_usage.

**Solutions:**

1. Make sure you entered the correct password
2. Your account needs admin privileges to use fs_usage
3. Try running from Terminal instead of an IDE

"Operation not permitted" on macOS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** fs_usage fails even with password.

**Solutions:**

1. Give Terminal/Jupyter "Full Disk Access" in System Preferences > Security & Privacy
2. Restart Terminal/Jupyter after granting access
3. Try with sudo in a terminal:

   .. code-block:: console

      >> sudo fs_usage -w -f filesystem

Linux-Specific Issues
---------------------

/proc/[pid]/io Not Available
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Cannot read I/O stats from /proc.

**Solutions:**

1. Verify you're on Linux 2.6.20+:

   .. code-block:: console

      >> uname -r

2. Check /proc is mounted:

   .. code-block:: console

      >> mount | grep proc

3. In containers, ensure /proc is accessible

Permission Issues in Containers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Cannot access I/O statistics in Docker/Kubernetes.

**Solutions:**

1. Don't use ``--privileged`` unless necessary; instead ensure /proc is mounted
2. Use ``--pid=host`` to access host process information (use cautiously)
3. Check container security policies

Windows-Specific Issues
-----------------------

Inaccurate Operation Counts
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Operation counts seem wrong or zero.

**Explanation:** Windows aggregates I/O operations differently than Linux. This is expected behavior.

**Solutions:**

1. Focus on bytes read/written and throughput rather than operation counts
2. Use relative comparisons (strategy A vs B) rather than absolute numbers
3. For precise measurements, use Linux

Performance Issues
------------------

Profiling Takes Too Long
~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** The %%iops cell runs much slower than without profiling.

**Expected overhead:** 1-5% in most cases.

**If overhead is higher:**

1. **Histogram mode:** Adds overhead. Try without ``--histogram`` flag
2. **macOS:** Privilege elevation adds overhead. Expected behavior
3. **Many small operations:** Tracking overhead becomes significant

Histogram Issues
----------------

Histogram Not Generated
~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Using ``--histogram`` flag but no histogram appears.

**Causes:**

1. **Platform:** Histograms not supported on Windows
2. **No operations:** Your code didn't perform measurable I/O
3. **matplotlib missing:** Install with ``pip install matplotlib``

Empty or Sparse Histograms
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Histogram has very few bars or looks empty.

**Solutions:**

1. Perform more I/O operations with varied sizes:

   .. code-block:: python

      %%iops --histogram
      import tempfile
      # Create multiple files of different sizes
      for i in range(10):
          with open(f'/tmp/test_{i}.txt', 'w') as f:
              f.write('x' * (1024 * (i + 1)))

2. Use operations that create diverse I/O patterns

Results Interpretation Issues
------------------------------

Unexpected Results
~~~~~~~~~~~~~~~~~~

**Problem:** Results don't match expectations.

**Common causes:**

1. **OS Caching:**

   .. code-block:: python

      # First run - actual I/O
      %%iops
      with open('test.txt', 'r') as f:
          data = f.read()
      
      # Second run - might be cached!
      %%iops  # May show 0 reads
      with open('test.txt', 'r') as f:
          data = f.read()

2. **Buffering:** Python/OS buffers hide true I/O patterns

3. **Async I/O:** Some libraries use async I/O that's hard to measure

Inconsistent Results Between Runs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Same code gives different results each time.

**This is normal!** I/O performance varies based on:

- System load
- Cache state
- Background processes
- Disk state and fragmentation

**Best practices:**

1. Run multiple times and average results
2. Warm up the system with a practice run
3. Close other applications
4. Use relative comparisons

Very High IOPS Numbers
~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** IOPS numbers seem unrealistically high.

**Causes:**

1. **Cached operations:** Data came from cache, not disk
2. **Buffered writes:** OS buffering operations
3. **Fast storage:** Modern SSDs can achieve 100k+ IOPS

**Verify:**

.. code-block:: python

   %%iops
   import os
   # Force sync to disk
   f = open('test.txt', 'w')
   f.write('data' * 10000)
   f.flush()
   os.fsync(f.fileno())
   f.close()

Very Low or Zero Throughput
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem:** Throughput shows 0 or very low values.

**Causes:**

1. No actual bytes transferred (operations were metadata only)
2. Operations too fast to measure accurately
3. All operations were cached

Getting More Help
-----------------

If none of these solutions work:

1. **Check GitHub Issues:** `github.com/lincc-frameworks/iops-profiler/issues <https://github.com/lincc-frameworks/iops-profiler/issues>`_

2. **Enable Debug Output:** Add this to your notebook:

   .. code-block:: python

      import logging
      logging.basicConfig(level=logging.DEBUG)

3. **Gather Information:** When reporting issues, include:

   - Python version: ``python --version``
   - OS and version: ``uname -a`` (Linux/Mac) or ``ver`` (Windows)
   - Package version: ``pip show iops-profiler``
   - Full error message and traceback
   - Minimal code to reproduce the issue

4. **File an Issue:** `Create a new issue <https://github.com/lincc-frameworks/iops-profiler/issues/new>`_ with the information above

Next Steps
----------

- Return to :doc:`user_guide` for usage instructions
- Review :doc:`platform_notes` for platform-specific information
- Try the :doc:`notebooks/index` examples
