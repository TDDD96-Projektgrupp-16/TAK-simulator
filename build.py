import subprocess
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        proto_dir = Path("proto")
        output_dir = Path("src/tak_simulator/proto")
        proto_files = list(proto_dir.glob("*.proto"))

        if not proto_files:
            return

        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"--proto_path={proto_dir}",
            f"--python_out={output_dir}",
            f"--pyi_out={output_dir}",
        ] + [str(p) for p in proto_files]

        subprocess.run(cmd, check=True)