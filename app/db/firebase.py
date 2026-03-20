"""
Firebase / Firestore integration.

Initialises the Firebase Admin SDK once at startup and exposes
`get_firestore_session()` as a FastAPI dependency that returns a
`FirestoreSession` – a thin wrapper that provides add / flush / commit /
delete / refresh and targeted query helpers so the rest of the app can
stay largely unchanged.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import firebase_admin
from firebase_admin import credentials, firestore

from app.core.config import settings

if TYPE_CHECKING:
    from google.cloud.firestore_v1 import Client as FirestoreClient

logger = logging.getLogger(__name__)

_firebase_app: firebase_admin.App | None = None


def init_firebase() -> None:
    global _firebase_app
    if _firebase_app is not None:
        return
    if settings.google_application_credentials:
        cred = credentials.Certificate(settings.google_application_credentials)
        logger.info("Firebase initialised with service-account: %s", settings.google_application_credentials)
    else:
        cred = credentials.ApplicationDefault()
        logger.info("Firebase initialised with Application Default Credentials")
    _firebase_app = firebase_admin.initialize_app(
        cred, {"projectId": settings.firebase_project_id or None}
    )


def get_firestore_client() -> "FirestoreClient":
    return firestore.client()


# ---------------------------------------------------------------------------
# FirestoreSession
# ---------------------------------------------------------------------------

class FirestoreSession:
    """
    Mimics just enough of the SQLAlchemy Session interface so the orchestrator
    and repositories can work without a full rewrite.

    Writes are buffered locally and flushed in a single Firestore batch on
    commit() / flush().  Deletes are also batched.
    """

    def __init__(self, client: "FirestoreClient") -> None:
        self._db = client
        # (collection_name, doc_id, data_dict)
        self._pending_writes: list[tuple[str, str, dict]] = []
        # (collection_name, doc_id)
        self._pending_deletes: list[tuple[str, str]] = []

    # ── write helpers ──────────────────────────────────────────────────────

    def add(self, obj) -> None:
        """Stage a model object for upsert."""
        self._pending_writes.append((obj.__tablename__, obj.id, obj._to_firestore()))

    def flush(self) -> None:
        """Write all staged operations to Firestore in batches of 500."""
        items = list(self._pending_writes)
        deletes = list(self._pending_deletes)
        self._pending_writes.clear()
        self._pending_deletes.clear()

        ops = [("set", col, did, data) for col, did, data in items] + \
              [("del", col, did, None) for col, did in deletes]

        for chunk_start in range(0, max(len(ops), 1), 500):
            chunk = ops[chunk_start: chunk_start + 500]
            if not chunk:
                break
            batch = self._db.batch()
            for op, col, did, data in chunk:
                ref = self._db.collection(col).document(did)
                if op == "set":
                    batch.set(ref, data, merge=True)
                else:
                    batch.delete(ref)
            batch.commit()

    def commit(self) -> None:
        self.flush()

    def delete(self, obj) -> None:
        """Stage a model object for deletion."""
        self._pending_deletes.append((obj.__tablename__, obj.id))

    def refresh(self, obj) -> None:
        """Reload a model object's attributes from Firestore."""
        doc = self._db.collection(obj.__tablename__).document(obj.id).get()
        if doc.exists:
            obj._update_from_firestore(doc.to_dict())

    # ── read helpers ───────────────────────────────────────────────────────

    def get(self, model_class, doc_id: str):
        """Fetch a single document by ID; returns None if not found."""
        doc = self._db.collection(model_class.__tablename__).document(doc_id).get()
        if not doc.exists:
            return None
        return model_class._from_firestore(doc.id, doc.to_dict())

    def query_by_job_id(self, model_class, job_id: str) -> list:
        """Return all documents in a collection where job_id == job_id."""
        docs = (
            self._db.collection(model_class.__tablename__)
            .where("job_id", "==", job_id)
            .stream()
        )
        return [model_class._from_firestore(d.id, d.to_dict()) for d in docs]

    def query_by_project_id(self, model_class, project_id: str) -> list:
        docs = (
            self._db.collection(model_class.__tablename__)
            .where("project_id", "==", project_id)
            .stream()
        )
        return [model_class._from_firestore(d.id, d.to_dict()) for d in docs]

    def query_selected_clips(self, job_id: str) -> list:
        """Return ClipCandidates for a job where selected == True."""
        from app.models.clip import ClipCandidate
        docs = (
            self._db.collection(ClipCandidate.__tablename__)
            .where("job_id", "==", job_id)
            .where("selected", "==", True)
            .stream()
        )
        return [ClipCandidate._from_firestore(d.id, d.to_dict()) for d in docs]

    # ── bulk delete helpers ────────────────────────────────────────────────

    def delete_by_job_id(
        self,
        model_class,
        job_id: str,
        asset_types: list[str] | None = None,
    ) -> None:
        """
        Delete all documents in model_class's collection where job_id matches.
        Optionally restrict to documents whose `asset_type` is in asset_types.
        """
        q = self._db.collection(model_class.__tablename__).where("job_id", "==", job_id)
        batch = self._db.batch()
        count = 0
        for doc in q.stream():
            if asset_types is not None and doc.to_dict().get("asset_type") not in asset_types:
                continue
            batch.delete(doc.reference)
            count += 1
            if count % 500 == 0:
                batch.commit()
                batch = self._db.batch()
        if count % 500 != 0:
            batch.commit()

    def delete_transcript_for_job(self, job_id: str) -> None:
        """Delete all transcript segments and their words for a job."""
        from app.models.transcript import TranscriptSegment, TranscriptWord
        # Collect segment IDs first
        seg_ids = []
        batch = self._db.batch()
        count = 0
        for doc in (
            self._db.collection(TranscriptSegment.__tablename__)
            .where("job_id", "==", job_id)
            .stream()
        ):
            seg_ids.append(doc.id)
            batch.delete(doc.reference)
            count += 1
            if count % 500 == 0:
                batch.commit()
                batch = self._db.batch()
        if count % 500 != 0:
            batch.commit()

        # Delete associated words
        batch = self._db.batch()
        count = 0
        for seg_id in seg_ids:
            for doc in (
                self._db.collection(TranscriptWord.__tablename__)
                .where("segment_id", "==", seg_id)
                .stream()
            ):
                batch.delete(doc.reference)
                count += 1
                if count % 500 == 0:
                    batch.commit()
                    batch = self._db.batch()
        if count % 500 != 0:
            batch.commit()


# ── FastAPI dependency ─────────────────────────────────────────────────────

def get_firestore_session() -> FirestoreSession:
    return FirestoreSession(get_firestore_client())
