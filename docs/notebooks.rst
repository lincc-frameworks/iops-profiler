Example Notebooks
=================

These Jupyter notebooks demonstrate the key features of iops-profiler with practical, hands-on examples.

.. toctree::
   :maxdepth: 1
   :caption: Notebooks

   notebooks/basic_usage
   notebooks/histogram_visualization
   notebooks/advanced_usage

Running the Notebooks
---------------------

You can run these notebooks in several ways:

1. **View Online**: The notebooks are rendered as part of this documentation
2. **Download and Run Locally**: 
   
   .. code-block:: console

      >> git clone https://github.com/lincc-frameworks/iops-profiler.git
      >> cd iops-profiler/docs/notebooks
      >> jupyter notebook

3. **Try in Google Colab**: Upload the notebook files to Google Colab

Prerequisites
-------------

Before running the notebooks, make sure you have:

- Python 3.10 or higher
- Jupyter Notebook or JupyterLab installed
- iops-profiler installed (``pip install iops-profiler``)

The notebooks will handle creating and cleaning up temporary files automatically.

Notebook Descriptions
---------------------

Basic Usage
~~~~~~~~~~~

:doc:`notebooks/basic_usage`

Learn the fundamentals of iops-profiler:

- Loading the extension
- Using line magic (``%iops``) for single-line profiling
- Using cell magic (``%%iops``) for multi-line profiling
- Understanding the results table
- Comparing different I/O strategies
- Working with text and binary files

**Recommended for:** First-time users and those wanting a quick introduction.

Histogram Visualization
~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`notebooks/histogram_visualization`

Explore the histogram feature for visualizing I/O patterns:

- Enabling histogram mode with ``--histogram``
- Understanding operation count and bytes distributions
- Analyzing read vs. write patterns
- Optimizing buffer sizes based on histograms
- Working with mixed operation sizes
- Real-world examples (CSV files, etc.)

**Recommended for:** Users who want to understand and optimize I/O operation distributions.

**Note:** Histogram mode is available on Linux and macOS, but not Windows.

Advanced Usage
~~~~~~~~~~~~~~

:doc:`notebooks/advanced_usage`

Master advanced features and optimization techniques:

- Profiling data science workflows (JSON, pickle, etc.)
- Understanding and working with OS caching
- Forcing synchronous I/O with fsync
- Profiling multi-file operations
- Comparing chunked writing strategies
- Working with memory-mapped files
- Best practices for accurate measurements

**Recommended for:** Users who want to optimize I/O performance in production code.

Additional Resources
--------------------

After working through the notebooks, check out:

- :doc:`user_guide` for detailed feature documentation
- :doc:`platform_notes` for platform-specific tips
- :doc:`troubleshooting` if you encounter issues

You can also find more examples in the project's GitHub repository.
