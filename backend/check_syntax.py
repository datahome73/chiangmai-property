import subprocess,sys
r=subprocess.run(['python3','-c','import py_compile; py_compile.compile("/home/datahome/chiangmai-property/backend/app/schemas/property.py",doraise=True); print("OK")'],capture_output=True,text=True)
print(r.stdout,r.stderr)
print(r.returncode)
