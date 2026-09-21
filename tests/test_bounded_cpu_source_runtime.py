"""Mock OCI source conversion. No synthetic result is native execution evidence."""

import ast
import io
import json
import subprocess
import tarfile
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from tuc.runtime import bounded_cpu_source as runtime

SOURCE = b"PRIVATE_USER_SOURCE_NEVER_IN_BUILD_CONTEXT"
SIGNATURE = b"PRIVATE_SIGNATURE_NEVER_IN_BUILD_CONTEXT"
REQUEST = b'{"synthetic_request":"source-worker-runtime-test"}'
RESPONSE = b'{"synthetic_response":"not-native-evidence"}'
GRAPH = b'{"synthetic_graph":"not-native-evidence"}\n'


@pytest.fixture
def host(tmp_path, monkeypatch):
    state = SimpleNamespace(events=[], commands=[], contexts=[], build_result=None,
                            inspect_result=None, run_result=None, failure=None,
                            decode_error=None, cleanup_ok=True, workspace=tmp_path,
                            cleaned=[], removed=[], request=REQUEST, remove_result=None,
                            remove_error=None, list_result=None, list_results=[], list_error=None)

    def prepare(source, signature):
        state.events.append("prepare")
        assert source is SOURCE and signature is SIGNATURE
        return state.request

    def decode(request, response):
        state.events.append("decode")
        assert request == REQUEST and response == RESPONSE
        if state.decode_error is not None:
            raise state.decode_error
        return GRAPH

    def context(workspace, files):
        state.events.append("context")
        assert workspace == tmp_path
        value = SimpleNamespace(files=files, tag="tuc-test:owned" + str(len(state.contexts)),
                                directory=tmp_path / "fixed-context")
        state.contexts.append(value)
        return value

    def command(context, arguments, **options):
        state.commands.append((arguments, options))
        if arguments[0] == "build":
            state.events.append("build")
            return state.build_result or runtime.isolated._ProcessResult(0, b"", b"")
        if arguments[:2] == ("image", "inspect"):
            state.events.append("inspect")
            return state.inspect_result or runtime.isolated._ProcessResult(
                0, b"sha256:" + b"a" * 64 + b"\n", b"")
        if arguments[0] == "rm":
            state.events.append("remove-container")
            assert arguments[:2] == ("rm", "--force") and len(arguments) == 3
            state.removed.append((context, arguments[2]))
            if state.remove_error is not None:
                raise state.remove_error
            return state.remove_result or runtime.isolated._ProcessResult(0, b"", b"")
        if arguments[:2] == ("container", "ls"):
            state.events.append("confirm-container-absent")
            if state.list_error is not None:
                raise state.list_error
            if state.list_results:
                return state.list_results.pop(0)
            return state.list_result or runtime.isolated._ProcessResult(0, b"", b"")
        assert arguments[0] == "run"
        state.events.append("run")
        if state.failure is not None:
            raise state.failure
        return state.run_result or runtime.isolated._ProcessResult(0, RESPONSE, b"")

    def cleanup(context):
        state.events.append("cleanup")
        state.cleaned.append(context)
        return state.cleanup_ok

    monkeypatch.setattr(runtime, "prepare_source_request", prepare)
    monkeypatch.setattr(runtime, "decode_source_response", decode)
    monkeypatch.setattr(runtime.isolated, "_require_platform", lambda: None)
    monkeypatch.setattr(runtime.isolated, "_workspace", lambda path: path)
    monkeypatch.setattr(runtime.isolated, "_make_context", context)
    monkeypatch.setattr(runtime.isolated, "_write_context",
                        lambda ctx: state.events.append("write"))
    monkeypatch.setattr(runtime.isolated, "_verify_context",
                        lambda ctx: state.events.append("verify"))
    monkeypatch.setattr(runtime.isolated, "_command", command)
    monkeypatch.setattr(runtime.isolated, "_cleanup", cleanup)
    return state


def convert(host):
    return runtime.convert_bounded_cpu_source(SOURCE, SIGNATURE, workspace=host.workspace)


