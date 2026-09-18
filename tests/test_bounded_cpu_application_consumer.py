"""Independent example arithmetic and inert installed-client checks."""
import ast
import json
from pathlib import Path

import numpy as np
import pytest

from integration.bounded_cpu_application import consumer
from tuc.compiler.bounded_c11_application import encode_bounded_c11_inputs


@pytest.mark.parametrize("graph", consumer.GRAPHS)
@pytest.mark.parametrize("case", range(3))
def test_example_reference_matches_explicit_numpy_rounding(graph, case):
    data = consumer.inputs(graph, case)
    actual = consumer.reference(graph, data)
    if graph == "activation":
        expected = np.maximum(np.asarray(data["x"], dtype=np.float32), np.float32(0))
        np.testing.assert_array_equal(actual["activated"], expected)
        return
    a = np.asarray(data["a"], dtype=np.float32).reshape(2, 3)
    b = np.asarray(data["b"], dtype=np.float32).reshape(3, 2)
    result = np.zeros((2, 2), dtype=np.float32)
    for inner in range(3):
        result = np.add(result, np.multiply(a[:, inner, None], b[inner, None, :],
                                           dtype=np.float32), dtype=np.float32)
    np.testing.assert_array_equal(actual["activated"], np.maximum(result, np.float32(0)).ravel())
    np.testing.assert_array_equal(actual["totals"], np.add(result[:, 0], result[:, 1],
                                                          dtype=np.float32))


def test_client_default_prepares_only_and_inputs_change():
    report = consumer.candidate()
    assert report["native_execution_observed"] is False
    assert len(set(report["programs"].values())) == 2
    for graph in consumer.GRAPHS:
        app = consumer.prepare_bounded_c11_application(consumer.module(graph), consumer.bindings())
        frames = [encode_bounded_c11_inputs(consumer.module(graph), consumer.bindings(), app,
                                           consumer.inputs(graph, case)) for case in range(3)]
        assert len(set(frames)) == 3
        assert len({tuple(consumer.reference(graph, consumer.inputs(graph, case)).values())
                    for case in range(3)}) == 3


def test_installed_consumer_has_no_repository_or_native_loader_imports():
    tree = ast.parse(Path(consumer.__file__).read_text(encoding="utf-8"))
    names = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert not any(name.startswith(("examples", "integration")) for name in names)
    assert not any(isinstance(node, ast.Import) and any(alias.name in ("ctypes", "subprocess")
               for alias in node.names) for node in ast.walk(tree))


def test_fuzz_contexts_contain_original_artifacts_and_fixed_frames(monkeypatch, tmp_path, capsys):
    for name in ("fuzz.c", "fuzz.Dockerfile", "fuzz.Dockerfile.dockerignore"):
        (tmp_path / name).write_bytes((consumer.ROOT / name).read_bytes())
    monkeypatch.setattr(consumer, "ROOT", tmp_path)
    consumer.emit_fuzz()
    contexts = [Path(line) for line in capsys.readouterr().out.splitlines()]
    assert len(contexts) == 2
    for graph, context in zip(consumer.GRAPHS, contexts, strict=True):
        app = consumer.prepare_bounded_c11_application(consumer.module(graph), consumer.bindings())
        for name, value in app.files().items():
            assert (context / name).read_bytes() == value.encode()
        identity = json.loads((context / "identity.json").read_text())
        assert identity["program_digest"] == app.program_digest
        request = (context / "request.bin").read_bytes()
        assert (context / "truncated.bin").read_bytes() == request[:-1]
        assert (context / "extra.bin").read_bytes() == request + b"\0"
        assert (context / "expected.bin").stat().st_size == 100
