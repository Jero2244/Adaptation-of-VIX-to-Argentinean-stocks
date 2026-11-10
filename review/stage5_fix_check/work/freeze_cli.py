import os, runpy, sys
os.chdir(os.environ["DRIVER_PROJECT"]); sys.path.insert(0, os.environ["DRIVER_PROJECT"])
sys.argv = ["freeze.py", *sys.argv[1:]]
runpy.run_path(os.path.join(os.environ["DRIVER_PROJECT"], "freeze.py"), run_name="__main__")
