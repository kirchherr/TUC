"""Emit the data-only first-proof onboarding evidence report."""

from tuc import build_research_onboarding_report, dump_research_onboarding_report


def build_report() -> str:
    """Return the stable serialized onboarding evidence report."""

    return dump_research_onboarding_report(build_research_onboarding_report())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
