"""Emit Source-to-Intent parser property corpus evidence."""

from __future__ import annotations

from examples.source_to_intent_corpus import build_source_to_intent_corpus_cases
from tuc.frontend import (
    build_source_to_intent_corpus_report,
    build_source_to_intent_property_corpus_report,
    dump_source_to_intent_property_corpus_report,
)


def build_report() -> str:
    """Return stable Source-to-Intent property corpus evidence."""

    source_corpus = build_source_to_intent_corpus_report(
        build_source_to_intent_corpus_cases()
    )
    return dump_source_to_intent_property_corpus_report(
        build_source_to_intent_property_corpus_report(source_corpus)
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
