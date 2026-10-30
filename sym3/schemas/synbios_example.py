"""Synbios forge command field sets (example schema for bench and conformance tests).

SYM-3 encoders are schema-driven: another deployment can swap this module for its
own command vocabulary while keeping wire format, lexicon, and session rules.
"""

from __future__ import annotations

COMMAND_FIELDS: dict[str, set[str]] = {
    "project.create": {"name", "description", "repository"},
    "principal.create": {"name", "kind"},
    "principal.revoke": {"principal_id"},
    "grant.create": {"principal_id", "task_id", "capabilities"},
    "grant.revoke": {"grant_id"},
    "task.create": {
        "project_id",
        "title",
        "description",
        "criteria",
        "scope",
        "priority",
        "dependencies",
    },
    "task.claim": {"task_id"},
    "task.transition": {"task_id", "status"},
    "artifact.add": {"task_id", "title", "kind", "revision", "digest", "uri", "summary"},
    "evidence.add": {
        "task_id",
        "artifact_id",
        "artifact_digest",
        "revision",
        "kind",
        "status",
        "command",
        "summary",
        "tool",
        "tool_version",
        "assumptions",
    },
    "review.create": {"task_id", "artifact_id", "revision", "decision", "comment"},
}
