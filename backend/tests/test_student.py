from sqlalchemy import select

from app.models import Application, AuditLog, Job, Offer, Student

from .conftest import login

API = "/api/v1"


def make_pdf(text: str) -> bytes:
    """A minimal one-page PDF containing `text` (enough for pypdf to extract)."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


def job_id(db, title):
    return db.scalar(select(Job.id).where(Job.title == title))


def test_profile_and_controlled_fields(client, student, db):
    p = client.get(f"{API}/student/profile", headers=student).json()["data"]
    assert p["studentCode"] == "23CSE101" and p["academic"]["cgpaVerified"] is True
    r = client.patch(f"{API}/student/profile", headers=student, json={"placementStatus": "placed"})
    assert r.status_code == 403
    assert db.scalar(select(AuditLog).where(AuditLog.action == "student.update", AuditLog.result == "denied"))


def test_changing_cgpa_resets_verification(client, student):
    r = client.patch(f"{API}/student/profile", headers=student, json={"cgpa": 8.9, "skills": ["Go", "Rust", "go"]})
    data = r.json()["data"]
    assert data["academic"]["cgpa"] == 8.9 and data["academic"]["cgpaVerified"] is False
    assert data["skills"] == ["Go", "Rust"]
    bad = client.patch(f"{API}/student/profile", headers=student, json={"currentYear": 9})
    assert bad.status_code == 422


def test_job_board_tabs_and_eligibility(client, student):
    all_jobs = client.get(f"{API}/jobs", headers=student, params={"pageSize": 50}).json()
    assert all(v["job"]["status"] == "published" for v in all_jobs["data"])
    assert all("eligibility" in v for v in all_jobs["data"])
    applied = client.get(f"{API}/jobs", headers=student, params={"tab": "applied", "pageSize": 50}).json()["data"]
    assert {v["job"]["title"] for v in applied} >= {"Ninja Developer", "Digital Engineer"}
    eligible = client.get(f"{API}/jobs", headers=student, params={"tab": "eligible", "pageSize": 50}).json()["data"]
    assert all(v["eligibility"]["state"] == "eligible" for v in eligible)


def test_student_cannot_see_draft(client, student, db):
    draft = job_id(db, "Advanced App Engineering Analyst")
    assert client.get(f"{API}/jobs/{draft}", headers=student).status_code == 404


def test_apply_rules(client, student, db):
    jid = job_id(db, "Prime Engineer")
    r = client.post(f"{API}/applications", headers=student, json={"jobId": jid})
    assert r.status_code == 201, r.text
    assert r.json()["data"]["application"]["eligibilitySnapshot"]["state"] == "eligible"
    dup = client.post(f"{API}/applications", headers=student, json={"jobId": jid})
    assert dup.status_code == 409
    # L&T is only for MECH/CIVIL/EEE -> not eligible
    lt = client.post(f"{API}/applications", headers=student, json={"jobId": job_id(db, "Graduate Engineer Trainee")})
    assert lt.status_code == 403
    closed = client.post(f"{API}/applications", headers=student, json={"jobId": job_id(db, "Ninja Developer")})
    assert closed.status_code == 409


def test_withdraw_and_reapply(client, student, db):
    app_id = db.scalar(select(Application.id).join(Job).where(Job.title == "Systems Engineer",
                                                               Application.student_id == 1))
    r = client.post(f"{API}/applications/{app_id}/withdraw", headers=student)
    assert r.json()["data"]["application"]["status"] == "withdrawn"
    again = client.post(f"{API}/applications/{app_id}/withdraw", headers=student)
    assert again.status_code == 409


def test_other_students_application_forbidden(client, db):
    other = login(client, "diya.0@campus.demo")
    aarav_app = db.scalar(select(Application.id).join(Student).where(Student.student_code == "23CSE101"))
    assert client.get(f"{API}/applications/{aarav_app}", headers=other).status_code == 403


def test_application_detail_has_timeline_and_offer(client, student, db):
    aarav = db.scalar(select(Student).where(Student.student_code == "23CSE101"))
    ninja = db.scalar(select(Application).join(Job).where(Job.title == "Ninja Developer", Application.student_id == aarav.id))
    d = client.get(f"{API}/applications/{ninja.id}", headers=student).json()["data"]
    assert d["offer"]["status"] == "received"
    assert [h["status"] for h in d["application"]["history"]][-1] == "offer_received"


def test_offer_accept(client, student, db):
    offers = client.get(f"{API}/offers/me", headers=student).json()["data"]
    oid = offers[0]["offer"]["id"]
    r = client.post(f"{API}/offers/{oid}/respond", headers=student, json={"decision": "accepted"})
    assert r.json()["data"]["offer"]["status"] == "accepted"
    assert client.get(f"{API}/student/profile", headers=student).json()["data"]["placementStatus"] == "placed"
    assert client.post(f"{API}/offers/{oid}/respond", headers=student, json={"decision": "declined"}).status_code == 409


def test_dashboard(client, student):
    d = client.get(f"{API}/student/dashboard", headers=student).json()["data"]
    assert d["metrics"]["offers"] == 1 and d["metrics"]["activeApplications"] >= 3
    assert any(e["kind"] == "interview" for e in d["events"])


def test_onboarding(client, db):
    h = login(client, "newstudent@campus.demo")
    me = client.get(f"{API}/auth/me", headers=h).json()["data"]["user"]
    assert me["onboardingComplete"] is False
    body = {"studentCode": "23IT202", "departmentId": 2, "degree": "B.Tech", "currentYear": 4, "graduationYear": 2027,
            "cgpa": 7.8, "skills": ["Python", "SQL", "Java"], "preferredRoles": ["Developer"]}
    r = client.post(f"{API}/student/onboarding", headers=h, json=body)
    assert r.status_code == 200 and r.json()["data"]["onboardingComplete"] is True
    assert client.post(f"{API}/student/onboarding", headers=h, json=body).status_code == 409


def test_reminders_crud(client, student):
    r = client.post(f"{API}/reminders", headers=student, json={"title": "Mock test", "at": "2030-01-01T09:00:00Z"})
    rid = r.json()["data"]["reminder"]["id"]
    assert r.json()["data"]["reminder"]["kind"] == "custom"
    assert client.post(f"{API}/reminders/{rid}/toggle", headers=student).json()["data"]["reminder"]["done"] is True
    other = login(client, "diya.0@campus.demo")
    assert client.delete(f"{API}/reminders/{rid}", headers=other).status_code == 404
    assert client.delete(f"{API}/reminders/{rid}", headers=student).status_code == 200


def test_student_interviews(client, student):
    rows = client.get(f"{API}/interviews", headers=student).json()["data"]
    assert len(rows) == 1 and rows[0]["candidates"] == []


def test_documents_upload_extract_and_access(client, student, faculty, tmp_path, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path))
    pdf = make_pdf("Campus drive circular for Zoho")
    r = client.post(f"{API}/documents", headers=faculty, data={"title": "Zoho circular", "type": "circular"},
                    files={"file": ("circular.pdf", pdf, "application/pdf")})
    assert r.status_code == 201, r.text
    doc = r.json()["data"]
    assert doc["processing"] == "indexed" and doc["pages"] == 1
    detail = client.get(f"{API}/documents/{doc['id']}", headers=student).json()["data"]
    assert "Zoho" in detail["extractedExcerpts"][0]["text"]
    assert client.delete(f"{API}/documents/{doc['id']}", headers=student).status_code == 403

    resume = client.post(f"{API}/documents", headers=student, data={"title": "My resume", "type": "resume"},
                         files={"file": ("cv.pdf", make_pdf("Aarav resume"), "application/pdf")})
    assert resume.status_code == 201
    assert client.get(f"{API}/student/profile", headers=student).json()["data"]["resumeFile"] == "cv.pdf"
    other = login(client, "diya.0@campus.demo")
    assert client.get(f"{API}/documents/{resume.json()['data']['id']}", headers=other).status_code == 404
    bad = client.post(f"{API}/documents", headers=student, data={"title": "x", "type": "resume"},
                      files={"file": ("cv.txt", b"hello", "text/plain")})
    assert bad.status_code == 422
    assert client.get(f"{API}/documents/{resume.json()['data']['id']}/file", headers=student).content.startswith(b"%PDF")
