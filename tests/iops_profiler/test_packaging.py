import iops_profiler


def test_version():
    """Check to see that we can get the package version"""
    assert iops_profiler.__version__ is not None
