# Source Code Organization

This document describes the organization of the iops-profiler source code after the refactoring completed on 2025-11-05.

## Overview

The original `iops_profiler.py` file (~940 lines) has been split into three focused modules to improve maintainability and clarity:

1. **`collector.py`** - Data collection and I/O measurement
2. **`display.py`** - Result formatting and visualization  
3. **`magic.py`** - IPython magic integration and orchestration

## Module Details

### collector.py (Data Collection)

**Purpose**: Contains all functionality related to collecting I/O statistics from the operating system.

**Key Components**:
- Constants:
  - `STRACE_ATTACH_DELAY`, `STRACE_CAPTURE_DELAY` - Timing constants for strace
  - `STRACE_IO_SYSCALLS` - List of I/O syscalls to trace

- Parsing functions:
  - `parse_fs_usage_line()` - Parse macOS fs_usage output
  - `parse_strace_line()` - Parse Linux strace output

- Helper functions:
  - `create_helper_script()` - Generate bash script for fs_usage
  - `launch_helper_via_osascript()` - Launch elevated processes on macOS

- Measurement functions:
  - `measure_macos_osascript()` - macOS I/O measurement using fs_usage
  - `measure_linux_strace()` - Linux I/O measurement using strace
  - `measure_linux_windows()` - Per-process measurement using psutil
  - `measure_systemwide_fallback()` - System-wide fallback measurement

**Dependencies**: `os`, `sys`, `time`, `re`, `subprocess`, `tempfile`, `psutil` (optional)

### display.py (Display & Visualization)

**Purpose**: Contains all functionality related to displaying results and generating visualizations.

**Key Components**:
- Environment detection:
  - `is_notebook_environment()` - Detect if running in Jupyter vs terminal

- Formatting:
  - `format_bytes()` - Convert bytes to human-readable format (KB, MB, GB, etc.)

- Display functions:
  - `display_results()` - Main entry point that routes to appropriate display method
  - `display_results_plain_text()` - Terminal/console text output
  - `display_results_html()` - Jupyter notebook HTML table output

- Visualization:
  - `generate_histograms()` - Create matplotlib histograms of I/O operation sizes

**Dependencies**: `matplotlib.pyplot`, `numpy`, `IPython.display` (HTML, display)

### magic.py (IPython Magic Glue)

**Purpose**: Contains the IPython magic command integration and orchestrates the data collection and display modules.

**Key Components**:
- Main class:
  - `IOPSProfiler` - IPython Magics class that implements the `%iops` and `%%iops` magic commands

- Magic command:
  - `iops()` - Line and cell magic handler (decorated with `@line_cell_magic`)

- Orchestration:
  - `_profile_code()` - Coordinates platform-specific measurement and result display
  - Compatibility wrapper methods (delegate to collector/display modules)

- Extension loading:
  - `load_ipython_extension()` - Register the magic with IPython
  - `unload_ipython_extension()` - Clean up on unload

**Dependencies**: `sys`, `re`, `IPython.core.magic`, and the `collector` and `display` modules

## Design Principles

### 1. Backward Compatibility
All existing function signatures and interfaces are preserved. The `IOPSProfiler` class maintains compatibility wrapper methods that delegate to the appropriate module functions. This ensures:
- No test changes required
- Existing code using the profiler continues to work
- Import statements remain the same (`from iops_profiler import IOPSProfiler`)

### 2. Clear Separation of Concerns
- **collector.py** knows nothing about display or IPython - it just collects data
- **display.py** knows nothing about how data is collected - it just formats and displays
- **magic.py** orchestrates both but contains minimal logic itself

### 3. Minimal Changes
The refactoring focused on moving code with minimal modifications:
- Function bodies were copied nearly verbatim
- Only necessary changes were made (e.g., adding parameters for shell context)
- Test suite passes without modifications (119/119 tests passing)

## File Structure

```
src/iops_profiler/
├── __init__.py          # Public API exports (IOPSProfiler, load/unload functions)
├── magic.py             # IPython magic integration (~250 lines)
├── collector.py         # Data collection functions (~550 lines)
├── display.py           # Display and visualization (~280 lines)
└── iops_profiler.py     # Original file (kept for reference, can be deleted)
```

## Usage Examples

The public API remains unchanged:

```python
# Load the extension
%load_ext iops_profiler

# Line magic
%iops open('test.txt', 'w').write('Hello')

# Cell magic
%%iops
with open('test.txt', 'w') as f:
    f.write('Hello World')

# With histogram
%%iops --histogram
with open('test.txt', 'w') as f:
    for i in range(1000):
        f.write(f'Line {i}\n')
```

## Testing

All 119 existing tests pass without modification:
- `tests/test_parsing.py` - Tests for parsing functions (still work via wrapper methods)
- `tests/test_display_modes.py` - Tests for display functions (still work via wrapper methods)
- `tests/test_histograms.py` - Tests for histogram generation (still work via wrapper methods)
- `tests/test_integration.py` - Integration tests (still work via wrapper methods)

## Future Improvements

Potential enhancements that could be made while maintaining this structure:

1. **Remove compatibility wrappers**: Once confident the refactoring is stable, tests could be updated to import functions directly from `collector` and `display` modules, and the wrapper methods in `IOPSProfiler` could be removed.

2. **Add type hints**: The modules could be enhanced with type annotations for better IDE support and documentation.

3. **Extract constants**: Constants could be moved to a separate `constants.py` module if they need to be shared more widely.

4. **Split collector further**: The `collector.py` module could potentially be split into platform-specific modules (`collector_linux.py`, `collector_macos.py`, etc.) if it grows larger.

## For Future AI Agents

If you need to modify this code:

1. **For data collection changes**: Modify `collector.py`
   - Add new measurement methods as standalone functions
   - Keep functions platform-agnostic where possible
   - Pass shell context as a parameter rather than using self.shell

2. **For display changes**: Modify `display.py`
   - Keep display functions independent of how data was collected
   - Maintain both plain text and HTML output support
   - Test in both Jupyter and terminal environments

3. **For magic command changes**: Modify `magic.py`
   - Keep orchestration logic in `_profile_code()` and `iops()`
   - Use the wrapper methods to delegate to collector/display
   - Platform detection should remain in magic.py

4. **Maintaining backward compatibility**: 
   - Keep the wrapper methods in `IOPSProfiler` class
   - Preserve the public API in `__init__.py`
   - Ensure all 119 tests continue to pass

## Migration Notes

The original `iops_profiler.py` file can be safely deleted after this refactoring, as all functionality has been moved to the new modules. However, it's kept temporarily for reference during the transition period.

The refactoring maintains 100% backward compatibility - no changes to tests, imports, or user-facing functionality were required.
