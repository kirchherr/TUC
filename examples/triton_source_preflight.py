"""Run the execution-free Triton source preflight report."""

from __future__ import annotations

from tuc.frontend import preflight_triton_source

SOURCE = """@triton.jit
def kernel(a, b, c):
    offsets = tl.arange(0, 16)
    acc = tl.dot(a, b)
    y = tl.exp(acc + 1.0)
    tl.store(c + offsets, y)
"""


def main() -> None:
    report = preflight_triton_source(SOURCE, source_name="mvp_kernel")
    print(report.dump())


if __name__ == "__main__":
    main()
