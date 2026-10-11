#!/usr/bin/env python3
"""Check raw unfiltered validation errors from test fixture."""

import sys
from pathlib import Path

# Add plan/scripts to path
sys.path.insert(0, str(Path(__file__).parent / "plan/scripts"))

from test_governance import GovernanceTests
import validate_plan as validator
from governance_checks import evidence_checks
from execution_checks import execution_checks

# Create test instance and set up fixture
test = GovernanceTests()
test.setUp()

# Get raw unfiltered errors (bypass the filtered errors() method)
raw_errors = (
    validator.validate_objects(test.data)
    + evidence_checks(test.data, test.plan)
    + execution_checks(test.data, test.plan)
)

print(f'Total raw errors: {len(raw_errors)}')
print()

if raw_errors:
    for i, e in enumerate(raw_errors, 1):
        print(f'{i}. {e}')
else:
    print('No errors found - fixture is clean!')
