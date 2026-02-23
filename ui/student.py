from core.layout import base_console
from core.guards import require_role
from ui.dashboard import render_dashboard

@require_role(["student"])
def student_console():

    menu = base_console("Student Panel", ["Dashboard"])

    if menu == "Dashboard":
        render_dashboard()
