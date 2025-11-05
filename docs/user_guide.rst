User Guide
==========

This guide covers all the features of iops-profiler and how to use them effectively.

Loading the Extension
---------------------

Before using any iops-profiler magic commands, you must load the extension in your notebook:

.. code-block:: python

   %load_ext iops_profiler

You only need to do this once per notebook session. The extension will be available for the rest of your session.

Basic Usage
-----------

Line Magic (``%iops``)
~~~~~~~~~~~~~~~~~~~~~~

Use ``%iops`` to profile a single line of code:

.. code-block:: python

   %iops open('test.txt', 'w').write('Hello World' * 1000)

This is perfect for quick measurements of one-line operations.

Cell Magic (``%%iops``)
~~~~~~~~~~~~~~~~~~~~~~~

Use ``%%iops`` to profile an entire cell of code:

.. code-block:: python

   %%iops
   # Your code here
   with open('test.txt', 'w') as f:
       for i in range(1000):
           f.write(f'Line {i}\n')

This is ideal for profiling code blocks, loops, and complex operations.

Understanding the Results
-------------------------

When you run a profiled cell, you'll see a results table with these metrics:

Basic Metrics
~~~~~~~~~~~~~

**Time (seconds)**
   Total execution time of your code

**Read Ops**
   Number of read operations performed

**Write Ops**
   Number of write operations performed

**Bytes Read**
   Total bytes read from disk

**Bytes Written**
   Total bytes written to disk

Performance Metrics
~~~~~~~~~~~~~~~~~~~

**Read IOPS**
   Read operations per second (Read Ops / Time)

**Write IOPS**
   Write operations per second (Write Ops / Time)

**Read Throughput (bytes/sec)**
   Bytes read per second (Bytes Read / Time)

**Write Throughput (bytes/sec)**
   Bytes written per second (Bytes Written / Time)

Advanced Features
-----------------

Histogram Visualization
~~~~~~~~~~~~~~~~~~~~~~~

Use the ``--histogram`` flag to visualize I/O operation distributions:

.. code-block:: python

   %%iops --histogram
   import tempfile
   import os
   
   # Create files with different sizes
   test_dir = tempfile.mkdtemp()
   for i in range(5):
       with open(os.path.join(test_dir, f'file_{i}.txt'), 'w') as f:
           f.write('x' * (1024 * (i + 1)))  # Varying sizes

This generates two histogram charts:

1. **Operation Count Distribution**: Shows how many I/O operations fall into each size bucket
2. **Total Bytes Distribution**: Shows the total bytes transferred in each size bucket

Both charts use logarithmic scale for the x-axis and display separate lines for reads, writes, and combined operations.

When to Use Histograms
^^^^^^^^^^^^^^^^^^^^^^

Histograms are useful when:

- You want to understand the distribution of I/O operation sizes
- Your code performs many operations of varying sizes
- You're optimizing buffer sizes or chunk sizes
- You're comparing different I/O strategies

**Note:** Histogram mode is available when using ``strace`` on Linux and ``fs_usage`` on macOS. These tools provide operation-level detail needed for histogram generation. If strace is not available on Linux, the extension falls back to psutil (without histogram support). Histogram collection adds some overhead due to detailed tracking.

Practical Examples
------------------

Example 1: Comparing Write Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Strategy 1: Many small writes
   %%iops
   with open('test1.txt', 'w') as f:
       for i in range(10000):
           f.write('a')
   
   # Strategy 2: Fewer large writes
   %%iops
   with open('test2.txt', 'w') as f:
       data = 'a' * 10000
       f.write(data)

Compare the IOPS and throughput to see which is more efficient.

Example 2: Buffer Size Optimization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   %%iops --histogram
   # Test different buffer sizes
   with open('large_file.bin', 'wb') as f:
       data = b'x' * 1024 * 1024  # 1 MB
       f.write(data)

Use the histogram to see how the system batches your writes.

Example 3: Read vs Write Performance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   %%iops
   # Write test data
   with open('data.txt', 'w') as f:
       f.write('data' * 100000)
   
   # Read it back
   with open('data.txt', 'r') as f:
       content = f.read()

Compare read and write IOPS for your specific use case.

Best Practices
--------------

1. **Warm Up**: Run your code once before profiling to account for caching and initialization
2. **Multiple Runs**: Profile the same operation multiple times to account for variability
3. **Clean Environment**: Clear caches and close files between runs when testing
4. **Realistic Data**: Use data sizes similar to your production workload
5. **Avoid Timing Noise**: Don't profile in the same cell as print statements or other I/O

Limitations and Caveats
-----------------------

Measurement Accuracy
~~~~~~~~~~~~~~~~~~~~

- Very fast operations (< 1 millisecond) may not be measured accurately
- Operating system caching can affect results significantly
- Network file systems (NFS, SMBFS) may report inaccurate I/O counts

Platform Differences
~~~~~~~~~~~~~~~~~~~~

- macOS requires password input for privilege elevation
- Windows may not track all I/O operations as precisely as Linux
- Different platforms may report operations differently (e.g., buffering behavior)

Overhead
~~~~~~~~

- The profiling itself adds some overhead (typically 1-5%)
- Histogram mode adds additional overhead due to detailed tracking
- Very high frequency operations may be impacted more

Next Steps
----------

- See :doc:`notebooks/index` for detailed examples
- Read :doc:`platform_notes` for platform-specific information
- Check :doc:`troubleshooting` if you encounter issues
