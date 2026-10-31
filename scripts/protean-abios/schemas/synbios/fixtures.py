"""Lifecycle fixtures for ABIOS/3 bench and tests."""
from __future__ import annotations

import copy
import hashlib
import re
from typing import Any

from canonical import ForgeMessage

FIXTURE_PROJECT = "a1" * 16
FIXTURE_TASK = "b2" * 16
FIXTURE_AGENT = "c3" * 16
FIXTURE_HUMAN = "d4" * 16
FIXTURE_ARTIFACT = "e5" * 16
FIXTURE_REVISION = "a" * 40
FIXTURE_DIGEST = "b" * 64

_HEX32 = re.compile(r"^[0-9a-f]{32}$")


def _random_hex(seed: int, label: str, n_hex: int) -> str:
    digest = hashlib.sha256(f"{seed}:{label}".encode("utf-8")).hexdigest()
    return digest[:n_hex]


def _replace_hex_values(obj: Any, mapping: dict[str, str]) -> Any:
    if isinstance(obj, str):
        if obj in mapping:
            return mapping[obj]
        if _HEX32.fullmatch(obj) and len(obj) >= 32 and obj in mapping:
            return mapping[obj]
        return obj
    if isinstance(obj, list):
        return [_replace_hex_values(x, mapping) for x in obj]
    if isinstance(obj, dict):
        return {k: _replace_hex_values(v, mapping) for k, v in obj.items()}
    return obj


def remap_fixture_hex(messages: list[ForgeMessage], seed: int) -> list[ForgeMessage]:
    """Deterministic random hex for every fixture hex string (32+ chars), per tokenpage study."""
    mapping = {
        FIXTURE_PROJECT: _random_hex(seed, "project", 32),
        FIXTURE_TASK: _random_hex(seed, "task", 32),
        FIXTURE_AGENT: _random_hex(seed, "agent", 32),
        FIXTURE_HUMAN: _random_hex(seed, "human", 32),
        FIXTURE_ARTIFACT: _random_hex(seed, "artifact", 32),
        FIXTURE_REVISION: _random_hex(seed, "revision", 40),
        FIXTURE_DIGEST: _random_hex(seed, "digest", 64),
    }
    out: list[ForgeMessage] = []
    for action, payload in messages:
        cloned = copy.deepcopy(payload)
        out.append((action, _replace_hex_values(cloned, mapping)))
    return out


def lifecycle_hex_aliases(seed: int | None = None) -> dict[str, str]:
    if seed is None:
        return {"v": FIXTURE_REVISION, "g": FIXTURE_DIGEST}
    return {
        "v": _random_hex(seed, "revision", 40),
        "g": _random_hex(seed, "digest", 64),
    }


def lifecycle_session_ids(seed: int | None = None) -> dict[str, str]:
    if seed is None:
        return {
            "project_id": FIXTURE_PROJECT,
            "task_id": FIXTURE_TASK,
            "agent_id": FIXTURE_AGENT,
            "human_id": FIXTURE_HUMAN,
            "artifact_id": FIXTURE_ARTIFACT,
        }
    return {
        "project_id": _random_hex(seed, "project", 32),
        "task_id": _random_hex(seed, "task", 32),
        "agent_id": _random_hex(seed, "agent", 32),
        "human_id": _random_hex(seed, "human", 32),
        "artifact_id": _random_hex(seed, "artifact", 32),
    }


def lifecycle_11_random(seed: int = 1) -> list[ForgeMessage]:
    return remap_fixture_hex(lifecycle_11(), seed)


def lifecycle_40_random(seed: int = 1) -> list[ForgeMessage]:
    return remap_fixture_hex(lifecycle_40(), seed)


def lifecycle_200_random(seed: int = 1) -> list[ForgeMessage]:
    return remap_fixture_hex(lifecycle_200(), seed)


