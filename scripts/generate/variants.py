"""Generation variants derived from the feature manifest.

A variant is one set of Copier answers. The set is built from features.py, so
adding a feature to the manifest adds its variants everywhere they are used
(the offline checker, bake.py and the template CI matrix) with no extra edits:

- ``minimal``: the default base, every optional feature off.
- ``full``: every feature that has a question switched on.
- ``only-<feature>``: one feature on, plus the parents it needs.
- ``without-<feature>``: ``full`` minus one feature and every feature under it.

Variants that resolve to the same feature set are listed once.

Usage:
    python scripts/generate/variants.py            # variant names, one per line
    python scripts/generate/variants.py --matrix   # GitHub Actions matrix JSON
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import features  # noqa: E402


def question_features() -> list[features.Feature]:
    """Features the user can switch on (they have a Copier question)."""
    return [feature for feature in features.FEATURES if feature.question]


def _with_ancestors(names: set[str]) -> set[str]:
    result = set(names)
    for name in names:
        parent = features.FEATURES_BY_NAME[name].parent
        while parent is not None:
            result.add(parent)
            parent = features.FEATURES_BY_NAME[parent].parent
    return result


def _with_descendants(names: set[str]) -> set[str]:
    result = set(names)
    changed = True
    while changed:
        changed = False
        for feature in question_features():
            if feature.parent in result and feature.name not in result:
                result.add(feature.name)
                changed = True
    return result


def answers(enabled: set[str]) -> dict:
    """Copier answers (the --features-json payload) for a set of enabled features."""
    unknown = enabled - {feature.name for feature in question_features()}
    if unknown:
        raise ValueError(f"not switchable features: {sorted(unknown)}")
    raw: dict = {"services": "custom" if enabled else "minimal"}
    for feature in question_features():
        raw[feature.question] = feature.name in enabled
    return raw


def all_variants() -> dict[str, dict]:
    """Variant name -> Copier answers, deduplicated by enabled feature set."""
    switchable = [feature.name for feature in question_features()]
    candidates: list[tuple[str, set[str]]] = [("minimal", set()), ("full", set(switchable))]
    for name in switchable:
        candidates.append((f"only-{name}", _with_ancestors({name})))
    for name in switchable:
        candidates.append((f"without-{name}", set(switchable) - _with_descendants({name})))

    variants: dict[str, dict] = {}
    seen: set[frozenset[str]] = set()
    for variant_name, enabled in candidates:
        key = frozenset(enabled)
        if key in seen:
            continue
        seen.add(key)
        variants[variant_name] = answers(enabled)
    return variants


def copier_data_args(raw: dict) -> list[str]:
    """`--data key=value` arguments for `copier copy` that reproduce these answers.

    Always sets `services` first, so the result does not depend on what a bare
    `--defaults` selects (it selects `full`).
    """
    args = ["--data", f"services={raw['services']}"]
    for key, value in raw.items():
        if key != "services" and value:
            args += ["--data", f"{key}=true"]
    return args


def enabled_features(raw: dict) -> list[str]:
    return [feature.name for feature in question_features() if raw[feature.question]]


def computed_features(raw: dict) -> list[str]:
    """Computed features (no question, e.g. redis) that these answers switch on."""
    on = set(enabled_features(raw))
    result = []
    for feature in features.FEATURES:  # manifest order: sources come before what they compute
        if feature.computed_from and any(source in on for source in feature.computed_from):
            on.add(feature.name)
            result.append(feature.name)
    return result


def all_enabled_features(raw: dict) -> list[str]:
    """Every feature these answers switch on: the chosen ones plus the computed ones."""
    return enabled_features(raw) + computed_features(raw)


def matrix() -> dict:
    """GitHub Actions `strategy.matrix` value: one include entry per variant."""
    return {
        "include": [
            {
                "variant": name,
                "data": " ".join(copier_data_args(raw)),
                "features": ",".join(enabled_features(raw)),
                # Computed features (e.g. redis) decide which CI services a bake needs.
                "computed": ",".join(computed_features(raw)),
            }
            for name, raw in all_variants().items()
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--matrix", action="store_true", help="print the GitHub Actions matrix as JSON")
    args = parser.parse_args()
    if args.matrix:
        print(json.dumps(matrix()))
    else:
        print("\n".join(all_variants()))


if __name__ == "__main__":
    main()
