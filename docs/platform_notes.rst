Platform-Specific Notes
=======================

iops-profiler uses different measurement techniques on each platform. This page provides platform-specific details beyond the basic setup covered in :doc:`installation`.

Linux
-----

**Measurement:** Uses ``psutil`` to read ``/proc/[pid]/io`` for low-overhead, accurate per-process I/O statistics.

**Key Features:**

- No special permissions required
- Histogram mode available when ``strace`` is installed
- Best for CI/CD and automated workflows

**Considerations:**

- **Caching:** Linux's page cache may cause repeated reads to show zero I/O. Clear caches with ``sync`` or ``/proc/sys/vm/drop_caches`` if needed.
- **Containers:** Ensure ``/proc/[pid]/io`` is accessible (most containers allow this by default).

macOS
-----

**Measurement:** Uses ``fs_usage`` system utility, which requires elevated privileges via password prompt.

**Key Features:**

- Password prompt appears each time you run ``%iops`` or ``%%iops``
- Histogram mode provides detailed operation distributions
- The extension never stores credentials

**Considerations:**

- **Automation:** Password prompts make macOS unsuitable for CI/CD. Use Linux or Windows instead.
- **Overhead:** Privilege elevation adds some performance overhead.

Windows
-------

**Measurement:** Uses ``psutil`` with Windows performance counters.

**Key Features:**

- No special permissions required
- No password prompts

**Limitations:**

- **Operation counts:** Windows aggregates I/O differently than Unix systems. Counts are approximate and may not match 1:1 with read/write calls.
- **Histogram mode:** Not available (Windows counters lack operation-level detail).

Platform Comparison
-------------------

.. list-table::
   :header-rows: 1
   :widths: 40 20 20 20

   * - Feature
     - Linux
     - macOS
     - Windows
   * - Accuracy
     - High
     - High
     - Moderate
   * - Histogram mode
     - Yes (strace)
     - Yes (fs_usage)
     - No
   * - Special permissions
     - No
     - Yes (password)
     - No
   * - CI/CD suitable
     - Yes
     - No
     - Yes

Recommendations
---------------

- **Production/Benchmarking:** Use Linux for most accurate results
- **Development:** Any platform works; use your development machine's OS
- **Automated Testing:** Linux or Windows (avoid macOS password prompts)
- **Learning:** Any platform based on user familiarity

See :doc:`user_guide` for usage details and :doc:`troubleshooting` for platform-specific issues.
