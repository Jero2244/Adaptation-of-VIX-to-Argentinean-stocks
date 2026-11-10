import json
from common import *
d = make_copy("cli")
run(d, "good", script="freeze_cli.py")
(d / "reports" / "backward_test_run.json").write_text(json.dumps(dict(status="crashed", attempts=[])))
print(d)
