#!/bin/bash
# halt script on error
set -e
# Check for Style Code Violations
doc8 --max-line-length 100 --ignore D000 --ignore-path build --quiet .
