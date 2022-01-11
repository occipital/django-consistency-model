#! /usr/bin/env python3
import sys

import pytest

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pytest_args = sys.argv[1:]
    else:
        pytest_args = []

    sys.exit(pytest.main(["-vv", "-s"] + pytest_args))
