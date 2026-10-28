"""Documents: upload, text extraction (for the assistant's search), replace, reprocess, delete.

Who sees what:
  * personal documents (resume, certificate) belong to one student: only that student and staff can open them;
  * placement documents (circular, brochure, eligibility) are uploaded by staff with `documents.upload` and are
    visible to the roles in `access_roles` (students only when the linked job is not a draft).
Files are stored on local disk under UPLOAD_DIR with a random name; the original name is kept for display.
"""
import io
import re
import uuid
import zipfile
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import utcnow
from ..deps import ensure_permission, is_staff
from ..enums import PERSONAL_DOCUMENT_TYPES, DocumentType, JobStatus, ProcessingStatus, RoleName
from ..errors import Forbidden, NotFound, ValidationFailed
from ..models import Company, Document, DocumentChunk, Job, Student, User
from ..serializers import document_dict
from . import audit
from .common import like, student_of
from .profile import compute_completion

CHUNK_CHARS = 1000
ALLOWED = {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


# ---------------------------------------------------------------- storage + extraction
def upload_root() -> Path:
    root = Path(get_settings().upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def file_path(doc: Document) -> Path:
    return upload_root() / doc.storage_key


def _check_file(name: str, data: bytes, allowed_ext: tuple[str, ...]) -> str:
    ext = Path(name or "").suffix.lower()
    if ext not in allowed_ext:
        raise ValidationFailed(f"Upload a {' or '.join(e.upper().lstrip('.') for e in allowed_ext)} file.", field="file")
    if not data:
        raise ValidationFailed("The file is empty.", field="file")
    if len(data) > get_settings().max_upload_mb * 1024 * 1024:
        raise ValidationFailed(f"The file is larger than {get_settings().max_upload_mb} MB.", field="file")
    if ext == ".pdf" and not data.startswith(b"%PDF"):
        raise ValidationFailed("This does not look like a PDF file.", field="file")
    if ext == ".docx" and not data.startswith(b"PK"):
        raise ValidationFailed("This does not look like a Word (.docx) file.", field="file")
    return ext


def extract_pages(data: bytes, ext: str) -> list[str]:
    """Plain text per page (a .docx is treated as one page)."""
    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return [(page.extract_text() or "") for page in reader.pages]
    if ext == ".docx":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        xml = re.sub(r"</w:p>", "\n", xml)
        return [re.sub(r"<[^>]+>", "", xml)]
    return []


def _index(db: Session, doc: Document, data: bytes, ext: str) -> None:
    doc.chunks.clear()
    db.flush()
    try:
        pages = extract_pages(data, ext)
    except Exception:
        doc.processing, doc.pages = ProcessingStatus.FAILED, 0
        return
    index = 0
    for number, text in enumerate(pages, start=1):
        text = re.sub(r"[ \t]+", " ", text).strip()
        for start in range(0, len(text), CHUNK_CHARS):
            doc.chunks.append(DocumentChunk(page=number, chunk_index=index, text=text[start:start + CHUNK_CHARS]))
            index += 1
    doc.pages = len(pages)
    doc.processing = ProcessingStatus.INDEXED if index else ProcessingStatus.FAILED


def _store(db: Session, doc: Document, name: str, data: bytes, ext: str) -> None:
    old = doc.storage_key
    doc.storage_key = f"{uuid.uuid4().hex}{ext}"
    doc.file_name = Path(name).name[:255]
    doc.size_kb = max(1, round(len(data) / 1024))
    file_path(doc).write_bytes(data)
    if old:
        (upload_root() / old).unlink(missing_ok=True)
    doc.processing = ProcessingStatus.PROCESSING
    _index(db, doc, data, ext)


# ---------------------------------------------------------------- access
def _student_id(db: Session, user: User) -> int | None:
    return student_of(db, user).id if user.role_name == RoleName.STUDENT else None


def can_read(db: Session, user: User, doc: Document) -> bool:
    if doc.owner_student_id:
        return is_staff(user) or doc.owner_student_id == _student_id(db, user)
    if user.role_name not in (doc.access_roles or []):
        return False
    if user.role_name == RoleName.STUDENT and doc.job and doc.job.status == JobStatus.DRAFT:
        return False
    return True


def can_manage(db: Session, user: User, doc: Document) -> bool:
    if doc.owner_student_id:
        return doc.owner_student_id == _student_id(db, user) or user.role_name == RoleName.ADMIN
    return is_staff(user) and user.can("documents.upload")


def _get(db: Session, user: User, doc_id: int) -> Document:
    doc = db.get(Document, doc_id)
    if not doc or not can_read(db, user, doc):
        raise NotFound("Document not found.")
    return doc


def view(db: Session, user: User, doc: Document, excerpts: bool = False) -> dict:
    out = document_dict(doc, with_excerpts=excerpts)
    out["canManage"] = can_manage(db, user, doc)
    return out


# ---------------------------------------------------------------- operations
def list_documents(db: Session, user: User, doc_type: str | None, q: str | None, mine: bool, page: int, page_size: int):
    query = select(Document)
    if user.role_name == RoleName.STUDENT:
        sid = _student_id(db, user)
        query = query.where(or_(Document.owner_student_id == sid, Document.owner_student_id.is_(None)))
        if mine:
            query = query.where(Document.owner_student_id == sid)
    else:
        query = query.where(Document.owner_student_id.is_(None))
    if doc_type:
        query = query.where(Document.doc_type == doc_type)
    if q:
        query = query.outerjoin(Company, Company.id == Document.company_id).where(
            or_(Document.title.ilike(like(q)), Company.name.ilike(like(q))))
    query = query.order_by(Document.created_at.desc(), Document.id.desc())
    # access_roles is JSON; filter it in Python so this works the same on MySQL and SQLite.
    rows = [d for d in db.scalars(query).unique().all() if can_read(db, user, d)]
    total = len(rows)
    rows = rows[(page - 1) * page_size: page * page_size]
    return [view(db, user, d) for d in rows], total


def detail(db: Session, user: User, doc_id: int) -> dict:
    return view(db, user, _get(db, user, doc_id), excerpts=True)


def upload(db: Session, user: User, *, title: str, doc_type: str, file_name: str, data: bytes,
           company_id: int | None, job_id: int | None, visible_to_students: bool) -> dict:
    title = (title or "").strip()
    if not 1 <= len(title) <= 120:
        raise ValidationFailed("Give the document a title (up to 120 characters).", field="title")
    try:
        kind = DocumentType(doc_type)
    except ValueError:
        raise ValidationFailed("Unknown document type.", field="type")

    if user.role_name == RoleName.STUDENT:
        if kind not in PERSONAL_DOCUMENT_TYPES:
            raise Forbidden("Students can upload a resume or a certificate.")
        ext = _check_file(file_name, data, (".pdf", ".docx"))
        student = student_of(db, user)
        doc = Document(title=title, doc_type=kind, uploaded_by=user.id, owner_student_id=student.id, access_roles=["student"])
    else:
        ensure_permission(db, user, "documents.upload")
        if kind in PERSONAL_DOCUMENT_TYPES:
            raise ValidationFailed("Staff upload circulars, brochures or eligibility documents.", field="type")
        ext = _check_file(file_name, data, (".pdf",))
        if company_id and not db.get(Company, company_id):
            raise ValidationFailed("Unknown company.", field="companyId")
        job = db.get(Job, job_id) if job_id else None
        if job_id and not job:
            raise ValidationFailed("Unknown job.", field="jobId")
        if job and company_id and job.company_id != company_id:
            raise ValidationFailed("That job belongs to another company.", field="jobId")
        roles = ["faculty", "admin"] + (["student"] if visible_to_students else [])
        doc = Document(title=title, doc_type=kind, uploaded_by=user.id, company_id=company_id or (job.company_id if job else None),
                       job_id=job_id, access_roles=roles)
    db.add(doc)
    db.flush()
    _store(db, doc, file_name, data, ext)
    if kind == DocumentType.RESUME:
        s = student_of(db, user)
        s.resume_file = doc.file_name
        s.profile_completion = compute_completion(s)
    audit.record(db, "document.upload", f"Document {doc.id} · {doc.title}", actor=user)
    db.commit()
    return view(db, user, doc)


def replace(db: Session, user: User, doc_id: int, file_name: str, data: bytes) -> dict:
    doc = _get(db, user, doc_id)
    if not can_manage(db, user, doc):
        raise Forbidden("You cannot replace this document.")
    ext = _check_file(file_name, data, (".pdf", ".docx") if doc.owner_student_id else (".pdf",))
    _store(db, doc, file_name, data, ext)
    doc.version += 1
    doc.updated_at = utcnow()
    audit.record(db, "document.replace", f"Document {doc.id} · v{doc.version}", actor=user)
    db.commit()
    return view(db, user, doc)


def reprocess(db: Session, user: User, doc_id: int) -> dict:
    doc = _get(db, user, doc_id)
    if not (is_staff(user) and can_manage(db, user, doc)):
        raise Forbidden("You cannot reprocess this document.")
    path = file_path(doc)
    if not path.exists():
        raise NotFound("The stored file is missing.")
    _index(db, doc, path.read_bytes(), path.suffix.lower())
    audit.record(db, "document.reprocess", f"Document {doc.id}", actor=user)
    db.commit()
    return view(db, user, doc)


def remove(db: Session, user: User, doc_id: int) -> None:
    doc = _get(db, user, doc_id)
    if not can_manage(db, user, doc):
        raise Forbidden("You cannot delete this document.")
    if doc.doc_type == DocumentType.RESUME and doc.owner_student_id:
        s = db.get(Student, doc.owner_student_id)
        if s and s.resume_file == doc.file_name:
            s.resume_file = None
    file_path(doc).unlink(missing_ok=True)
    audit.record(db, "document.delete", f"Document {doc.id} · {doc.title}", actor=user)
    db.delete(doc)
    db.commit()


def open_file(db: Session, user: User, doc_id: int) -> tuple[Path, str, str]:
    doc = _get(db, user, doc_id)
    path = file_path(doc)
    if not path.exists():
        raise NotFound("The stored file is missing.")
    return path, ALLOWED.get(path.suffix.lower(), "application/octet-stream"), doc.file_name or path.name
