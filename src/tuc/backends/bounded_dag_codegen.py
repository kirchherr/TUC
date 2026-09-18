"""Deterministic primitive source emission; never compile or execute artifacts.

Names and source fragments cannot enter this boundary. The public DAG lowering
pass supplies validated integer shapes and closed operation kinds. Emitted
primitives still require a separately reviewed native caller to establish live
buffer extents, non-overlapping output storage, rounding mode and launch geometry.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import prod


@dataclass(frozen=True)
class KernelSpec:
    index: int
    kind: str
    input_shapes: tuple[tuple[int, ...], ...]
    output_shape: tuple[int, ...]


def _validate_specs(specs: tuple[KernelSpec, ...]) -> None:
    if type(specs) is not tuple or not 1 <= len(specs) <= 8:
        raise ValueError("bounded DAG kernel count rejected")
    scalar_work = 0
    for index, spec in enumerate(specs):
        if (
            type(spec) is not KernelSpec
            or type(spec.index) is not int
            or spec.index != index
            or type(spec.kind) is not str
            or spec.kind not in ("matmul", "relu", "sum_axis1")
            or type(spec.input_shapes) is not tuple
            or len(spec.input_shapes) != (2 if spec.kind == "matmul" else 1)
        ):
            raise ValueError("bounded DAG kernel descriptor rejected")
        for shape in (*spec.input_shapes, spec.output_shape):
            if (
                type(shape) is not tuple
                or len(shape) not in (1, 2)
                or any(type(d) is not int or not 1 <= d <= 64 for d in shape)
            ):
                raise ValueError("bounded DAG kernel shape rejected")
        first = spec.input_shapes[0]
        if spec.kind == "matmul":
            second = spec.input_shapes[1]
            if (
                len(first) != 2
                or len(second) != 2
                or first[1] != second[0]
                or spec.output_shape != (first[0], second[1])
            ):
                raise ValueError("bounded DAG matmul shape rejected")
        elif spec.kind == "relu":
            if spec.output_shape != first:
                raise ValueError("bounded DAG ReLU shape rejected")
        elif len(first) != 2 or spec.output_shape != (first[0],):
            raise ValueError("bounded DAG reduction shape rejected")
        scalar_work += (
            2 * first[0] * first[1] * spec.output_shape[1]
            if spec.kind == "matmul"
            else prod(first)
        )
        if scalar_work > 1_000_000:
            raise ValueError("bounded DAG scalar work budget exceeded")


def _parameters(spec: KernelSpec) -> str:
    return ", ".join(
        [*(f"const float *input_{i}" for i in range(len(spec.input_shapes))), "float *output"]
    )


def _body(spec: KernelSpec, cuda: bool) -> list[str]:
    count = prod(spec.output_shape)
    if cuda:
        lines = [
            "  const size_t index = (size_t)blockIdx.x * blockDim.x + threadIdx.x;",
            f"  if (index >= {count}U) return;",
        ]
        indent = "  "
    else:
        lines = [f"  for (size_t index = 0; index < {count}U; ++index) {{"]
        indent = "    "
    if spec.kind == "relu":
        lines.extend([
            f"{indent}const float value = input_0[index];",
            f"{indent}output[index] = value < 0.0F ? 0.0F : value;",
        ])
    else:
        if spec.kind == "matmul":
            columns = spec.output_shape[1]
            inner = spec.input_shapes[0][1]
            lines.extend([
                f"{indent}const size_t row = index / {columns}U;",
                f"{indent}const size_t column = index % {columns}U;",
            ])
            operands = f"input_0[row * {inner}U + k], input_1[k * {columns}U + column]"
            c_product = operands.replace(", ", " * ")
        else:
            inner = spec.input_shapes[0][1]
        accumulator = "float" if cuda else "volatile float"
        lines.extend([
            f"{indent}{accumulator} value = 0.0F;",
            f"{indent}for (size_t k = 0; k < {inner}U; ++k) {{",
        ])
        if spec.kind == "matmul":
            product = f"__fmul_rn({operands})" if cuda else c_product
            lines.append(f"{indent}  {accumulator} product = {product};")
            addend = "product"
        else:
            addend = f"input_0[index * {inner}U + k]"
        addition = f"__fadd_rn(value, {addend})" if cuda else f"value + {addend}"
        lines.extend([
            f"{indent}  value = {addition};",
            f"{indent}}}",
            f"{indent}output[index] = value;",
        ])
    if not cuda:
        lines.append("  }")
    return lines


def emit_kernels(specs: tuple[KernelSpec, ...]) -> tuple[str, str, str]:
    """Return C11 header/source and CUDA source, as inert bounded text.

The result is not an execution API or evidence of native correctness. C11
requires binary32 arithmetic, FE_TONEAREST, -fno-fast-math and -ffp-contract=off.
CUDA requires sm86 SASS, --ftz=false and --fmad=false. All pointer extents and
the distinct output storage remain obligations of the future native wrapper.
"""
    _validate_specs(specs)
    header = [
        "#ifndef TUC_BOUNDED_DAG_GENERATED_H",
        "#define TUC_BOUNDED_DAG_GENERATED_H",
        "/* Inert primitives: caller validates extents and disjoint output buffers. */",
        '#ifdef __cplusplus',
        'extern "C" {',
        "#endif",
    ]
    c11 = [
        '#include "generated.h"',
        "#include <stddef.h>",
        "#include <float.h>",
        "#ifdef __FAST_MATH__",
        '#error "bounded DAG forbids fast math"',
        "#endif",
        '_Static_assert(sizeof(float) == 4 && FLT_RADIX == 2 && FLT_MANT_DIG == 24,',
        '               "bounded DAG requires binary32");',
        '_Static_assert(FLT_MAX_EXP == 128 && FLT_MIN_EXP == -125 && FLT_EVAL_METHOD == 0,',
        '               "bounded DAG requires binary32 evaluation");',
        "/* Build with -std=c11 -fno-fast-math -ffp-contract=off; use FE_TONEAREST. */",
        "",
    ]
    cuda = [
        "#ifndef TUC_BOUNDED_DAG_KERNELS_CUH",
        "#define TUC_BOUNDED_DAG_KERNELS_CUH",
        "#include <stddef.h>",
        "#if defined(__CUDA_ARCH__) && __CUDA_ARCH__ != 860",
        '#error "bounded DAG CUDA target requires sm86"',
        "#endif",
        "/* Compile sm86 SASS only, --ftz=false --fmad=false; no runtime JIT. */",
        "/* Launch a 1D grid with 128 threads/block and ceil(output_elements/128) blocks. */",
        "/* Caller validates live device extents and disjoint output buffers. */",
        "",
    ]
    for spec in specs:
        parameters = _parameters(spec)
        declaration = f"void tuc_dag_op_{spec.index}({parameters})"
        header.append(declaration + ";")
        c11.extend([declaration + " {", *_body(spec, False), "}", ""])
        cuda.extend([
            f"__global__ void tuc_dag_cuda_op_{spec.index}({parameters}) {{",
            *_body(spec, True), "}", "",
        ])
    header.extend(["#ifdef __cplusplus", "}", "#endif", "#endif", ""])
    cuda.extend(["#endif", ""])
    return "\n".join(header), "\n".join(c11), "\n".join(cuda)
