from . import admin, assistant, auth, documents, notifications, reference, staff, student

# Order matters where paths overlap: /applications/export must be matched before /applications/{id}.
ROUTERS = [
    reference.router,
    auth.router,
    notifications.router,
    admin.router,
    staff.router,
    student.router,
    documents.router,
    assistant.router,
]