def lifecycle_11() -> list[ForgeMessage]:
    project = FIXTURE_PROJECT
    task = FIXTURE_TASK
    agent = FIXTURE_AGENT
    artifact = FIXTURE_ARTIFACT
    revision = FIXTURE_REVISION
    digest = FIXTURE_DIGEST
    return [
        ("project.create", {"name": "Commons starter", "description": "Agent-first forge pilot.", "repository": "https://example.invalid/commons"}),
        ("principal.create", {"name": "Build agent", "kind": "agent"}),
        ("principal.create", {"name": "Independent reviewer", "kind": "human"}),
        ("task.create", {
            "project_id": project,
            "title": "Wire SYM-2P codec",
            "description": "Encode forge commands as SYM-2P v1 packets.",
            "criteria": ["Round-trip lossless", "Validator exit 0"],
            "scope": ["synbios/sym2p"],
            "priority": "high",
            "dependencies": [],
        }),
        ("grant.create", {"principal_id": agent, "task_id": task, "capabilities": ["claim", "work", "artifact", "evidence", "submit"]}),
        ("task.claim", {"task_id": task}),
        ("task.transition", {"task_id": task, "status": "in_progress"}),
        ("artifact.add", {
            "task_id": task,
            "title": "SYM-2P codec module",
            "kind": "git_commit",
            "revision": revision,
            "digest": digest,
            "uri": "https://example.invalid/commit",
            "summary": "Implement forge packet codec.",
        }),
        ("evidence.add", {
            "task_id": task,
            "artifact_id": artifact,
            "artifact_digest": digest,
            "revision": revision,
            "kind": "test",
            "status": "passed",
            "command": "python -m unittest discover -s tests -v",
            "summary": "Unit tests passed locally.",
            "tool": "python",
            "tool_version": "3.11",
            "assumptions": ["Reported by agent; not executed by forge."],
        }),
        ("task.transition", {"task_id": task, "status": "in_review"}),
        ("review.create", {
            "task_id": task,
            "artifact_id": artifact,
            "revision": revision,
            "decision": "approved",
            "comment": "Independent human acceptance.",
        }),
    ]


def lifecycle_40() -> list[ForgeMessage]:
    """Extended transcript with repeated bodies, refs, and status churn."""
    base = lifecycle_11()
    project = FIXTURE_PROJECT
    task = FIXTURE_TASK
    agent = FIXTURE_AGENT
    artifact = FIXTURE_ARTIFACT
    revision = FIXTURE_REVISION
    digest = FIXTURE_DIGEST
    shared_spec = (
        "Acceptance criteria: round-trip all forge commands through SYM-3 encoders; "
        "bench must beat JSON on repeated large fields."
    )
    extra: list[ForgeMessage] = []
    for i in range(1, 16):
        extra.append(
            (
                "evidence.add",
                {
                    "task_id": task,
                    "artifact_id": artifact,
                    "artifact_digest": digest,
                    "revision": revision,
                    "kind": "test",
                    "status": "passed" if i % 3 else "failed",
                    "command": "python -m unittest discover -s tests -v",
                    "summary": shared_spec,
                    "tool": "python",
                    "tool_version": "3.14",
                    "assumptions": ["CI not executed in transcript."],
                },
            )
        )
    extra.append(("task.transition", {"task_id": task, "status": "in_review"}))
    extra.append(
        (
            "artifact.add",
            {
                "task_id": task,
                "title": "SYM-3 bench harness",
                "kind": "git_commit",
                "revision": revision,
                "digest": digest,
                "uri": "https://example.invalid/sym3",
                "summary": shared_spec,
            },
        )
    )
    extra.append(("grant.create", {"principal_id": agent, "task_id": task, "capabilities": ["claim", "work"]}))
    while len(base) + len(extra) < 40:
        extra.append(
            (
                "evidence.add",
                {
                    "task_id": task,
                    "artifact_id": artifact,
                    "artifact_digest": digest,
                    "revision": revision,
                    "kind": "test",
                    "status": "passed",
                    "command": "python -m unittest discover -s tests -v",
                    "summary": shared_spec,
                    "tool": "python",
                    "tool_version": "3.14",
                    "assumptions": ["Synthetic bench filler."],
                },
            )
        )
    return base + extra[: 40 - len(base)]


def lifecycle_200() -> list[ForgeMessage]:
    """Deterministic 200-message transcript: repeat lifecycle_40 segments five times."""
    chunk = lifecycle_40()
    out: list[ForgeMessage] = list(chunk)
    # Append four more full cycles (40 * 5 = 200).
    for cycle in range(1, 5):
        for action, payload in chunk:
            # Clone payload so cycles do not share mutable lists.
            cloned = {k: (list(v) if isinstance(v, list) else v) for k, v in payload.items()}
            if action == "evidence.add":
                cloned["summary"] = f"{cloned['summary']} (cycle {cycle + 1})"
            out.append((action, cloned))
    assert len(out) == 200
    return out

