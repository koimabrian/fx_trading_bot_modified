---
name: Fix Unused Imports
about: Remove all unused import statements from codebase
title: "[CLEANUP] Fix Pylint W0611 unused-import violations"
labels: refactoring, code-quality, pylint, cleanup
assignees: ''
---

## 🎯 Objective

Remove all unused imports (Pylint W0611) from the codebase to improve code cleanliness, reduce memory footprint, and speed up module loading.

---

## 📋 Problem Description

**Pylint Rule:** `W0611 (unused-import)`

> Unused import statement - module is imported but never used.

### Why this matters:
1. **Performance**: Unused imports waste memory and slow startup
2. **Readability**: Cluttered imports make dependencies unclear
3. **Maintenance**: Dead imports create confusion about actual dependencies
4. **Bundle Size**: Unused imports may pull in unnecessary dependencies

---

## 🔍 STEP 1: Find All Violations

Run this command to identify all unused imports:

```bash
pylint src/ --disable=all --enable=W0611 --output-format=text
```

Or use a more detailed report:

```bash
pylint src/ --disable=all --enable=W0611 --output-format=json > unused_imports.json
```

---

## 🔧 STEP 2: Fix Patterns

### Pattern A: Simply remove unused import
```python
# Before ❌
import os
import sys  # Never used
import logging

# After ✅
import os
import logging
```

### Pattern B: Remove from grouped imports
```python
# Before ❌
from typing import Dict, List, Optional, Any  # Any never used

# After ✅
from typing import Dict, List, Optional
```

### Pattern C: Remove entire import line
```python
# Before ❌
from src.utils.some_module import unused_function  # Never called

# After ✅
# (line removed entirely)
```

---

## ⚠️ STEP 3: Special Cases

### TYPE_CHECKING imports (Keep these!)
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.module import SomeClass  # Used for type hints only - KEEP!
```

### __all__ exports (Keep these!)
```python
from .submodule import SomeClass  # Re-exported in __all__ - KEEP!

__all__ = ['SomeClass']
```

### Future use with TODO (Document or remove)
```python
# If keeping for future use, add comment:
import future_module  # TODO: Will be used in feature X

# Otherwise, remove it - can always add back later
```

---

## 📁 STEP 4: Common Locations to Check

| File Pattern         | Common Unused Imports                         |
| -------------------- | --------------------------------------------- |
| `src/**/__init__.py` | Re-exports that aren't in `__all__`           |
| `src/utils/*.py`     | `os`, `sys`, `json` often imported but unused |
| `src/core/*.py`      | Type hints imported but not used              |
| `src/ui/**/*.py`     | Flask/PyQt imports not all used               |
| `tests/**/*.py`      | Test fixtures imported but not used           |

---

## 🛠️ STEP 5: Automated Fix (Optional)

Use `autoflake` for automatic removal:

```bash
# Install
pip install autoflake

# Dry run (preview changes)
autoflake --remove-all-unused-imports --recursive --check src/

# Apply fixes
autoflake --remove-all-unused-imports --recursive --in-place src/
```

Or use `isort` to clean up imports:

```bash
pip install isort
isort src/ --remove-unused-imports
```

---

## ✅ STEP 6: Verification

After fixes, verify:

```bash
# Check no W0611 violations remain
pylint src/ --disable=all --enable=W0611

# Ensure code still compiles
python -m py_compile src/**/*.py

# Check no import errors
python -c "import src.main"

# Run full test suite
python run_tests.py

# Expected: 729 tests passing, 5/6 suites PASS
```

---

## 📊 Acceptance Criteria

- [ ] `pylint src/ --disable=all --enable=W0611` returns no violations
- [ ] All modules still import correctly: `python -c "import src.main"`
- [ ] All 729 unit tests pass
- [ ] No regression in functionality

---

## 🔄 Prevention

Add to CI/CD pipeline:

```yaml
# .github/workflows/lint.yml
- name: Check unused imports
  run: pylint src/ --disable=all --enable=W0611 --fail-under=10
```

Or add pre-commit hook:

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/PyCQA/autoflake
  rev: v2.0.0
  hooks:
    - id: autoflake
      args: [--remove-all-unused-imports, --in-place]
```

---

## 📚 References

- [Pylint W0611 Documentation](https://pylint.pycqa.org/en/latest/user_guide/messages/warning/unused-import.html)
- [PEP 8 - Imports](https://peps.python.org/pep-0008/#imports)
- [autoflake Tool](https://github.com/PyCQA/autoflake)
- [isort Tool](https://pycqa.github.io/isort/)