def test_conversion_publishes_only_after_checked_response_and_cleanup(host):
    assert convert(host) is GRAPH
    assert host.events == ["prepare", "context", "write", "build", "inspect", "verify",
                           "run", "decode", "confirm-container-absent", "cleanup"]
    assert host.cleaned == host.contexts
    assert not host.removed
    build, inspect, run, absent = host.commands
    assert build[0] == ("build", "--network=none", "--pull=false", "--no-cache", "--tag",
                         host.contexts[0].tag, "--file", "Dockerfile", "-")
    assert build[1]["timeout"] == runtime.isolated.BUILD_TIMEOUT
    assert build[1]["stdout_limit"] == build[1]["stderr_limit"] == 2 * 1024 * 1024
    assert inspect[0] == ("image", "inspect", "--format", "{{.Id}}", host.contexts[0].tag)
    assert inspect[1]["stdout_limit"] == 80
    assert run[0][-4:] == ("sha256:" + "a" * 64, "-I", runtime._WORKER, "--oci")
    assert run[1] == {"input_bytes": REQUEST, "timeout": 30.0,
                      "stdout_limit": 256 * 1024, "stderr_limit": 4096}
    assert "--entrypoint=/usr/local/bin/python" in run[0]
    name = run[0][run[0].index("--name") + 1]
    assert absent[0] == ("container", "ls", "--all", "--format", "{{.Names}}", "--filter",
                         "name=^/" + name + "$")
    assert absent[1] == {"stdout_limit": 80}
    for flag in ("--network=none", "--read-only", "--user=10001:10001", "--cpus=1",
                 "--memory=1g", "--memory-swap=1g", "--pids-limit=32", "--cap-drop=ALL",
                 "--security-opt=no-new-privileges:true", "--workdir=/run/tuc",
                 "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m", "--pull=never"):
        assert flag in run[0]
    assert not any(arg.startswith(("--gpus", "--privileged", "--mount", "--volume", "--env"))
                   for arg in run[0])


def test_build_context_has_no_caller_source_signature_or_request(host):
    assert convert(host) == GRAPH
    archive_bytes = host.commands[0][1]["input_bytes"]
    assert SOURCE not in archive_bytes and SIGNATURE not in archive_bytes
    assert REQUEST not in archive_bytes
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
        expected = dict(runtime._fixed_files())
        assert {item.name for item in archive.getmembers()} == set(expected)
        for member in archive.getmembers():
            assert member.isfile() and member.name == Path(member.name).name
            assert archive.extractfile(member).read() == expected[member.name]


def test_fresh_conversion_has_no_image_or_container_reuse(host):
    convert(host)
    convert(host)
    assert len(host.contexts) == 2
    assert host.contexts[0].tag != host.contexts[1].tag
    runs = [args for args, _ in host.commands if args[0] == "run"]
    assert runs[0][runs[0].index("--name") + 1] != runs[1][runs[1].index("--name") + 1]
    assert all("--no-cache" in args for args, _ in host.commands if args[0] == "build")


@pytest.mark.parametrize("candidate", [b"", b"x" * (96 * 1024 + 1), "text", bytearray(b"x")],
                         ids=["empty", "oversized", "text", "mutable"])
def test_request_budget_and_type_reject_before_context(host, candidate):
    host.request = candidate
    with pytest.raises(runtime.BoundedCPUSourceRuntimeError, match="protocol_rejected"):
        convert(host)
    assert host.events == ["prepare"] and not host.contexts


def test_pure_rejection_never_reads_bundle_or_touches_workspace(host, monkeypatch):
    def reject(*args):
        raise runtime.BoundedCPUSourceError("source_rejected")

    monkeypatch.setattr(runtime, "prepare_source_request", reject)
    monkeypatch.setattr(runtime, "_fixed_files", lambda: pytest.fail("bundle read"))
    with pytest.raises(runtime.BoundedCPUSourceError):
        convert(host)
    assert not host.contexts and not host.commands


@pytest.mark.parametrize("stage,expected", [("platform", "unsupported_platform"),
    ("bundle", "bundle_rejected"), ("workspace", "workspace_rejected"),
    ("write", "workspace_rejected"), ("verify", "context_drift")])
