"""Upload chunk points to Qdrant."""

from __future__ import annotations

import os

from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

UPLOAD_PARALLEL = 2
UPLOAD_MAX_RETRIES = 3


def upsert_points(
    client: QdrantClient,
    collection_name: str,
    points: list[PointStruct],
) -> None:
    """Upload points to the target collection."""
    if not points:
        return
    cpu_count = os.cpu_count() or 4
    n = len(points)
    batch_size = min(256, max(32, n // max(cpu_count * 2, 1)))
    client.upload_points(
        collection_name=collection_name,
        points=points,
        batch_size=batch_size,
        wait=True,
        parallel=UPLOAD_PARALLEL,
        max_retries=UPLOAD_MAX_RETRIES,
    )
