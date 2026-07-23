"""Shared test doubles for the LLM provider. No test makes real calls."""

import json
import re

from app.llm.provider import LLMRateLimited

CANNED_QUERIES = [
    {"query": "best towel under 30 dollars", "intent_type": "budget"},
    {"query": "towel that fits a gym bag", "intent_type": "use_case"},
    {"query": "is it certified organic", "intent_type": "trust"},
]

CANNED_EVALUATIONS = [
    {
        "query": "best towel under 30 dollars",
        "would_surface": True,
        "confidence": 0.9,
        "missing_info": [],
        "reason": "price fits the budget",
    },
    {
        "query": "towel that fits a gym bag",
        "would_surface": False,
        "confidence": 0.7,
        "missing_info": ["usage_scenario", "dimensions"],
        "reason": "no usage context in the data",
    },
    {
        "query": "is it certified organic",
        "would_surface": False,
        "confidence": 0.6,
        "missing_info": ["certifications"],
        "reason": "no certifications listed",
    },
]


class FakeProvider:
    """Returns canned JSON keyed off the system prompt. Rewrites echo the
    requested attributes: certifications stay null with a needs_human
    note, everything else gets a specific value."""

    def __init__(self):
        self.calls = []

    def complete(self, system, user, json_mode=False):
        self.calls.append((system, user, json_mode))
        if "shopping queries" in system:
            return json.dumps({"queries": CANNED_QUERIES})
        if "retrieval and reasoning" in system:
            return json.dumps({"evaluations": CANNED_EVALUATIONS})
        if "rewrite" in system:
            match = re.search(r"missing or vague: (.+)$", user, re.MULTILINE)
            names = [n.strip() for n in match.group(1).split(",")]
            rewrites = []
            for name in names:
                if name == "certifications":
                    rewrites.append(
                        {
                            "attribute": name,
                            "value": None,
                            "needs_human": "certification documents required",
                        }
                    )
                else:
                    rewrites.append(
                        {
                            "attribute": name,
                            "value": f"specific rewritten {name} content",
                            "needs_human": None,
                        }
                    )
            return json.dumps({"rewrites": rewrites})
        raise AssertionError(f"unexpected system prompt: {system[:60]}")


class RateLimitedProvider:
    def complete(self, system, user, json_mode=False):
        raise LLMRateLimited("daily cap simulated")
