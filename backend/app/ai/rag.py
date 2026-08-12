import logging
from collections.abc import Callable

from typing import Any

from backend.app.ai.embeddings import Embedder
from backend.app.core.config import get_settings
from backend.app.models import Requirement

logger = logging.getLogger(__name__)


def _search_safe(search: Callable[[list[float]], list[dict]]) -> Callable[[list[float]], list[dict]]:
    """A single failed vector search should cost that one requirement its context, not the
    whole retrieval step."""

    def _run(embedding: list[float]) -> list[dict]:
        try:
            return search(embedding)
        except Exception as exc:  # noqa: BLE001
            logger.warning("pgvector search failed: %s", exc)
            return []

    return _run

_embedder: Embedder | None = None

TOP_K = 4
# Below this cosine similarity two requirements are unrelated enough that feeding one as
# context for the other only adds noise. Calibrated against the embedding model: a genuinely
# related pair scores ~0.80 while an unrelated pair scores ~0.57.
MIN_SIMILARITY = 0.70


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


def embed_and_store(
    requirements: list[Requirement],
    document_id: str,
    repository: Any,
) -> tuple[dict[str, str], list[list[float]]]:
    """Embed each requirement and persist it, with its vector, to Supabase pgvector."""
    if not get_settings().embeddings_enabled:
        # Requirements are still stored for traceability; only the vectors are skipped.
        logger.info("Embeddings disabled; storing requirements without vectors")
        return repository.persist_requirements(document_id, requirements), []
    embedder = get_embedder()
    embeddings = embedder.embed_texts([req.text for req in requirements])
    requirement_id_map = repository.persist_requirements(document_id, requirements)
    repository.persist_chunks(document_id, requirement_id_map, requirements, embeddings)
    return requirement_id_map, embeddings


def retrieve_related(
    requirements: list[Requirement],
    embeddings: list[list[float]],
    requirement_id_map: dict[str, str],
    document_id: str,
    repository: Any,
) -> dict[str, list[Requirement]]:
    """Semantic retrieval: for each requirement, pgvector-search its own embedding against the
    document's stored chunks and return the most similar *other* requirements.

    Matching is done on the database UUID rather than the human-readable REQ-nnn code, because
    that code restarts at REQ-001 on every re-analysis and would otherwise alias onto chunks
    written by a previous run of the same document.
    """
    if not embeddings:
        return {req.id: [] for req in requirements}
    db_id_to_code = {db_id: code for code, db_id in requirement_id_map.items()}
    by_code = {req.id: req for req in requirements}
    related: dict[str, list[Requirement]] = {}

    # Issued sequentially on purpose. The Supabase client wraps a single httpx connection and
    # is not safe to drive from several threads at once - doing so produced intermittent
    # "Server disconnected" failures mid-analysis. Measured cost is ~0.15s per requirement,
    # which is not worth that risk.
    def _search(embedding: list[float]) -> list[dict]:
        return repository.match_chunks(embedding, document_id, match_count=TOP_K + len(requirements))

    safe_search = _search_safe(_search)
    search_results = [safe_search(embedding) for embedding in embeddings]

    for requirement, matches in zip(requirements, search_results, strict=True):
        self_db_id = requirement_id_map.get(requirement.id)
        neighbours: list[Requirement] = []
        seen: set[str] = set()
        for match in matches:
            match_db_id = match.get("requirement_id")
            if not match_db_id or match_db_id == self_db_id or match_db_id not in db_id_to_code:
                continue
            if (match.get("similarity") or 0) < MIN_SIMILARITY:
                continue
            code = db_id_to_code[match_db_id]
            if code in seen or code not in by_code:
                continue
            seen.add(code)
            neighbours.append(by_code[code])
            if len(neighbours) >= TOP_K:
                break
        related[requirement.id] = neighbours

    retrieved = sum(len(v) for v in related.values())
    logger.info("RAG retrieval: %d related requirements across %d requirements", retrieved, len(requirements))
    return related
