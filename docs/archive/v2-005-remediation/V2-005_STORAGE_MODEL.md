# V2-005 Storage Model - Three-Layer Semantics

**Proposed Converged Specification** (H2-05)

**Status**: REVISED / INDEPENDENT_REVIEW_PENDING

---

## Three Layers

### Layer 1: Input Value
User-provided string as passed to API.

**Example**: `"  John　Doe  "`

**No processing**: Received as-is.

---

### Layer 2: Stored Display Value
Value persisted in EntityIdentity for display/serialization.

**Processing**: 
- Strip outer whitespace only: `.strip()`
- Result: `"John　Doe"`

**Purpose**: 
- Remove meaningless leading/trailing whitespace
- Preserve user's actual content (including U+3000)
- Used for display, JSON serialization

**Storage**:
- `canonical_name`: stored display value
- `aliases`: each stored as display value

---

### Layer 3: Lookup Key
Computed at query time only (never persisted).

**Processing** (via `normalize_for_lookup()`):
1. Strip outer whitespace
2. Delete all U+3000: `s.replace('　', '')`
3. Collapse ASCII spaces
4. ASCII lowercase

**Example**: `"John　Doe"` → `"johndoe"`

**Purpose**: 
- Enable flexible matching
- User queries normalized same way

**Not Stored**: Computed on-demand.

---

## Examples

| Input | Stored Display | Lookup Key |
|-------|---------------|------------|
| `"  张三  "` | `"张三"` | `"张三"` |
| `"Zhang  San"` | `"Zhang  San"` | `"zhang san"` |
| `"李　明"` | `"李　明"` | `"李明"` |
| `"  John　Doe  "` | `"John　Doe"` | `"johndoe"` |
| `"  老张　  "` | `"老张"` | `"老张"` |

**Note**: U+3000 (full-width space) is classified as whitespace by Python.
- **Edge U+3000**: Removed by `str.strip()` (e.g., `"  老张　  "` → `"老张"`)
- **Internal U+3000**: Preserved in stored display (e.g., `"李　明"` → `"李　明"`)
- **Lookup normalization**: All U+3000 deleted (e.g., `"李　明"` → `"李明"`)

---

## Contract Implications

### create_identity
```python
input: "  John  "
stored canonical_name: "John"
```

### add_alias
```python
input: "  老张　  "
stored in aliases: "老张"
# Note: strip() removes leading/trailing whitespace including U+3000
# Trailing U+3000 is edge whitespace, removed by strip()
```

### resolve_alias
```python
query: "老张　"
lookup_key: normalize_for_lookup("老张　") = "老张"
match against: normalize_for_lookup(stored_canonical_name)
             and normalize_for_lookup(each stored alias)
```

---

## Terminology

**Avoid**:
- ❌ "raw storage" (implies no processing)
- ❌ "stored after normalization" (implies lookup processing)

**Use**:
- ✅ "stored display value" (trimmed for display)
- ✅ "lookup key" (computed on query)

---

**Status**: Proposed converged semantics for V2-005, pending independent review approval
