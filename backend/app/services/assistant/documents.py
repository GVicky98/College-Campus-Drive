"""Keyword search over the extracted text of documents the user may read.

Excerpts are returned to the model marked as untrusted data. Once a reply has read document text,
no change can be prepared in that same reply (see framework.run_tool).
"""
import re

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ...enums import ProcessingStatus
from ...models import Document, DocumentChunk, User
from ..common import like
from ..documents_service import can_read


def search(db: Session, user: User, query: str, limit: int) -> list[dict]:
    terms = list(dict.fromkeys(re.findall(r"[a-z0-9+#&.]{3,}", query.lower())))[:8]
    if not terms:
        return []
    rows = db.execute(
        select(DocumentChunk, Document).join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.processing == ProcessingStatus.INDEXED, or_(*[DocumentChunk.text.ilike(like(t)) for t in terms]))
        .limit(300)
    ).all()
    hits = []
    for chunk, doc in rows:
        if not can_read(db, user, doc):
            continue
        low = chunk.text.lower()
        score = sum(low.count(t) for t in terms)
        first = min((low.find(t) for t in terms if t in low), default=0)
        start = max(0, first - 120)
        excerpt = re.sub(r"\s+", " ", re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", chunk.text[start:start + 600])).strip()
        hits.append((score, doc.id, chunk.page, {"documentId": str(doc.id), "title": doc.title, "type": doc.doc_type,
                                                  "page": chunk.page, "excerpt": excerpt}))
    hits.sort(key=lambda h: (-h[0], h[1], h[2]))
    return [h[3] for h in hits[:limit]]
