# H1-03: EntityId Validator Executable Check

**Test**: Verify fullmatch() rejects trailing newline

```python
import re

ENTITY_ID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
)

def is_valid_entity_id(s: str) -> bool:
    """Validate EntityId using fullmatch (whole-string)."""
    return ENTITY_ID_PATTERN.fullmatch(s) is not None

# Test cases
tests = [
    ("550e8400-e29b-41d4-a716-446655440000", True, "Valid UUID v4"),
    ("550e8400-e29b-41d4-a716-446655440000\n", False, "Trailing newline"),
    ("\n550e8400-e29b-41d4-a716-446655440000", False, "Leading newline"),
    (" 550e8400-e29b-41d4-a716-446655440000", False, "Leading space"),
    ("550e8400-e29b-41d4-a716-446655440000 ", False, "Trailing space"),
    ("550E8400-E29B-41D4-A716-446655440000", False, "Uppercase"),
    ("550e8400-e29b-11d4-a716-446655440000", False, "Wrong version (v1)"),
    ("550e8400-e29b-41d4-f716-446655440000", False, "Wrong variant"),
    ("01HQZQZQZQZQZQZQZQZQZQ", False, "ULID format"),
    ("abc", False, "Invalid format"),
    ("", False, "Empty string"),
]

print("=== EntityId Validation Tests ===\n")
all_pass = True
for input_val, expected, description in tests:
    result = is_valid_entity_id(input_val)
    status = "✅" if result == expected else "❌"
    if result != expected:
        all_pass = False
    print(f"{status} {description}")
    print(f"   Input: {repr(input_val)}")
    print(f"   Result: {result}, Expected: {expected}")
    print()

print(f"Overall: {'✅ ALL PASS' if all_pass else '❌ SOME FAILED'}")
```

## Execution Result

```
=== EntityId Validation Tests ===

✅ Valid UUID v4
   Input: '550e8400-e29b-41d4-a716-446655440000'
   Result: True, Expected: True

✅ Trailing newline
   Input: '550e8400-e29b-41d4-a716-446655440000\n'
   Result: False, Expected: False

✅ Leading newline
   Input: '\n550e8400-e29b-41d4-a716-446655440000'
   Result: False, Expected: False

✅ Leading space
   Input: ' 550e8400-e29b-41d4-a716-446655440000'
   Result: False, Expected: False

✅ Trailing space
   Input: '550e8400-e29b-41d4-a716-446655440000 '
   Result: False, Expected: False

✅ Uppercase
   Input: '550E8400-E29B-41D4-A716-446655440000'
   Result: False, Expected: False

✅ Wrong version (v1)
   Input: '550e8400-e29b-11d4-a716-446655440000'
   Result: False, Expected: False

✅ Wrong variant
   Input: '550e8400-e29b-41d4-f716-446655440000'
   Result: False, Expected: False

✅ ULID format
   Input: '01HQZQZQZQZQZQZQZQZQZQ'
   Result: False, Expected: False

✅ Invalid format
   Input: 'abc'
   Result: False, Expected: False

✅ Empty string
   Input: ''
   Result: False, Expected: False

Overall: ✅ ALL PASS
```

**Status**: ✅ H1-03 VERIFIED
