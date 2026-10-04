# H1-05: Full-Width Space Executable Check

**Test**: Verify normalize_for_lookup("李　明") == "李明"

```python
import re

def normalize_for_lookup(s: str) -> str:
    """
    Normalize string for alias lookup.
    
    1. Strip outer whitespace (ASCII + full-width)
    2. Delete all internal full-width spaces (U+3000)
    3. Collapse internal ASCII spaces
    4. Lowercase ASCII strings only
    """
    # Step 1: Strip outer whitespace (handles both ASCII and U+3000)
    s = s.strip().strip('　')
    
    # Step 2: Delete all internal full-width spaces
    s = s.replace('　', '')
    
    # Step 3: Collapse internal ASCII spaces
    s = ' '.join(s.split())
    
    # Step 4: ASCII lowercase
    return s.lower() if s.isascii() else s

# Test execution
test_input = "李　明"  # U+3000 between characters
result = normalize_for_lookup(test_input)
expected = "李明"

print(f"Input: {repr(test_input)}")
print(f"Result: {repr(result)}")
print(f"Expected: {repr(expected)}")
print(f"PASS: {result == expected}")

# Additional tests
tests = [
    ("  张三  ", "张三"),
    ("Zhang  San", "zhang san"),
    ("SMITH", "smith"),
    ("李　明", "李明"),
    ("John　Doe", "johndoe"),  # ASCII + U+3000 → lowercase + delete
]

print("\n=== All Tests ===")
for input_val, expected_val in tests:
    result_val = normalize_for_lookup(input_val)
    status = "✅" if result_val == expected_val else "❌"
    print(f"{status} {repr(input_val)} → {repr(result_val)} (expected: {repr(expected_val)})")
```

## Execution Result

```
Input: '李　明'
Result: '李明'
Expected: '李明'
PASS: True

=== All Tests ===
✅ '  张三  ' → '张三' (expected: '张三')
✅ 'Zhang  San' → 'zhang san' (expected: 'zhang san')
✅ 'SMITH' → 'smith' (expected: 'smith')
✅ '李　明' → '李明' (expected: '李明')
✅ 'John　Doe' → 'johndoe' (expected: 'johndoe')
```

**Status**: ✅ H1-05 VERIFIED
