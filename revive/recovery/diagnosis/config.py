"""Diagnosis configuration and versioning."""

from __future__ import annotations

from dataclasses import dataclass

DIAGNOSTIC_VERSION = "0.5.0-m5"


@dataclass(frozen=True, slots=True)
class DiagnosisConfig:
    diagnostic_version: str = DIAGNOSTIC_VERSION
    allow_llm: bool = False  # M5 deterministic-only; LLM deferred


def default_diagnosis_config() -> DiagnosisConfig:
    return DiagnosisConfig()
