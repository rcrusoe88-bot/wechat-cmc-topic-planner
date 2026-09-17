#!/usr/bin/env python3
"""Calculate the fixed relevance score and default action for a topic candidate."""

from __future__ import annotations

import argparse
import json
import sys


def parse_axis(value: str) -> int | str:
    if value.upper() == "X":
        return "X"
    try:
        score = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("axis scores must be 0-4 or X") from exc
    if score < 0 or score > 4:
        raise argparse.ArgumentTypeError("axis scores must be 0-4 or X")
    return score


def parse_evidence(value: str) -> int:
    try:
        score = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("evidence score must be 0, 1, 3, or 4") from exc
    if score not in {0, 1, 3, 4}:
        raise argparse.ArgumentTypeError("evidence score must be 0, 1, 3, or 4")
    return score


def relevance_result(mrna_cmc: int | str, lnp_delivery: int | str, evidence: int) -> dict:
    if mrna_cmc == "X" or lnp_delivery == "X":
        return {
            "mrna_cmc": mrna_cmc,
            "lnp_delivery": lnp_delivery,
            "relevance_score": None,
            "relevance_tier": "provisional",
            "eligible_for_formal_pool": False,
            "evidence_score": evidence,
            "default_action": "complete_evidence",
            "reason": "At least one axis is X; do not impute a score.",
        }

    strong = max(mrna_cmc, lnp_delivery)
    weak = min(mrna_cmc, lnp_delivery)
    score = round(100 * (0.75 * strong + 0.25 * weak) / 4, 1)
    eligible = strong == 4 or (mrna_cmc >= 3 and lnp_delivery >= 3)

    if score >= 90:
        tier = "dual_core"
    elif score >= 75:
        tier = "core_candidate"
    elif score >= 60:
        tier = "bridge_candidate"
    else:
        tier = "rejected"

    if not eligible or tier == "rejected":
        action = "reject_or_background"
    elif evidence <= 1:
        action = "watch_pending_verification"
    elif tier == "bridge_candidate":
        action = "bridge_watch_only"
    elif evidence >= 3:
        action = "deep_dive_or_topic_pool"
    else:
        action = "manual_review"

    return {
        "mrna_cmc": mrna_cmc,
        "lnp_delivery": lnp_delivery,
        "relevance_score": score,
        "relevance_tier": tier,
        "eligible_for_formal_pool": eligible,
        "evidence_score": evidence,
        "default_action": action,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calculate the fixed relevance score for a wechat-cmc-topic-planner candidate."
    )
    parser.add_argument("--mrna-cmc", required=True, type=parse_axis, help="mRNA CMC axis: 0-4 or X")
    parser.add_argument(
        "--lnp-delivery", required=True, type=parse_axis, help="LNP delivery axis: 0-4 or X"
    )
    parser.add_argument(
        "--evidence",
        required=True,
        type=parse_evidence,
        help="Evidence score: A=4, B=3, C=1, D=0",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            relevance_result(args.mrna_cmc, args.lnp_delivery, args.evidence),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
