from typing import Dict, List

ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "admin": ["manage_users", "approve_faculty", "view_courses", "view_dashboard", "update_profile"],
    "faculty": ["view_courses", "update_profile", "view_dashboard"],
    "faculty_ultra": ["view_courses", "update_profile", "view_dashboard", "upro_grade"],
    "student": ["view_dashboard"],
}

VALID_ROLES: List[str] = list(ROLE_PERMISSIONS.keys())  # includes faculty_ultra


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, [])