def test_preexecution_failures_are_closed_and_cleanup_when_context_exists(host, monkeypatch,
                                                                         stage, expected):
    def fail(*args):
        raise ValueError("SECRET path or source")

    target, name = {
        "platform": (runtime.isolated, "_require_platform"),
        "bundle": (runtime, "_fixed_files"),
        "workspace": (runtime.isolated, "_workspace"),
        "write": (runtime.isolated, "_write_context"),
        "verify": (runtime.isolated, "_verify_context"),
    }[stage]
    monkeypatch.setattr(target, name, fail)
    with pytest.raises(runtime.BoundedCPUSourceRuntimeError) as error:
        convert(host)
    assert str(error.value) == error.value.reason == expected
    assert "SECRET" not in repr(error.value)
    assert host.cleaned == host.contexts
    assert not host.removed


@pytest.mark.parametrize("kind,reason", [("build", "build_failed"), ("inspect", "image_rejected"),
                                       ("identity", "image_rejected"), ("stderr", "process_error"),
                                       ("exit", "process_error")])
def test_bad_process_result_never_reaches_response_decoder(host, kind, reason):
    if kind == "build":
        host.build_result = runtime.isolated._ProcessResult(9, b"SECRET", b"SECRET")
    elif kind == "inspect":
        host.inspect_result = runtime.isolated._ProcessResult(0, b"sha256:" + b"a" * 64, b"SECRET")
    elif kind == "identity":
        host.inspect_result = runtime.isolated._ProcessResult(0, b"caller/image:untrusted", b"")
    elif kind == "stderr":
        host.run_result = runtime.isolated._ProcessResult(0, RESPONSE, b"SECRET")
    else:
        host.run_result = runtime.isolated._ProcessResult(1, RESPONSE, b"")
    with pytest.raises(runtime.BoundedCPUSourceRuntimeError) as error:
        convert(host)
    assert error.value.reason == reason
    assert "decode" not in host.events and host.events[-1] == "cleanup"
    assert len(host.removed) == (1 if kind in {"stderr", "exit"} else 0)


@pytest.mark.parametrize("exception,reason", [
    (runtime.isolated._ProcessFailure("timeout"), "timeout"),
    (runtime.isolated._ProcessFailure("output_limit"), "output_limit"),
    (runtime.isolated._ProcessFailure("input_rejection"), "process_error"),
    (subprocess.TimeoutExpired("SECRET", 30), "timeout"),
    (OSError("SECRET host path"), "process_error"),
])
def test_runtime_failure_removes_only_owned_container_and_never_exposes_diagnostics(host,
                                                                                   exception,
                                                                                   reason):
    host.failure = exception
    with pytest.raises(runtime.BoundedCPUSourceRuntimeError) as error:
        convert(host)
    assert error.value.reason == reason and "SECRET" not in str(error.value)
    assert host.cleaned == host.contexts
    assert len(host.removed) == 1
    args = next(args for args, _ in host.commands if args[0] == "run")
    assert host.removed[0] == (host.contexts[0], args[args.index("--name") + 1])


def test_validated_source_rejection_is_preserved_only_after_cleanup(host):
    rejected = runtime.BoundedCPUSourceError("source_rejected")
    host.decode_error = rejected
    with pytest.raises(runtime.BoundedCPUSourceError) as error:
        convert(host)
    assert error.value is rejected
    assert host.events[-1] == "cleanup" and len(host.removed) == 1


@pytest.mark.parametrize("kind", ["accepted", "source_rejected", "timeout", "interrupt"])
def test_cleanup_failure_overrides_any_graph_or_original_failure(host, kind):
    host.cleanup_ok = False
    if kind == "source_rejected":
        host.decode_error = runtime.BoundedCPUSourceError("source_rejected")
    elif kind == "timeout":
        host.failure = runtime.isolated._ProcessFailure("timeout")
    elif kind == "interrupt":
        host.failure = KeyboardInterrupt()
    with pytest.raises(runtime.BoundedCPUSourceRuntimeError, match="cleanup_failed"):
        convert(host)
    assert host.events[-1] == "cleanup"


def test_interrupt_still_removes_owned_container_and_context(host):
    host.failure = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        convert(host)
    assert host.cleaned == host.contexts and len(host.removed) == 1


def test_unclassified_response_decoder_exception_is_closed(host):
    host.decode_error = ValueError("SECRET response bytes")
    with pytest.raises(runtime.BoundedCPUSourceRuntimeError, match="protocol_rejected"):
        convert(host)
    assert host.events[-1] == "cleanup"


