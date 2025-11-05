# iops-profiler

A Jupyter IPython magic extension for measuring I/O operations per second (IOPS) in your code.

## Installation

You can install `iops-profiler` directly from PyPI (once published):

```bash
pip install iops-profiler
```

Or install from source:

```bash
git clone https://github.com/lincc-frameworks/iops-profiler.git
cd iops-profiler
pip install -e .
```

## Usage

Load the extension in your Jupyter notebook:

```python
%load_ext iops_profiler
```

### Line Magic Mode

Use the `%iops` line magic to profile a single line of code:

```python
%iops open('test.txt', 'w').write('Hello World' * 1000)
```

### Cell Magic Mode

Use the `%%iops` cell magic to profile I/O operations in an entire cell:

```python
%%iops
# Your code here
with open('test.txt', 'w') as f:
    f.write('Hello World' * 1000)
```

The extension will display a table showing:
- Execution time
- Read/write operation counts
- Bytes read/written
- IOPS (operations per second)
- Throughput (bytes per second)

### Histogram Visualization

Use the `--histogram` flag to visualize I/O operation distributions (available for `strace` and `fs_usage` measurement modes):

**Example - Analyzing I/O patterns with multiple file sizes:**
```python
%%iops --histogram
import tempfile
import os
import shutil

# Create test files with different sizes
test_dir = tempfile.mkdtemp()

try:
    # Write files of various sizes to create diverse write operations
    # Small writes (few KB)
    for i in range(5):
        with open(os.path.join(test_dir, f'small_{i}.txt'), 'w') as f:
            f.write('x' * 1024)  # 1 KB
    
    # Medium writes (tens of KB)
    for i in range(3):
        with open(os.path.join(test_dir, f'medium_{i}.txt'), 'w') as f:
            f.write('y' * (10 * 1024))  # 10 KB
    
    # Large writes (hundreds of KB)
    for i in range(2):
        with open(os.path.join(test_dir, f'large_{i}.txt'), 'w') as f:
            f.write('z' * (100 * 1024))  # 100 KB
    
    # Now read back the files to create diverse read operations
    # Small reads
    for i in range(5):
        with open(os.path.join(test_dir, f'small_{i}.txt'), 'r') as f:
            _ = f.read()
    
    # Medium reads
    for i in range(3):
        with open(os.path.join(test_dir, f'medium_{i}.txt'), 'r') as f:
            _ = f.read()
    
    # Large reads
    for i in range(2):
        with open(os.path.join(test_dir, f'large_{i}.txt'), 'r') as f:
            _ = f.read()

finally:
    # Cleanup
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
```

This example generates a rich distribution of I/O operations across multiple size ranges, producing histograms like:

![Histogram Example](images/histogram_example.png)

When enabled, two histogram charts are displayed alongside the results table:
1. **Operation Count Distribution**: Shows the count of I/O operations bucketed by bytes-per-operation (log scale)
2. **Total Bytes Distribution**: Shows the total bytes transferred bucketed by bytes-per-operation (log scale)

Both charts display separate lines for reads, writes, and all operations combined, making it easy to identify patterns in your code's I/O behavior.

## Platform Support

- **Linux/Windows**: Uses `psutil` for per-process I/O tracking
- **macOS**: Uses `fs_usage` with privilege elevation (requires password prompt)

## Requirements

- Python 3.10+
- IPython/Jupyter
- psutil
- matplotlib (for histogram visualization)
- numpy (for histogram visualization)

## Dev Guide - Getting Started

Before installing any dependencies or writing code, it's a great idea to create a
virtual environment. LINCC-Frameworks engineers primarily use `conda` to manage virtual
environments. If you have conda installed locally, you can run the following to
create and activate a new environment.

```bash
conda create -n <env_name> python=3.10
conda activate <env_name>
```

Once you have created a new environment, you can install this project for local
development using the following commands:

```bash
pip install -e '.[dev]'
pre-commit install
```

Notes:
1. The install command will install the package in editable mode with all development dependencies
2. `pre-commit install` will initialize pre-commit for this local repository, so
   that a set of tests will be run prior to completing a local commit. For more
   information, see the Python Project Template documentation on 
   [pre-commit](https://lincc-ppt.readthedocs.io/en/latest/practices/precommit.html)
