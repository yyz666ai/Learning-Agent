import json
from pathlib import Path


def validate_maps(curriculum: Path) -> dict[str, object]:
    maps = sorted(curriculum.glob("*/concept-map.json"))
    nodes: dict[str, dict] = {}
    languages: list[str] = []
    for path in maps:
        data = json.loads(path.read_text(encoding="utf-8"))
        languages.append(data["language"])
        for node in data["concepts"]:
            concept_id = node["id"]
            if concept_id in nodes:
                raise ValueError(f"duplicate concept id: {concept_id}")
            if not node.get("outcomes"):
                raise ValueError(f"missing outcomes: {concept_id}")
            if "common_misconceptions" not in node:
                raise ValueError(f"missing misconceptions: {concept_id}")
            nodes[concept_id] = node
    for concept_id, node in nodes.items():
        for prerequisite in node.get("prerequisites", []):
            if prerequisite not in nodes:
                raise ValueError(
                    f"unknown prerequisite {prerequisite} for {concept_id}"
                )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(concept_id: str) -> None:
        if concept_id in visiting:
            raise ValueError(f"cycle detected at {concept_id}")
        if concept_id in visited:
            return
        visiting.add(concept_id)
        for prerequisite in nodes[concept_id].get("prerequisites", []):
            visit(prerequisite)
        visiting.remove(concept_id)
        visited.add(concept_id)

    for concept_id in nodes:
        visit(concept_id)
    return {"languages": sorted(languages), "concept_count": len(nodes)}
