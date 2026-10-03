"""Print DRC violations present in NEW but not in BASE (both KiCad JSON reports)."""
import collections
import json
import re
import sys


def load(path):
    d = json.load(open(path))
    c, where = collections.Counter(), {}
    for v in d["violations"] + d.get("unconnected_items", []):
        items = tuple(sorted(re.sub(r"(length [\d.]+ mm|Arc|Segment|actual [\d.]+ mm)", "", i["description"]) for i in v["items"]))
        k = (v["type"], items)
        c[k] += 1
        where.setdefault(k, []).append([(round(i["pos"]["x"], 2), round(i["pos"]["y"], 2)) for i in v["items"]])
    return c, where


base, _ = load(sys.argv[1])
new, where = load(sys.argv[2])
extra = new - base
for k, n in sorted(extra.items()):
    print(n, k[0], "|", " / ".join(k[1]), where[k][0])
print(f"total {sum(new.values())} (base {sum(base.values())}), new kinds: {sum(extra.values())}")
