# Clean up temp files
import os
for f in ['verify_all.py', 'verify_imports.py', 'check_syntax.py']:
    fp = os.path.join('/home/datahome/chiangmai-property/backend', f)
    if os.path.exists(fp):
        os.remove(fp)
        print(f"Removed {f}")
