"""Emit proposal-only Source-to-Intent parser report evidence."""

from __future__ import annotations

from examples.source_to_intent_corpus import build_source_to_intent_corpus_cases
from tuc.frontend import (
    build_source_to_intent_corpus_report,
    build_source_to_intent_parser_report,
    build_source_to_intent_property_corpus_report,
    dump_source_to_intent_parser_report,
)


def build_report() -> str:
    """Return stable proposal-only Source-to-Intent parser report evidence."""

    source_corpus = build_source_to_intent_corpus_report(
        build_source_to_intent_corpus_cases()
    )
    property_corpus = build_source_to_intent_property_corpus_report(source_corpus)
    return dump_source_to_intent_parser_report(
        build_source_to_intent_parser_report(property_corpus)
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
