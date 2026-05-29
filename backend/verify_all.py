"""Syntax check of all created schemas and services."""
import sys
import py_compile
import os

base = '/home/datahome/chiangmai-property/backend/app'

files = [
    f'{base}/schemas/__init__.py',
    f'{base}/schemas/property.py',
    f'{base}/schemas/auth.py',
    f'{base}/schemas/favorite.py',
    f'{base}/services/__init__.py',
    f'{base}/services/property_service.py',
    f'{base}/services/auth_service.py',
    f'{base}/services/favorite_service.py',
]

ok = True
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        name = os.path.relpath(f, base)
        print(f"  ✅ {name}")
    except py_compile.PyCompileError as e:
        print(f"  ❌ {os.path.basename(f)}: {e}")
        ok = False

if ok:
    print("\n🎉 All 8 files pass syntax check!")
else:
    print("\n❌ Some files have errors!")
    sys.exit(1)
