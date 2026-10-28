"""Starter questions shown in the chat, per role and filtered by the user's permissions."""
from ...enums import RoleName
from ...models import User

STUDENT = [
    "Generate my placement report",
    "Show a chart of my applications by status",
    "Show a chart of how many open jobs I am eligible for",
    "Which jobs am I eligible for?",
    "Why am I not eligible for a job I'm interested in?",
    "What is the status of my applications?",
    "Do I have any interviews coming up?",
    "What offers do I have, and by when must I respond?",
    "Recommend jobs that match my skills and interests",
    "What do the latest placement circulars say?",
    "Remind me a day before the next deadline to update my resume",
]

# (text, permissions — the user needs at least one; empty = always shown)
STAFF = {
    RoleName.FACULTY: [
        ("Generate a placement summary report", ("reports.view",)),
        ("Generate a student directory report for CSE", ("students.view",)),
        ("Add a new company", ("companies.manage",)),
        ("Show a pie chart of placed vs unplaced students", ("students.view", "reports.view")),
        ("Show offers by department as a bar chart", ("reports.view",)),
        ("Show monthly applications and offers as a line chart", ("reports.view",)),
        ("List students with a CGPA above 8", ("students.view",)),
        ("Which students are eligible for our latest open job?", ("students.view",)),
        ("Summarise applicants by stage for the jobs I manage", ("applications.review",)),
        ("What interviews are scheduled this week?", ("applications.review",)),
        ("How are offers distributed by department?", ("offers.manage", "reports.view")),
        ("What does the latest company circular say?", ()),
        ("Which hiring drives need attention?", ("reports.view", "applications.review")),
    ],
    RoleName.ADMIN: [
        ("Generate a placement summary report", ("reports.view",)),
        ("Create a faculty account", ("users.manage",)),
        ("Show and update the placement policies", ("policies.manage",)),
        ("Add a new company", ("companies.manage",)),
        ("Show a pie chart of placed vs unplaced students", ("students.view", "reports.view")),
        ("Show placement rate by department as a bar chart", ("reports.view",)),
        ("Show monthly applications and offers as a line chart", ("reports.view",)),
        ("List all students with their placement status", ("students.view",)),
        ("Show the faculty accounts", ("users.manage",)),
        ("Give me an overview of placement statistics", ("reports.view",)),
        ("What are the current placement policies?", ()),
        ("Summarise recruitment activity and trends", ("reports.view", "applications.review")),
        ("Are there any administrative alerts?", ()),
        ("Show recent denied access attempts", ("audit.view",)),
        ("How are offers distributed by department?", ("offers.manage", "reports.view")),
    ],
}


def for_user(user: User) -> list[str]:
    if user.role_name == RoleName.STUDENT:
        return STUDENT
    return [text for text, perms in STAFF[user.role_name] if not perms or any(user.can(p) for p in perms)]
