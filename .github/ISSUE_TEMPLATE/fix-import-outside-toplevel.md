---
name: Fix Import Outside Toplevel
about: Refactor imports from inside functions to module level
title: "[REFACTOR] Fix Pylint C0415 import-outside-toplevel violations"
labels: refactoring, code-quality, pylint
assignees: ''
---

## 🎯 Objective

Fix all Pylint C0415 (`import-outside-toplevel`) violations across the codebase by moving imports from inside functions/methods to the top of each module.

---

## 📋 Problem Description

**Pylint Rule:** `C0415 (import-outside-toplevel)`

> Import should be done at module level, not inside functions or methods.

### Why this matters:
1. **Performance**: Imports inside functions run on every call
2. **Readability**: All dependencies visible at top of file
3. **Maintenance**: Easier to track what a module depends on
4. **IDE Support**: Better autocomplete and static analysis

---

## 🔍 STEP 1: Find All Violations

Run this command to identify all violations:

```bash
pylint src/ --disable=all --enable=C0415 --output-format=text
```

Or use grep to find inline imports:

```bash
# Find imports inside functions (indented imports)
grep -rn "^    import \|^        import \|^    from .* import\|^        from .* import" src/ --include="*.py"
```

---

## 🔧 STEP 2: Fix Pattern

### Before (Wrong):
```python
class MyClass:
    def my_method(self):
        from src.utils.config_manager import ConfigManager  # ❌ Inside method
        config = ConfigManager.get_config()
```

### After (Correct):
```python
from src.utils.config_manager import ConfigManager  # ✅ At module level

class MyClass:
    def my_method(self):
        config = ConfigManager.get_config()
```

---

## ⚠️ STEP 3: Handle Circular Imports

Some imports are inside functions to avoid circular imports. For these cases:

### Option A: Restructure to break the cycle
```python
# Extract shared code to a new module that both can import
```

### Option B: Use TYPE_CHECKING guard (for type hints only)
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.some_module import SomeClass  # Only imported during type checking
```

### Option C: Keep inside function with pylint disable (last resort)
```python
def my_function():
    # pylint: disable=import-outside-toplevel
    from src.module import Something  # Justified: circular import prevention
    # pylint: enable=import-outside-toplevel
```

---

## 📁 STEP 4: Known Files to Check

Based on common patterns, check these files:

| File                          | Likely Issue                         |
| ----------------------------- | ------------------------------------ |
| `src/mt5_connector.py`        | ConfigManager import inside methods  |
| `src/core/trader.py`          | Strategy imports inside methods      |
| `src/core/adaptive_trader.py` | Dynamic strategy loading             |
| `src/strategies/*.py`         | Config imports inside signal methods |
| `src/ui/web/*.py`             | Database imports inside routes       |

---

## ✅ STEP 5: Verification

After fixes, verify:

```bash
# Check no C0415 violations remain
pylint src/ --disable=all --enable=C0415

# Ensure no circular import errors
python -c "import src.main"

# Run full test suite
python run_tests.py

# Expected: 729 tests passing, 5/6 suites PASS
```

---

## 📊 Acceptance Criteria

- [ ] `pylint src/ --disable=all --enable=C0415` returns no violations
- [ ] No new circular import errors introduced
- [ ] All 729 unit tests pass
- [ ] Code compiles without errors: `python -m py_compile src/**/*.py`

---

## 📚 References

- [Pylint C0415 Documentation](https://pylint.pycqa.org/en/latest/user_guide/messages/convention/import-outside-toplevel.html)
- [Python Import Best Practices](https://peps.python.org/pep-0008/#imports)
- [Circular Import Solutions](https://stackoverflow.com/questions/744373/circular-or-cyclic-imports-in-python)
