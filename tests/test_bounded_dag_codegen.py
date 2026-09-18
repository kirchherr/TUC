"""Direct checks of the inert kernel-descriptor boundary and arithmetic policy."""

from dataclasses import replace
from enum import StrEnum

import pytest

from tuc.backends.bounded_dag_codegen import KernelSpec, emit_kernels


class _Untrusted:
    def __str__(self):
        raise AssertionError("untrusted object reached source interpolation")

    def __eq__(self, other):
        raise AssertionError("untrusted object reached semantic comparison")


class _Integer(int):
    pass


class _Tuple(tuple):
    pass


class _Kind(StrEnum):
    RELU = "relu"


class _Descriptor(KernelSpec):
    pass


def _matmul(index=0):
    return KernelSpec(index, "matmul", ((3, 2), (2, 5)), (3, 5))


@pytest.mark.parametrize(
    "specs",
    [
        None,
        {},
        (),
        [_matmul()],
        _Tuple((_matmul(),)),
        (_Untrusted(),),
        (None,),
        (dict(index=0, kind="matmul"),),
        (_Descriptor(0, "relu", ((3,),), (3,)),),
        tuple(_matmul(index) for index in range(9)),
    ],
)
def test_kernel_collection_rejects_untyped_or_oversized_inputs(specs):
    with pytest.raises(ValueError):
        emit_kernels(specs)


@pytest.mark.parametrize(
    "field,value",
    [
        ("index", True),
        ("index", _Integer(0)),
        ("index", -1),
        ("index", 1),
        ("index", "0"),
        ("index", _Untrusted()),
        ("kind", _Untrusted()),
        ("kind", _Kind.RELU),
        ("kind", "softmax"),
        ("kind", 'relu;system("bad")'),
        ("input_shapes", [[3, 2], [2, 5]]),
        ("input_shapes", _Tuple(((3, 2), (2, 5)))),
        ("input_shapes", ()),
        ("input_shapes", ((3, 2),)),
        ("input_shapes", ((3, 2), (2, 5), (2, 5))),
        ("input_shapes", (_Untrusted(), (2, 5))),
        ("input_shapes", ([3, 2], (2, 5))),
        ("input_shapes", ((3, True), (2, 5))),
        ("input_shapes", ((_Integer(3), 2), (2, 5))),
        ("input_shapes", ((3, "2"), (2, 5))),
        ("input_shapes", ((3, _Untrusted()), (2, 5))),
        ("input_shapes", ((0, 2), (2, 5))),
        ("input_shapes", ((65, 2), (2, 5))),
        ("input_shapes", ((3, 2, 1), (2, 5))),
        ("input_shapes", ((3,), (2, 5))),
        ("input_shapes", ((3, 2), (3, 5))),
        ("output_shape", _Untrusted()),
        ("output_shape", [3, 5]),
        ("output_shape", (3, True)),
        ("output_shape", (3, 4)),
        ("output_shape", (3,)),
        ("output_shape", ()),
    ],
)
def test_descriptor_fields_are_checked_before_rendering(field, value):
    with pytest.raises(ValueError):
        emit_kernels((replace(_matmul(), **{field: value}),))


@pytest.mark.parametrize(
    "spec",
    [
        KernelSpec(0, "relu", ((2, 3), (2, 3)), (2, 3)),
        KernelSpec(0, "relu", ((2, 3),), (3, 2)),
        KernelSpec(0, "relu", ((2, 3, 4),), (2, 3, 4)),
        KernelSpec(0, "sum_axis1", ((4,),), (4,)),
        KernelSpec(0, "sum_axis1", ((4, 3),), (3,)),
        KernelSpec(0, "sum_axis1", ((4, 3),), (4, 1)),
        KernelSpec(0, "sum_axis1", ((4, 3), (4, 3)), (4,)),
    ],
)
def test_unary_descriptors_cannot_change_shape_or_reduction_axis(spec):
    with pytest.raises(ValueError):
        emit_kernels((spec,))


@pytest.mark.parametrize("indices", [(1,), (0, 0), (0, 2), (1, 0)])
def test_symbols_require_unique_contiguous_indices(indices):
    with pytest.raises(ValueError):
        emit_kernels(tuple(_matmul(index) for index in indices))


def test_direct_helper_cannot_bypass_total_scalar_work_limit():
    # Each Matmul entails 64**3 products and 64**3 ordered additions.
    one = KernelSpec(0, "matmul", ((64, 64), (64, 64)), (64, 64))
    assert all(emit_kernels((one,)))
    with pytest.raises(ValueError):
        emit_kernels((one, replace(one, index=1)))


def test_eight_small_kernels_are_valid_and_have_distinct_symbols():
    specs = tuple(KernelSpec(index, "relu", ((64, 64),), (64, 64)) for index in range(8))
    header, c11, cuda = emit_kernels(specs)
    for index in range(8):
        assert header.count(f"void tuc_dag_op_{index}(") == 1
        assert c11.count(f"void tuc_dag_op_{index}(") == 1
        assert cuda.count(f"void tuc_dag_cuda_op_{index}(") == 1
    assert (header, c11, cuda) == emit_kernels(specs)


def test_emitted_arithmetic_requires_separate_binary32_rounding():
    specs = (
        _matmul(),
        KernelSpec(1, "sum_axis1", ((3, 5),), (3,)),
        KernelSpec(2, "relu", ((3,),), (3,)),
    )
    header, c11, cuda = emit_kernels(specs)
    # C volatile stores force products and accumulators back to float; the
    # documented compiler/environment constraints remain caller obligations.
    assert "volatile float product" in c11
    assert c11.count("volatile float value") == 2
    assert "FLT_EVAL_METHOD == 0" in c11
    assert "__FAST_MATH__" in c11
    # CUDA RN intrinsics express the two rounding points directly.
    assert cuda.count("__fmul_rn(") == 1
    assert cuda.count("__fadd_rn(") == 2
    assert "__fmaf" not in cuda
    assert "__CUDA_ARCH__ != 860" in cuda
    assert 'extern "C"' in header


@pytest.mark.parametrize("shape", [(1,), (33,), (1, 1), (33, 5), (64, 64)])
def test_cuda_guards_tail_threads_before_reading_operands(shape):
    _, _, cuda = emit_kernels((KernelSpec(0, "relu", (shape,), shape),))
    function = cuda[cuda.index("__global__ void") :]
    assert function.index("if (index >= ") < function.index("input_0[index]")
    assert "return;" in function[: function.index("input_0[index]")]


@pytest.mark.parametrize("shape", [(1, 1, 1), (2, 3, 5), (33, 7, 5), (64, 64, 64)])
def test_matmul_address_formulas_match_rectangular_extents(shape):
    rows, inner, columns = shape
    _, c11, cuda = emit_kernels(
        (KernelSpec(0, "matmul", ((rows, inner), (inner, columns)), (rows, columns)),)
    )
    # These are ABI address/iteration requirements, not complete text snapshots:
    # a wrong right-hand stride can remain in bounds while computing wrong code.
    for source in (c11, cuda):
        assert f"index / {columns}U" in source
        assert f"index % {columns}U" in source
        assert f"input_0[row * {inner}U + k]" in source
        assert f"input_1[k * {columns}U + column]" in source
        assert f"k < {inner}U" in source
    assert f"index < {rows * columns}U" in c11
    assert f"index >= {rows * columns}U" in cuda
