Platform-Specific Notes
=======================

iops-profiler works across Linux, macOS, and Windows, but uses different measurement techniques on each platform. This page explains the differences and platform-specific considerations.

Linux
-----

Measurement Method
~~~~~~~~~~~~~~~~~~

On Linux, iops-profiler uses the ``psutil`` library to access per-process I/O statistics from ``/proc/[pid]/io``. This provides accurate, low-overhead measurements.

Advantages
~~~~~~~~~~

- **No special permissions required**: Works for any user
- **Low overhead**: Minimal impact on performance
- **Accurate**: Direct kernel statistics
- **Detailed metrics**: Includes both logical and physical I/O

Supported Metrics
~~~~~~~~~~~~~~~~~

All metrics are fully supported:
- Read/write operation counts
- Bytes read/written  
- IOPS calculations
- Throughput calculations
- Histogram mode (when using strace backend)

Best Use Cases
~~~~~~~~~~~~~~

Linux is the recommended platform for:
- Automated testing and CI/CD pipelines
- Production-like performance analysis
- Benchmarking and comparison studies
- Educational environments

Considerations
~~~~~~~~~~~~~~

**Caching Effects**
   Linux's page cache aggressively caches file data. Repeated reads may show zero I/O operations because data comes from cache. Use ``sync`` or ``/proc/sys/vm/drop_caches`` to clear caches between tests if needed.

**Container Environments**
   When running in containers (Docker, Kubernetes), ensure the container has access to ``/proc/[pid]/io``. Most containers provide this by default.

macOS
-----

Measurement Method
~~~~~~~~~~~~~~~~~~

On macOS, iops-profiler uses the ``fs_usage`` system utility, which requires elevated privileges. The extension uses AppleScript to prompt for your password via the system security dialog.

Advantages
~~~~~~~~~~

- **System-wide visibility**: Can track operations across processes if needed
- **Detailed operation logs**: When using histogram mode, provides comprehensive data
- **Native tool**: Uses built-in macOS utilities

Supported Metrics
~~~~~~~~~~~~~~~~~

All metrics are supported, but with some caveats:
- Operation counts and bytes are accurate
- Histogram mode provides detailed distributions
- Some overhead from privilege elevation process

Privilege Elevation
~~~~~~~~~~~~~~~~~~~

The first time you run ``%iops`` or ``%%iops`` in a notebook session, you'll see a system password prompt. This is necessary because ``fs_usage`` requires root privileges.

**How it Works:**

1. Extension requests elevated privileges via AppleScript
2. macOS shows a standard system authentication dialog
3. You enter your password
4. The elevated process runs for the duration of the profiling
5. Privileges are released immediately after

**Security Notes:**

- The extension never stores your password
- Each notebook session requires re-authentication
- Only the ``fs_usage`` command runs with elevated privileges
- Your code still runs with your normal user privileges

Best Use Cases
~~~~~~~~~~~~~~

macOS is suitable for:
- Interactive development and exploration
- Local testing and debugging
- Learning and education
- Small-scale analysis

Considerations
~~~~~~~~~~~~~~

**Password Prompts**
   If you're running many profile operations, the repeated password prompts may become tedious. Consider using Linux or Windows for automated workflows.

**Automation Limitations**
   The password prompt makes it difficult to fully automate profiling on macOS. For CI/CD, use Linux.

**Overhead**
   The privilege elevation and ``fs_usage`` tool add some overhead compared to Linux's ``psutil`` approach.

**fs_usage Behavior**
   The tool may show more operations than expected due to system-level buffering and caching behaviors.

Windows
-------

Measurement Method
~~~~~~~~~~~~~~~~~~

On Windows, iops-profiler uses the ``psutil`` library to access Windows performance counters for I/O operations.

Advantages
~~~~~~~~~~

- **No special permissions required**: Works for standard users
- **Low overhead**: Native performance counters
- **Easy to use**: No password prompts or elevated privileges

Supported Metrics
~~~~~~~~~~~~~~~~~

Most metrics are supported:
- Read/write operation counts (approximate)
- Bytes read/written
- IOPS calculations  
- Throughput calculations

Limitations
~~~~~~~~~~~

**Operation Counting**
   Windows reports I/O operations differently than Unix-like systems. Operation counts may be:
   - Aggregated or batched by the OS
   - Less granular than on Linux
   - Not always 1:1 with actual read/write calls

**Fast Operations**
   Very fast operations (< 1ms) may not register as distinct I/O events in the performance counters.

**Histogram Mode**
   Histogram mode is not available on Windows because Windows performance counters don't provide operation-level detail.

Best Use Cases
~~~~~~~~~~~~~~

Windows is suitable for:
- Development on Windows machines
- Rough performance analysis
- Relative comparisons (e.g., strategy A vs strategy B)
- Educational purposes

Considerations
~~~~~~~~~~~~~~

**Precision**
   For precise measurements and detailed analysis, consider using Linux. Windows is better suited for relative comparisons rather than absolute measurements.

**Caching**
   Like Linux, Windows caches file data aggressively. Flush caches between tests for consistent results.

Cross-Platform Comparison
-------------------------

Here's a quick comparison of platform capabilities:

.. list-table::
   :header-rows: 1
   :widths: 30 20 20 20

   * - Feature
     - Linux
     - macOS
     - Windows
   * - Operation counts
     - ✓ Accurate
     - ✓ Accurate
     - ≈ Approximate
   * - Bytes read/written
     - ✓ Accurate
     - ✓ Accurate
     - ✓ Accurate
   * - IOPS calculation
     - ✓ Full support
     - ✓ Full support
     - ✓ Full support
   * - Histogram mode
     - ✓ Available
     - ✓ Available
     - ✗ Not available
   * - Privilege required
     - ✗ No
     - ✓ Yes (password)
     - ✗ No
   * - Overhead
     - Low
     - Medium
     - Low
   * - CI/CD friendly
     - ✓ Yes
     - ✗ No (password)
     - ✓ Yes

Recommendations
---------------

For Different Use Cases
~~~~~~~~~~~~~~~~~~~~~~~

**Production Analysis**
   Use Linux for the most accurate measurements and lowest overhead.

**Development**
   Any platform works fine. Use your development machine's OS.

**Automated Testing**
   Use Linux or Windows. Avoid macOS due to password prompts.

**Teaching/Learning**
   Any platform works. Choose based on student familiarity.

**Benchmarking**
   Linux provides the most reliable and reproducible results.

Handling Platform Differences in Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Your code doesn't need to change based on platform - the extension handles platform detection automatically. However, you may want to adjust expectations:

.. code-block:: python

   import sys
   
   %load_ext iops_profiler
   
   if sys.platform == 'darwin':
       print("Note: You'll be prompted for your password on macOS")
   
   %%iops
   # Your profiling code here

Next Steps
----------

- Return to :doc:`user_guide` for usage instructions
- Try :doc:`notebooks/index` for practical examples
- See :doc:`troubleshooting` for platform-specific issues
