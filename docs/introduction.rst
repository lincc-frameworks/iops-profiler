Introduction
============

**iops-profiler** is a Jupyter IPython magic extension that allows you to measure I/O operations per second (IOPS) directly in your notebooks. It helps you understand and optimize the I/O performance of your code by providing detailed metrics about file operations.

What is IOPS?
-------------

IOPS (Input/Output Operations Per Second) is a performance measurement used to characterize storage devices and file system operations. It tells you how many read or write operations your code can perform per second.

IOPS are typically a fundamental limiting factor on HPC storage systems. This tool helps you debug performance problems where your code issues many IOPS to read relatively little data, which can significantly slow down your applications.

Key Features
------------

- **Easy to Use**: Simple magic commands (``%iops`` and ``%%iops``) that work like any other Jupyter magic
- **Comprehensive Metrics**: Track execution time, operation counts, bytes transferred, IOPS, and throughput
- **Visual Analysis**: Generate histograms to visualize I/O operation distributions
- **Cross-Platform**: Works on Linux, macOS, and Windows with platform-specific optimizations
- **No Code Changes**: Profile existing code without modification

Why Use iops-profiler?
----------------------

Understanding I/O performance is crucial for:

- **Optimizing Data Processing**: Identify bottlenecks in data-intensive workflows
- **Comparing Approaches**: Evaluate different methods for reading/writing data
- **Debugging Performance**: Pinpoint slow I/O operations in complex code
- **Educational Purposes**: Learn about I/O patterns and file system behavior

Quick Example
-------------

.. code-block:: python

   %load_ext iops_profiler

   # Profile a single line
   %iops open('test.txt', 'w').write('Hello World' * 1000)

   # Profile an entire cell
   %%iops
   with open('test.txt', 'w') as f:
       for i in range(1000):
           f.write(f'Line {i}\n')

The extension displays a comprehensive table with:

- **Time**: Total execution time
- **Read Ops**: Number of read operations
- **Write Ops**: Number of write operations  
- **Bytes Read**: Total bytes read from disk
- **Bytes Written**: Total bytes written to disk
- **Read IOPS**: Read operations per second
- **Write IOPS**: Write operations per second
- **Read Throughput**: Bytes per second for reads
- **Write Throughput**: Bytes per second for writes

Platform Support
----------------

Linux and Windows
~~~~~~~~~~~~~~~~~

Uses ``psutil`` library for accurate per-process I/O tracking. Works out of the box with no special permissions required.

macOS
~~~~~

Uses ``fs_usage`` system utility which requires privilege elevation. You will be prompted to enter your password when running the magic for the first time in a session.

Next Steps
----------

- Follow the :doc:`installation` guide to get started
- Read the :doc:`user_guide` for detailed usage instructions
- Check out the :doc:`notebooks/index` for practical examples
