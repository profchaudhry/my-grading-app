from ui.admin import admin_console
from ui.faculty import faculty_console
from ui.student import student_console

ROUTE_MAP = {
    "admin": admin_console,
    "faculty": faculty_console,
    "student": student_console
}

def route(role):
    console = ROUTE_MAP.get(role)
    if console:
        console()
