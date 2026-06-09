"""Convert canonical Source Intent IR into schema-versioned metadata."""

from tuc.frontend import (
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentTensor,
    build_source_intent_metadata_report,
    source_intent_to_triton_metadata,
)


def build_source_intent() -> SourceIntentModule:
    """Build a small data-only Source Intent IR module."""

    return SourceIntentModule(
        name="source_intent_mlp",
        tensors=(
            SourceIntentTensor("a", (8, 16)),
            SourceIntentTensor("b", (16, 4)),
            SourceIntentTensor("c", (8, 4)),
            SourceIntentTensor("y", (8, 4)),
        ),
        operations=(
            SourceIntentOperation(
                name="projection",
                family="matmul",
                inputs=("a", "b"),
                outputs=("c",),
                hints={
                    "max_error_budget": 0.02,
                    "prefer_linear_accelerator": True,
                },
            ),
            SourceIntentOperation(
                name="activation",
                family="elementwise",
                inputs=("c",),
                outputs=("y",),
            ),
        ),
    )


def main() -> None:
    module = build_source_intent()
    metadata = source_intent_to_triton_metadata(module)

    print(build_source_intent_metadata_report(module).dump())
    print()
    print(metadata.intake_report().dump())


if __name__ == "__main__":
    main()
