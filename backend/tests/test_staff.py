from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import Application, AuditLog, Company, Job, Notification, Student

from .conftest import login

API = "/api/v1"


def future(days=10, hours=0):
    return (datetime.now(timezone.utc) + timedelta(days=days, hours=hours)).isoformat()


def job_body(company_id, **over):
    body = {
        "companyId": company_id, "title": "Graduate Analyst", "location": "Chennai", "type": "Full-time",
        "description": "Analyse things", "skills": ["SQL"],
        "eligibility": {"minCgpa": 7, "maxActiveArrears": 0, "departmentIds": [], "graduationYears": [2027]},
        "rounds": [{"name": "Aptitude", "mode": "Online"}, {"name": "HR", "mode": "On-campus"}],
        "ctcLpa": 6.5, "openDate": future(-1), "deadline": future(7), "driveDate": future(12), "status": "draft",
    }
    body.update(over)
    return body


def app_of(db, code, title):
    return db.scalar(select(Application).join(Student).join(Job).where(Student.student_code == code, Job.title == title))


def test_student_cannot_use_staff_endpoints(client, student):
    assert client.get(f"{API}/companies", headers=student).status_code == 403
    assert client.get(f"{API}/applications", headers=student).status_code == 403


def test_company_crud_and_archive_rules(client, faculty, db):
    body = {"name": "Acme Labs", "website": "https://acme.example", "industry": "R&D", "tier": "dream"}
    r = client.post(f"{API}/companies", headers=faculty, json=body)
    assert r.status_code == 201
    cid = r.json()["data"]["id"]
    assert client.post(f"{API}/companies", headers=faculty, json={**body, "name": "acme labs"}).status_code == 409
    tcs = db.scalar(select(Company.id).where(Company.name == "TCS"))
    assert client.post(f"{API}/companies/{tcs}/archive", headers=faculty, json={"archived": True}).status_code == 409
    assert client.post(f"{API}/companies/{cid}/archive", headers=faculty, json={"archived": True}).json()["data"]["archivedAt"]
    listed = client.get(f"{API}/companies", headers=faculty).json()
    assert "Acme Labs" not in [c["company"]["name"] for c in listed["data"]] and listed["meta"]["industries"]


def test_job_create_publish_lifecycle(client, faculty, db):
    tcs = db.scalar(select(Company.id).where(Company.name == "TCS"))
    r = client.post(f"{API}/jobs", headers=faculty, json=job_body(tcs))
    assert r.status_code == 201, r.text
    job = r.json()["data"]
    assert job["status"] == "draft" and [x["name"] for x in job["rounds"]] == ["Aptitude", "HR"]
    jid = job["id"]
    assert client.post(f"{API}/jobs/{jid}/status", headers=faculty, json={"status": "closed"}).status_code == 409
    assert client.post(f"{API}/jobs/{jid}/status", headers=faculty, json={"status": "published"}).json()["data"]["status"] == "published"
    assert client.post(f"{API}/jobs/{jid}/archive", headers=faculty, json={"archived": True}).status_code == 409
    no_reason = client.post(f"{API}/jobs/{jid}/status", headers=faculty, json={"status": "cancelled"})
    assert no_reason.status_code == 422
    assert client.post(f"{API}/jobs/{jid}/status", headers=faculty, json={"status": "cancelled", "reason": "Freeze"}).status_code == 200
    assert client.put(f"{API}/jobs/{jid}", headers=faculty, json=job_body(tcs)).status_code == 409


def test_unpublish_refused_with_applicants(client, faculty, db):
    jid = db.scalar(select(Job.id).where(Job.title == "Digital Engineer"))
    r = client.post(f"{API}/jobs/{jid}/status", headers=faculty, json={"status": "draft"})
    assert r.status_code == 409


def test_job_edit_updates_rounds_and_audits(client, faculty, db):
    tcs = db.scalar(select(Company.id).where(Company.name == "TCS"))
    jid = client.post(f"{API}/jobs", headers=faculty, json=job_body(tcs)).json()["data"]["id"]
    r = client.put(f"{API}/jobs/{jid}", headers=faculty, json=job_body(tcs, title="Senior Analyst", rounds=[{"name": "Coding", "mode": "Virtual"}]))
    assert r.json()["data"]["title"] == "Senior Analyst" and len(r.json()["data"]["rounds"]) == 1
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "job.update"))
    assert "title" in entry.reason


def test_deadline_before_open_rejected(client, faculty, db):
    tcs = db.scalar(select(Company.id).where(Company.name == "TCS"))
    r = client.post(f"{API}/jobs", headers=faculty, json=job_body(tcs, deadline=future(-3)))
    assert r.status_code == 422


def test_students_directory_masks_phone_and_audits(client, faculty, admin, db):
    rows = client.get(f"{API}/students", headers=faculty, params={"q": "Aarav"}).json()["data"]
    assert "•" in rows[0]["phone"]
    assert "•" not in client.get(f"{API}/students", headers=admin, params={"q": "Aarav"}).json()["data"][0]["phone"]
    client.get(f"{API}/students/{rows[0]['id']}", headers=faculty)
    assert db.scalar(select(AuditLog).where(AuditLog.action == "student.view"))
    hi = client.get(f"{API}/students", headers=faculty, params={"minCgpa": 9}).json()["data"]
    assert all(s["academic"]["cgpa"] >= 9 for s in hi)


def test_verify_cgpa_notifies(client, faculty, db):
    s = db.scalar(select(Student).where(Student.student_code == "23CSE101"))
    client.patch(f"{API}/student/profile", headers=login(client, "student@campus.demo"), json={"cgpa": 8.6})
    r = client.post(f"{API}/students/{s.id}/verify-cgpa", headers=faculty, json={})
    assert r.json()["data"]["academic"]["cgpaVerified"] is True
    assert db.scalar(select(Notification).where(Notification.title == "Your CGPA has been verified"))


