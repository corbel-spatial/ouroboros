# workaround until this PR gets merged
# https://github.com/plasma-umass/slipcover/pull/67

import json
from sys import argv

cov_file = argv[1]

with open(cov_file, "r") as f:
    data = json.load(f)
pct = data["summary"]["percent_covered"]
pct_display = f"{int(round(pct, 0))}%"
data["summary"]["percent_covered_display"] = pct_display
with open(cov_file, "w") as f:
    json.dump(data, f, indent=4)
print(pct_display)
