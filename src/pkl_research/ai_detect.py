"""Deteksi unsur AI pada teks perusahaan (regex frase, word-boundary)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

AI_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "AI Development",
        re.compile(
            r"\bai\s+(development|developer|dev|solutions?|software|application|apps?)\b"
            r"|\bai[- ]powered\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Artificial Intelligence",
        re.compile(r"\b(artificial intelligence|kecerdasan buatan)\b", re.IGNORECASE),
    ),
    (
        "Machine Learning",
        re.compile(r"\b(machine learning|machine intelligence|neural network)\b", re.IGNORECASE),
    ),
    (
        "Deep Learning",
        re.compile(r"\b(deep learning|tensorflow|pytorch)\b", re.IGNORECASE),
    ),
    (
        "LLM / Generative AI",
        re.compile(
            r"\b(llm|large language model|generative ai|chatgpt|openai|claude|rag|"
            r"retrieval-augmented)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Chatbot / Virtual Assistant",
        re.compile(r"\b(chatbot|chat bot|virtual assistant|ai chat)\b", re.IGNORECASE),
    ),
    (
        "Computer Vision",
        re.compile(
            r"\b(computer vision|object detection|image recognition|facial recognition)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "NLP",
        re.compile(r"\b(nlp|natural language processing)\b", re.IGNORECASE),
    ),
    (
        "Data Science",
        re.compile(r"\bdata science|data scientist|predictive model|predictive analytics\b", re.IGNORECASE),
    ),
    (
        "AI Agent / Automation",
        re.compile(
            r"\b(ai agent|ai agents|intelligent automation|ai automation|ai chatbot)\b",
            re.IGNORECASE,
        ),
    ),
]

_SNIPPET_PAD = 60
_SNIPPET_MAX = 140
_EVIDENCE_LIMIT = 5


@dataclass
class AIDetection:
    ai_focus: bool = False
    subfields: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


def detect_ai(texts: list[str]) -> AIDetection:
    """Deteksi AI pada kumpulan teks (title/meta/homepage/about/dll)."""
    combined = "\n".join(t for t in texts if t)
    subfields: set[str] = set()
    keywords: set[str] = set()
    evidence: list[str] = []

    for label, pattern in AI_PATTERNS:
        for match in pattern.finditer(combined):
            subfields.add(label)
            keywords.add(match.group(0).strip().lower()[:40])
            start = max(0, match.start() - _SNIPPET_PAD)
            end = min(len(combined), match.end() + _SNIPPET_PAD)
            snippet = combined[start:end].replace("\n", " ").strip()
            evidence.append(snippet[:_SNIPPET_MAX])

    return AIDetection(
        ai_focus=bool(subfields),
        subfields=sorted(subfields),
        keywords=sorted(keywords),
        evidence=evidence[:_EVIDENCE_LIMIT],
    )
