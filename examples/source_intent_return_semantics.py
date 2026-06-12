"""Declare Source Intent public return semantics without runtime execution."""

from tuc.frontend import (
    SOURCE_INTENT_SCHEMA_VERSION,
    build_source_intent_return_semantics_report,
    dump_source_intent_return_semantics_report,
    source_intent_from_mapping,
    source_intent_return_aliases,
)


def build_source_intent_return_data() -> dict[str, object]:
    """Return JSON-like Source Intent IR data with explicit public returns."""

    return {
        "name": "source_intent_return_mlp",
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
        "returns": [
            {
                "public_name": "api_y",
                "tensor_name": "y",
                "required": True,
            }
        ],
    }


def build_report() -> str:
    """Return stable Source Intent return semantics evidence."""

    module = source_intent_from_mapping(build_source_intent_return_data())
    report = build_source_intent_return_semantics_report(module)
    return dump_source_intent_return_semantics_report(report)


def build_aliases() -> dict[str, str]:
    """Return the public-name alias map derived from Source Intent returns."""

    module = source_intent_from_mapping(build_source_intent_return_data())
    return source_intent_return_aliases(module)


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
