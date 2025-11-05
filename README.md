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

Then use the `%%iops` magic to profile I/O operations in a cell:

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

Use the `--histogram` flag to visualize I/O operation distributions:

```python
%%iops --histogram
# Your code here
with open('test.txt', 'w') as f:
    f.write('data' * 1000)
```

When enabled, two histogram charts are displayed alongside the results table:
1. **Operation Count Distribution**: Shows the count of I/O operations bucketed by bytes-per-operation (log scale)
2. **Total Bytes Distribution**: Shows the total bytes transferred bucketed by bytes-per-operation (log scale)

Both charts display separate lines for reads, writes, and all operations combined.

## Platform Support

- **Linux**: Uses `strace` for detailed per-operation tracking (fallback to `psutil` if `strace` unavailable)
  - With `strace`: Captures all system-level I/O operations
  - With `psutil`: Provides aggregate counts only (no histogram support)
- **macOS**: Uses `fs_usage` with privilege elevation (requires password prompt)
  - Captures all system-level I/O operations
- **Windows**: Uses Python-level I/O tracking for granular data
  - Captures Python `open()`/`read()`/`write()` operations
  - **Note**: May not capture I/O from native C extensions or libraries

## Requirements

- Python 3.8+
- IPython/Jupyter
- psutil
- matplotlib (for histogram visualization)
- numpy (for histogram visualization)
