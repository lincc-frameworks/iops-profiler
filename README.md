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

## Platform Support

- **Linux/Windows**: Uses `psutil` for per-process I/O tracking
- **macOS**: Uses `fs_usage` with privilege elevation (requires password prompt)

## Requirements

- Python 3.8+
- IPython/Jupyter
- psutil
