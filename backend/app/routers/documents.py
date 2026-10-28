"""/documents: upload (multipart form), list, detail with extracted text, replace, reprocess, download, delete."""
from typing import Literal

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import Field

from ..deps import CurrentUser, Db
from ..enums import DocumentType
from ..schemas.common import PageParams, ok, paged
from ..services import documents_service as docs

router = APIRouter(prefix="/documents", tags=["documents"])


class DocQuery(PageParams):
    type: DocumentType | None = None
    q: str | None = Field(None, max_length=100)
    mine: Literal["true", "false"] | None = None


@router.get("")
def list_documents(request: Request, user: CurrentUser, db: Db):
    query = DocQuery.from_query(request.query_params)
    items, total = docs.list_documents(db, user, query.type, query.q, query.mine == "true", query.page, query.page_size)
    return paged(items, total, query.page, query.page_size)


@router.post("", status_code=201)
async def upload(
    user: CurrentUser,
    db: Db,
    file: UploadFile = File(...),
    title: str = Form(...),
    type: str = Form(...),
    company_id: int | None = Form(None, alias="companyId"),
    job_id: int | None = Form(None, alias="jobId"),
    visible_to_students: bool = Form(True, alias="visibleToStudents"),
):
    data = await file.read()
    return ok(docs.upload(db, user, title=title, doc_type=type, file_name=file.filename or "", data=data,
                          company_id=company_id, job_id=job_id, visible_to_students=visible_to_students))


@router.get("/{doc_id}")
def detail(doc_id: int, user: CurrentUser, db: Db):
    return ok(docs.detail(db, user, doc_id))


@router.get("/{doc_id}/file")
def download(doc_id: int, user: CurrentUser, db: Db):
    path, media_type, name = docs.open_file(db, user, doc_id)
    return FileResponse(path, media_type=media_type, filename=name, content_disposition_type="inline")


@router.post("/{doc_id}/replace")
async def replace(doc_id: int, user: CurrentUser, db: Db, file: UploadFile = File(...)):
    return ok(docs.replace(db, user, doc_id, file.filename or "", await file.read()))


@router.post("/{doc_id}/reprocess")
def reprocess(doc_id: int, user: CurrentUser, db: Db):
    return ok(docs.reprocess(db, user, doc_id))


@router.delete("/{doc_id}")
def remove(doc_id: int, user: CurrentUser, db: Db):
    docs.remove(db, user, doc_id)
    return ok({"ok": True})
