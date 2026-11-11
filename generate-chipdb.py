"""Run nextpnr's generator without retaining single-wire routing nodes."""

import sys
from pathlib import Path


generator = Path(sys.argv.pop(1)).resolve()
source = generator.read_text(encoding="utf-8")
original = "            for w in t.wires():\n                n = w.node()\n"
compact = (
    "            for wire_index in sorted(t.wire_to_node):\n"
    "                n = t.wire_to_node[wire_index]\n"
)
if source.count(original) != 1 or "if len(n.wires) > 1:" not in source:
    raise SystemExit("Unsupported nextpnr generator revision")

# Wire.node() creates a one-wire node when it finds no existing node.
# Those nodes never pass the generator's len(n.wires) > 1 test. Walk
# existing nodes in the original wire-index order and preserve all output.
sys.argv[0] = str(generator)
sys.path.insert(0, str(generator.parent))
scope = {"__name__": "__main__", "__file__": str(generator)}
exec(compile(source.replace(original, compact), str(generator), "exec"), scope)
