"""Generate packaged Python gRPC bindings from the versioned wire authority."""

import argparse
import tempfile
from pathlib import Path

from grpc_tools import protoc

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--check", action="store_true")
options = parser.parse_args()
destination = root / "services/control-plane/src/jocky_control_plane/generated"
with tempfile.TemporaryDirectory(prefix="jocky-protobuf-") as directory:
    output = Path(directory)
    result = protoc.main(
        [
            "protoc",
            f"-I{root / 'proto'}",
            f"--python_out={output}",
            f"--grpc_python_out={output}",
            str(root / "proto/jocky/v1/agent.proto"),
        ]
    )
    if result:
        raise SystemExit(result)
    for source in output.rglob("*.py"):
        content = source.read_text(encoding="utf-8").replace(
            "from jocky.v1 import agent_pb2",
            "from jocky_control_plane.generated.jocky.v1 import agent_pb2",
        )
        target = destination / source.relative_to(output)
        if options.check:
            if not target.exists() or target.read_text(encoding="utf-8") != content:
                raise SystemExit(f"Generated gRPC binding drift: {target.name}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8", newline="\n")