@pytest.mark.parametrize("failure", ["nonzero", "timeout", "diagnostic", "still_present"])
def test_failed_container_removal_cannot_be_hidden_by_context_cleanup(host, failure):
    host.failure = runtime.isolated._ProcessFailure("timeout")
    host.remove_result = runtime.isolated._ProcessResult(1, b"", b"remove failed")
    if failure == "nonzero":
        host.list_result = runtime.isolated._ProcessResult(1, b"", b"daemon error")
    elif failure == "timeout":
        host.list_error = runtime.isolated._ProcessFailure("timeout")
    elif failure == "diagnostic":
        host.list_result = runtime.isolated._ProcessResult(0, b"", b"unexpected diagnostic")
    else:
        host.list_result = runtime.isolated._ProcessResult(0, b"still-present\n", b"")
    with pytest.raises(runtime.BoundedCPUSourceRuntimeError, match="^cleanup_failed$"):
        convert(host)
    assert host.cleanup_ok and host.cleaned == host.contexts
    assert host.events[-3:] == ["remove-container", "confirm-container-absent", "cleanup"]


@pytest.mark.parametrize("remove_error", [None, OSError("private error"),
    runtime.isolated._ProcessFailure("timeout")], ids=["nonzero", "os-error", "timeout"])
def test_failed_remove_is_safe_only_after_positive_exact_absence(host, remove_error):
    host.failure = runtime.isolated._ProcessFailure("timeout")
    host.remove_error = remove_error
    host.remove_result = runtime.isolated._ProcessResult(1, b"", b"already absent")
    with pytest.raises(runtime.BoundedCPUSourceRuntimeError, match="^timeout$"):
        convert(host)
    assert host.events[-3:] == ["remove-container", "confirm-container-absent", "cleanup"]


def test_completed_run_with_unremoved_container_retries_only_owned_name(host):
    host.list_results = [runtime.isolated._ProcessResult(0, b"owned-still-present\n", b""),
                         runtime.isolated._ProcessResult(0, b"", b"")]
    assert convert(host) == GRAPH
    run = next(args for args, _ in host.commands if args[0] == "run")
    name = run[run.index("--name") + 1]
    assert host.removed == [(host.contexts[0], name)]
    listed = [args for args, _ in host.commands if args[:2] == ("container", "ls")]
    assert len(listed) == 2
    assert all(args[-1] == "name=^/" + name + "$" for args in listed)
    assert host.events[-4:] == ["confirm-container-absent", "remove-container",
                                "confirm-container-absent", "cleanup"]


def test_successful_worker_response_is_not_published_without_container_cleanup(host):
    host.list_result = runtime.isolated._ProcessResult(0, b"owned-still-present\n", b"")
    with pytest.raises(runtime.BoundedCPUSourceRuntimeError, match="^cleanup_failed$"):
        convert(host)
    assert "decode" in host.events and host.cleaned == host.contexts
    assert len(host.removed) == 1


@pytest.mark.parametrize("name", ["", "other-container", "tuc-source-worker-.*", "--all",
    "tuc-source-worker-" + "a" * 31, "tuc-source-worker-" + "A" * 32,
    "tuc-source-worker-" + "a" * 32 + "\n", None, True])
def test_container_cleanup_accepts_only_internal_exact_names(host, name):
    assert runtime._cleanup_container(None, name, remove=True) is False
    assert not host.commands and not host.removed


def test_bundle_is_deterministic_original_bytes_with_empty_package_initializers():
    files = dict(runtime._fixed_files())
    assert files == dict(runtime._fixed_files())
    expected = {name + ".py" for name in runtime._MODULES}
    assert set(files) == expected | {"tuc-init.py", "frontend-init.py", "Dockerfile",
                                     "Dockerfile.dockerignore", "bundle.json"}
    assert files["tuc-init.py"] == files["frontend-init.py"] == b""
    for name in expected:
        assert files[name] == (runtime._PACKAGE_ROOT / "frontend" / name).read_bytes()
    assert sum(map(len, files.values())) < 524288
    manifest = json.loads(files["bundle.json"])
    assert manifest["user_source_included"] is False
    assert manifest["python_image"] == runtime._PYTHON_IMAGE
    assert manifest["dockerfile_frontend"] == runtime._FRONTEND
    for name, digest in manifest["sources"].items():
        assert digest == sha256(files[name]).hexdigest()
    assert set(manifest["sources"]) == set(files) - {"bundle.json"}


