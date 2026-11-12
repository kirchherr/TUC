"""Installed CLI observer. Default mode uses only stdlib and never opens files."""

from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

SCHEMA = "tuc.bounded_model_cli_observation.v0"


def encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
            .encode("ascii") + b"\n")


def candidate() -> dict[str, object]:
    return {
        "schema_version": SCHEMA, "status": "candidate", "native_execution_observed": False,
        "planned_successful_requests": 3, "planned_rejections": 7,
    }


def run(root: Path) -> dict[str, object]:
    """Run the installed console command as a separate process for every action."""
    executable = Path(sys.executable).parent / "tuc-model-app"
    assert executable.is_file()
    environment = {key: value for key, value in os.environ.items()
                   if key not in {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONUSERBASE"}}
    environment.update(PYTHONNOUSERSITE="1", PYTHONSAFEPATH="1", PYTHONDONTWRITEBYTECODE="1")
    location = subprocess.run(
        [sys.executable, "-I", "-c",
         "import json,sys,tuc;print(json.dumps({'prefix':sys.prefix,'module':tuc.__file__}))"],
        cwd=root, env=environment, capture_output=True, timeout=15, check=True,
    )
    installed = json.loads(location.stdout)
    assert Path(installed["module"]).is_relative_to(Path(installed["prefix"]))
    assert not Path(installed["module"]).is_relative_to(root)
    workspace = root / "workspace"
    workspace.mkdir(mode=0o700)
    backends = ["--backends", "backends.json"]

    def write(name: str, data: bytes) -> str:
        with (root / name).open("xb") as stream:
            stream.write(data)
        return name

    def invoke(arguments: list[str], *, code: int = 0, reason: str = "") -> bytes:
        result = subprocess.run([str(executable), *arguments], cwd=root, env=environment,
                                capture_output=True, timeout=300, check=False)
        assert result.returncode == code
        assert len(result.stdout) <= 4 * 1024 * 1024 and len(result.stderr) <= 256
        if code:
            assert not result.stdout
            assert result.stderr == ("tuc-model-app: " + reason + "\n").encode("ascii")
        else:
            assert not result.stderr
        assert not list(workspace.iterdir())
        return result.stdout

    assert invoke(["--help"]).startswith(b"Usage: tuc-model-app")
    bundle = write("bundle.json", invoke(["plan", "model.json", *backends]))
    context = [*backends, "--bundle", bundle]
    inspected = json.loads(invoke(["inspect", "model.json", *context]))
    assert inspected["native_execution_observed"] is False
    assert all("value_bits" not in item for item in inspected["parameters"])
    report = json.loads(invoke([
        "run-batch", "model.json", *context, "--batch", "batch.json",
        "--workspace", str(workspace),
    ]))
    assert report["native_execution_observed"] is True
    assert [item["id"] for item in report["results"]] == ["base", "variable"]
    assert [item["sequence"] for item in report["results"]] == [1, 2]
    cases = []
    batch = json.loads((root / "batch.json").read_bytes())
    requests = []
    for item, result in zip(batch["requests"], report["results"], strict=True):
        inputs = write(item["id"] + "-inputs.json", encoded({
            "schema_version": "tuc.bounded_cpu_inputs.v0", "inputs": item["inputs"],
        }))
        request = invoke(["request", "model.json", *context, "--inputs", inputs])
        requests.append(write(item["id"] + "-request.json", request))
        assert result["receipt"]["request_digest"] == json.loads(request)["request_digest"]
        cases.append({"name": item["id"], "request": json.loads(request),
                      "receipt": result["receipt"]})

    model = json.loads((root / "model.json").read_bytes())
    model["parameters"]["w"][0] = 4.0
    parameter = write("parameter-model.json", encoded(model))
    parameter_bundle = write("parameter-bundle.json", invoke(["plan", parameter, *backends]))
    parameter_context = [*backends, "--bundle", parameter_bundle]
    parameter_request = invoke([
        "request", parameter, *parameter_context, "--inputs", "inputs.json",
    ])
    request_name = write("parameter-request.json", parameter_request)
    answer = json.loads(invoke([
        "run", parameter, *parameter_context, "--inputs", "inputs.json",
        "--request", request_name, "--workspace", str(workspace),
    ]))
    assert answer["native_execution_observed"] is True
    assert len(answer["results"]) == 1 and answer["results"][0]["sequence"] == 1
    cases.append({"name": "parameter", "request": json.loads(parameter_request),
                  "receipt": answer["results"][0]["receipt"]})

    rejections = []
    write("malformed-request.json", b"{}")
    write("wrong-inputs.json", encoded({
        "schema_version": "tuc.bounded_cpu_inputs.v0", "inputs": {"x": [1.0]},
    }))
    write("override-inputs.json", encoded({
        "schema_version": "tuc.bounded_cpu_inputs.v0", "inputs": {"x": [1.0] * 4, "w": [1.0] * 4},
    }))
    for name, inputs, request in (
        ("malformed_request", "inputs.json", "malformed-request.json"),
        ("wrong_extent", "wrong-inputs.json", requests[0]),
        ("fixed_override", "override-inputs.json", requests[0]),
    ):
        invoke(["run", "model.json", *context, "--inputs", inputs, "--request", request,
                "--workspace", str(workspace)], code=2, reason="input_rejected")
        rejections.append({"name": name, "reason": "model_application_rejected"})
    maximum = struct.unpack("<f", bytes.fromhex("ffff7f7f"))[0]
    write("numeric-inputs.json", encoded({
        "schema_version": "tuc.bounded_cpu_inputs.v0", "inputs": {"x": [maximum, 0.0, 0.0, 0.0]},
    }))
    numeric = invoke(["request", "model.json", *context, "--inputs", "numeric-inputs.json"])
    write("numeric-request.json", numeric)
    invoke(["run", "model.json", *context, "--inputs", "numeric-inputs.json",
            "--request", "numeric-request.json", "--workspace", str(workspace)],
           code=1, reason="numeric_rejection")
    rejections.append({"name": "numeric_overflow", "reason": "numeric_rejection"})

    # A malformed later request cannot publish the otherwise valid first result.
    batch["requests"][-1]["inputs"]["x"] = [1.0]
    write("invalid-batch.json", encoded(batch))
    invoke(["run-batch", "model.json", *context, "--batch", "invalid-batch.json",
            "--workspace", str(workspace)], code=2, reason="input_rejected")
    invoke(["run", "model.json", *context, "--inputs", "variable-inputs.json",
            "--request", requests[0], "--workspace", str(workspace)],
           code=2, reason="input_rejected")
    # CUDA remains valid planning data; the explicit CPU command must reject it.
    cuda = json.loads((root / "backends.json").read_bytes())
    cuda["bindings"][0]["target"] = "cuda-sm86"
    cuda["bindings"][0]["memory_domain"] = "unknown"
    write("cuda-backends.json", encoded(cuda))
    write("cuda-bundle.json", invoke(["plan", "model.json", "--backends", "cuda-backends.json"]))
    invoke(["run-batch", "model.json", "--backends", "cuda-backends.json",
            "--bundle", "cuda-bundle.json", "--batch", "batch.json",
            "--workspace", str(workspace)], code=2, reason="model_application_rejected")

    record = {
        "schema_version": "tuc.bounded_model_application_native.v0", "status": "PASS",
        "native_execution_observed": True, "successful_runs": 3, "cases": cases,
        "rejections": rejections, "workspaces_clean": True,
    }
    write("record.json", encoded(record))
    observation = {
        "schema_version": SCHEMA, "status": "PASS", "native_execution_observed": True,
        "installed_outside_checkout": True, "successful_requests": 3,
        "batch_sequences": [1, 2], "single_sequence": 1, "rejected_commands": 7,
        "workspaces_clean": True,
    }
    write("cli-observation.json", encoded(observation))
    return observation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    print(encoded(run(Path.cwd()) if args.run else candidate()).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
