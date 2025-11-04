# Publishing to PyPI

This document describes how to publish `iops-profiler` to PyPI.

## Prerequisites

1. Install build tools:
```bash
pip install --upgrade build twine
```

2. Set up PyPI account and API token at https://pypi.org/

## Building the Package

Build the distribution packages:

```bash
python -m build
```

This will create both source distribution (`.tar.gz`) and wheel (`.whl`) files in the `dist/` directory.

## Testing on TestPyPI (Recommended)

Before publishing to the main PyPI, test on TestPyPI:

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ iops-profiler
```

## Publishing to PyPI

Once you've verified everything works:

```bash
python -m twine upload dist/*
```

You'll be prompted for your PyPI credentials or API token.

## Installing from PyPI

After publishing, users can install with:

```bash
pip install iops-profiler
```

## Version Updates

Before releasing a new version:

1. Update version in `pyproject.toml`
2. Update version in `src/iops_profiler/__init__.py`
3. Create a git tag: `git tag v0.1.0`
4. Push tags: `git push --tags`
5. Build and publish as described above