def test_docker_recipe_has_exact_pins_offline_copy_allowlist_and_fixed_entrypoint():
    files = dict(runtime._fixed_files())
    recipe = files["Dockerfile"].decode()
    ignore = files["Dockerfile.dockerignore"].decode()
    assert recipe.startswith("# syntax=" + runtime._FRONTEND + "\n")
    assert "FROM --platform=linux/amd64 " + runtime._PYTHON_IMAGE in recipe
    assert "@sha256:" in runtime._PYTHON_IMAGE and "@sha256:" in runtime._FRONTEND
    assert "RUN " not in recipe and "pip" not in recipe and "requirements" not in recipe
    assert "USER 10001:10001\nWORKDIR /run/tuc\n" in recipe
    assert ('ENTRYPOINT ["/usr/local/bin/python", "-I", "' + runtime._WORKER + '", "--oci"]'
            in recipe)
    assert len([line for line in recipe.splitlines() if line.startswith("COPY ")]) == 8
    assert ignore.startswith("**\n") and "bundle.json" not in ignore
    assert "bundle.json" not in recipe
    assert not any(line.startswith(("ARG ", "ADD ", "ENV ")) for line in recipe.splitlines())


@pytest.mark.parametrize("source", [b"import numpy\n", b"from tuc import compiler\n",
    b"from .source_intent import SourceIntentModule\n", b"import subprocess\n",
    b"__import__('os')\n", b"eval('1')\n", b"exec('x=1')\n", b"compile('1','x','eval')\n",
    b"def nested():\n import importlib\n"],
    ids=["numpy", "root-package", "relative", "subprocess", "dynamic-import", "eval", "exec",
         "compile", "nested-import"])
def test_import_closure_rejects_new_dependency_or_dynamic_code(source):
    with pytest.raises(ValueError):
        runtime._verify_imports("installed_module", source)


def test_import_closure_covers_nested_worker_imports():
    worker = dict(runtime._fixed_files())["_isolated_source_ingestion_worker.py"]
    tree = ast.parse(worker)
    imported = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert "tuc.frontend.source_to_intent_research_kernel_ingress" in imported
    runtime._verify_imports("worker", worker)


def test_user_source_is_never_parsed_on_host(host, monkeypatch):
    original = runtime.ast.parse
    observed = []

    def parse(content, *args, **kwargs):
        assert content not in (SOURCE, SIGNATURE, REQUEST)
        observed.append(content)
        return original(content, *args, **kwargs)

    monkeypatch.setattr(runtime.ast, "parse", parse)
    convert(host)
    assert len(observed) == 6


@pytest.mark.parametrize("content", [b"", b"x" * 65537], ids=["empty", "oversized"])
def test_installed_module_reader_rejects_size_before_read(tmp_path, monkeypatch, content):
    path = tmp_path / "installed.py"
    path.write_bytes(content)
    monkeypatch.setattr(runtime.os, "read", lambda *args: pytest.fail("read before size check"))
    with pytest.raises(ValueError):
        runtime._read_module(path)


def test_module_content_mutation_changes_bundle_provenance(tmp_path, monkeypatch):
    original = dict(runtime._fixed_files())
    package = tmp_path / "package"
    frontend = package / "frontend"
    frontend.mkdir(parents=True)
    for name in runtime._MODULES:
        (frontend / (name + ".py")).write_bytes(original[name + ".py"])
    changed = frontend / "source_intent.py"
    changed.write_bytes(changed.read_bytes() + b"\n# changed installed implementation\n")
    monkeypatch.setattr(runtime, "_PACKAGE_ROOT", package)
    rebuilt = dict(runtime._fixed_files())
    assert rebuilt["source_intent.py"] != original["source_intent.py"]
    assert rebuilt["bundle.json"] != original["bundle.json"]
    assert rebuilt["Dockerfile"] == original["Dockerfile"]


def test_runtime_error_reason_is_closed_and_readonly():
    with pytest.raises(ValueError, match="invalid bounded CPU source runtime diagnostic"):
        runtime.BoundedCPUSourceRuntimeError("SECRET")
    error = runtime.BoundedCPUSourceRuntimeError("timeout")
    with pytest.raises(AttributeError):
        error.reason = "source_rejected"
    assert str(error) == "timeout"