def test_stage_changes_forward_only_and_bulk(client, faculty, db):
    zoho = app_of(db, "23CSE101", "Software Developer")      # shortlisted
    infy = app_of(db, "23CSE101", "Systems Engineer")        # applied
    ninja = app_of(db, "23CSE101", "Ninja Developer")        # offer received
    r = client.post(f"{API}/applications/stage", headers=faculty, json={"ids": [zoho.id, infy.id, ninja.id], "status": "interview"})
    data = r.json()["data"]
    assert set(data["updated"]) == {str(zoho.id), str(infy.id)}
    assert data["failed"][0]["id"] == str(ninja.id)
    back = client.post(f"{API}/applications/stage", headers=faculty, json={"ids": [zoho.id], "status": "shortlisted"})
    assert back.json()["data"]["failed"]
    rej = client.post(f"{API}/applications/stage", headers=faculty, json={"ids": [ninja.id], "status": "rejected"})
    assert "offer" in rej.json()["data"]["failed"][0]["reason"].lower()


def test_exception_required_for_ineligible_snapshot(client, faculty, db):
    app = app_of(db, "23CSE101", "Systems Engineer")  # status: applied
    app.snapshot.state = "not_eligible"
    db.commit()
    r = client.post(f"{API}/applications/stage", headers=faculty, json={"ids": [app.id], "status": "shortlisted"})
    assert "exception" in r.json()["data"]["failed"][0]["reason"]
    r = client.post(f"{API}/applications/stage", headers=faculty, json={
        "ids": [app.id], "status": "shortlisted", "exception": {"reason": "Strong portfolio", "approvedBy": "HOD CSE"}})
    assert r.json()["data"]["updated"] == [str(app.id)]
    assert db.scalar(select(AuditLog).where(AuditLog.action == "eligibility.exception"))


def test_applications_export_csv(client, faculty, db):
    r = client.get(f"{API}/applications/export", headers=faculty)
    text = r.json()["data"]
    assert text.startswith('"Student ID"') and "Aarav Menon" in text
    assert db.scalar(select(AuditLog).where(AuditLog.action == "report.export"))


def test_interview_scheduling_rules(client, faculty, db):
    zoho = app_of(db, "23CSE101", "Software Developer")  # shortlisted
    infy = app_of(db, "23CSE101", "Systems Engineer")    # only applied
    body = {"jobId": zoho.job_id, "applicationIds": [zoho.id], "round": "Technical", "at": future(5), "durationMins": 60, "location": "Lab 1"}
    r = client.post(f"{API}/interviews", headers=faculty, json=body)
    assert r.status_code == 201, r.text
    iid = r.json()["data"]["interview"]["id"]
    bad = client.post(f"{API}/interviews", headers=faculty, json={**body, "applicationIds": [infy.id]})
    assert bad.status_code == 422
    # Aarav already has a TCS interview in 2 days at 10:00 UTC -> clash
    tcs = app_of(db, "23CSE101", "Digital Engineer")
    clash_at = (datetime.now(timezone.utc) + timedelta(days=2)).replace(hour=10, minute=15, second=0, microsecond=0).isoformat()
    clash = client.post(f"{API}/interviews", headers=faculty, json={**body, "jobId": tcs.job_id, "applicationIds": [tcs.id], "at": clash_at})
    assert clash.status_code == 409
    assert client.post(f"{API}/interviews/{iid}/status", headers=faculty, json={"status": "completed"}).status_code == 409
    assert client.post(f"{API}/interviews/{iid}/notify", headers=faculty).json()["data"]["notified"] == 1
    assert client.post(f"{API}/interviews/{iid}/status", headers=faculty, json={"status": "cancelled"}).status_code == 200


def test_offer_issue_and_status(client, faculty, db):
    zoho = app_of(db, "23CSE101", "Software Developer")
    client.post(f"{API}/applications/stage", headers=faculty, json={"ids": [zoho.id], "status": "selected"})
    listing = client.get(f"{API}/offers", headers=faculty).json()
    assert any(a["application"]["id"] == str(zoho.id) for a in listing["meta"]["selectedWithoutOffer"])
    r = client.post(f"{API}/offers", headers=faculty, json={"applicationId": zoho.id, "ctcLpa": 8.4, "acceptBy": future(14)})
    assert r.status_code == 201, r.text
    oid = r.json()["data"]["offer"]["id"]
    assert client.post(f"{API}/offers", headers=faculty, json={"applicationId": zoho.id, "ctcLpa": 8.4, "acceptBy": future(14)}).status_code == 409
    assert client.post(f"{API}/offers/{oid}/status", headers=faculty, json={"status": "withdrawn"}).status_code == 422
    assert client.post(f"{API}/offers/{oid}/status", headers=faculty, json={"status": "accepted"}).json()["data"]["offer"]["status"] == "accepted"
    assert client.post(f"{API}/offers/{oid}/status", headers=faculty, json={"status": "declined"}).status_code == 409


def test_dashboard_and_reports(client, faculty):
    d = client.get(f"{API}/faculty/dashboard", headers=faculty).json()["data"]
    assert d["metrics"]["totalApplications"] > 0 and d["deptChart"]
    r = client.get(f"{API}/reports/placement", headers=faculty).json()["data"]
    assert r["kpis"]["uniqueStudentsPlaced"] == 4 and len(r["monthly"]) == 12
    csv_text = client.get(f"{API}/reports/placement/export.csv", headers=faculty).json()["data"]
    assert csv_text.count("\n") >= 5
