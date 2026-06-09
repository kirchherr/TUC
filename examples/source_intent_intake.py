"""Load Source Intent IR from schema-versioned plain data."""

from tuc.frontend import (
    SOURCE_INTENT_SCHEMA_VERSION,
    build_source_intent_intake_report,
    source_intent_from_mapping,
    source_intent_to_triton_metadata,
)


def build_source_intent_data() -> dict[str, object]:
    """Return JSON-like Source Intent IR data."""

    return {
        "name": "source_intent_data_mlp",
        "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
        "tensors": [
            {"name": "a", "shape": [4, 8]},
            {"name": "b", "shape": [8, 2]},
            {"name": "c", "shape": [4, 2]},
            {"name": "y", "shape": [4, 2]},
        ],
        "operations": [
            {
                "name": "projection",
                "family": "matmul",
                "inputs": ["a", "b"],
                "outputs": ["c"],
                "hints": {
                    "max_error_budget": 0.02,
                    "prefer_linear_accelerator": True,
                },
            },
            {
                "name": "activation",
                "family": "elementwise",
                "inputs": ["c"],
                "outputs": ["y"],
            },
        ],
    }


def main() -> None:
    module = source_intent_from_mapping(build_source_intent_data())
    metadata = source_intent_to_triton_metadata(module)

    print(build_source_intent_intake_report(module).dump())
    print()
    print(module.dump())
    print()
    print(metadata.intake_report().dump())


if __name__ == "__main__":
    main()
