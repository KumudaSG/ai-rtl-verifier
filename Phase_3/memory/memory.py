# memory.py

import json
import os
import uuid
from datetime import datetime
from typing import Literal, Optional, List

from pydantic import BaseModel


class Lesson(BaseModel):
    condition: str
    action: str
    rationale: str
    generality: Literal[
        "problem_specific",
        "family_specific",
        "domain_general"
    ]


class MemoryEntry(BaseModel):
    entry_id: str
    source_problem_id: str
    problem_features: str
    outcome: Literal["pass", "fail"]
    failure_type: Optional[str]
    lesson: Lesson
    timestamp: str


class MemoryStore:
    def __init__(self, path: str = "memory_dump.json"):
        self.path = path

        if not os.path.exists(self.path):
            with open(self.path, "w") as file:
                json.dump([], file, indent=4)

    def write(self, entry: MemoryEntry) -> None:
        entries = self.read_all()
        entries.append(entry)

        entries_as_dicts = []

        for memory_entry in entries:
            entries_as_dicts.append(memory_entry.model_dump())

        with open(self.path, "w") as file:
            json.dump(entries_as_dicts, file, indent=4)

    def read_all(self) -> List[MemoryEntry]:
        with open(self.path, "r") as file:
            data = json.load(file)

        entries = []

        for item in data:
            entries.append(MemoryEntry(**item))

        return entries

    def read_by_id(self, entry_id: str) -> Optional[MemoryEntry]:
        entries = self.read_all()

        for entry in entries:
            if entry.entry_id == entry_id:
                return entry

        return None

    def clear(self) -> None:
        with open(self.path, "w") as file:
            json.dump([], file, indent=4)
    
    def retrieve(
    self,
    current_problem_id: str,
    current_features: str,
    k: int = 3
    ) -> List[MemoryEntry]:
        if k > 3:
            k = 3

        entries = self.read_all()
        scored_entries = []

        for entry in entries:
            if entry.source_problem_id == current_problem_id:
                continue

            if entry.lesson.generality == "problem_specific":
                continue

            score = self._score_features(current_features, entry.problem_features)

            if score > 0:
                scored_entries.append((score, entry))

        scored_entries.sort(key=lambda pair: pair[0], reverse=True)

        retrieved_entries = []

        for score, entry in scored_entries[:k]:
            retrieved_entries.append(entry)

        return retrieved_entries
    
    def _score_features(self, current_features: str, memory_features: str) -> int:
        current_words = self._clean_words(current_features)
        memory_words = self._clean_words(memory_features)

        matching_words = current_words.intersection(memory_words)

        return len(matching_words)
    
    def _clean_words(self, text: str) -> set:
        text = text.lower()

        for symbol in [",", ".", ":", ";", "(", ")", "/", "-"]:
            text = text.replace(symbol, " ")

        words = set()

        for word in text.split():
            if len(word) > 2:
                words.add(word)

        return words
    
    def _get_family(self, features: str) -> str:
        text = features.lower()

        if "family a" in text:
            return "A"

        if "family b" in text:
            return "B"

        return ""

def create_memory_entry(
    source_problem_id: str,
    problem_features: str,
    outcome: Literal["pass", "fail"],
    failure_type: Optional[str],
    lesson: Lesson
) -> MemoryEntry:
    if outcome == "pass":
        failure_type = None

    return MemoryEntry(
        entry_id=str(uuid.uuid4()),
        source_problem_id=source_problem_id,
        problem_features=problem_features,
        outcome=outcome,
        failure_type=failure_type,
        lesson=lesson,
        timestamp=datetime.now().isoformat()
    )
