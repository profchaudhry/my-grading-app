"""
CommunicationsService — Announcements, Marquee Tickers, Login Notifications.
Phase 6 / UCS6.0
"""
import logging
from datetime import datetime, timezone
from services.supabase_client import supabase
from services.base_service import BaseService

logger = logging.getLogger("sylemax.communications")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ══════════════════════════════════════════════════════════════════
# TARGETING HELPER
# ══════════════════════════════════════════════════════════════════

def _matches_target(row: dict, user_id: str, role: str,
                    enrolled_course_ids: list[str]) -> bool:
    """Return True if a comms row is visible to this user."""
    ta  = row.get("target_audience", "all")
    tc  = row.get("target_course_id")
    tu  = row.get("target_user_id")

    if ta == "all":
        return True
    if ta == "faculty":
        return role in ("faculty", "faculty_ultra")
    if ta == "faculty_ultra":
        return role == "faculty_ultra"
    if ta == "students":
        return role == "student"
    if ta == "course":
        return tc and tc in enrolled_course_ids
    if ta == "user":
        return tu == user_id
    return False


# ══════════════════════════════════════════════════════════════════
# ANNOUNCEMENTS
# ══════════════════════════════════════════════════════════════════

class AnnouncementService(BaseService):

    # ── Admin / faculty_ultra: get all ────────────────────────────
    @staticmethod
    def get_all(created_by: str | None = None) -> list:
        try:
            q = supabase.table("announcements")\
                .select(
                    "*, creator:created_by(id,first_name,last_name,full_name,email),"
                    "course:target_course_id(name,code),"
                    "target_user:target_user_id(id,first_name,last_name,full_name,email)"
                )\
                .order("created_at", desc=True)
            if created_by:
                q = q.eq("created_by", created_by)
            r = q.execute()
            return r.data or []
        except Exception:
            logger.exception("get_all announcements failed")
            return []

    # ── For a specific user (filtered + active) ───────────────────
    @staticmethod
    def get_for_user(user_id: str, role: str,
                     enrolled_course_ids: list[str]) -> list:
        try:
            now = _now_iso()
            r = supabase.table("announcements")\
                .select(
                    "*, course:target_course_id(name,code),"
                    "creator:created_by(first_name,last_name,full_name)"
                )\
                .eq("is_active", True)\
                .or_(f"expires_at.is.null,expires_at.gt.{now}")\
                .order("pinned", desc=True)\
                .order("created_at", desc=True)\
                .execute()
            rows = r.data or []
            return [row for row in rows
                    if _matches_target(row, user_id, role, enrolled_course_ids)]
        except Exception:
            logger.exception("get_for_user announcements failed")
            return []

    # ── Faculty: only for their courses ──────────────────────────
    @staticmethod
    def get_for_faculty_courses(faculty_id: str,
                                course_ids: list[str]) -> list:
        try:
            r = supabase.table("announcements")\
                .select("*, course:target_course_id(name,code)")\
                .eq("created_by", faculty_id)\
                .order("created_at", desc=True)\
                .execute()
            return r.data or []
        except Exception:
            logger.exception("get_for_faculty_courses failed")
            return []

    # ── Create ────────────────────────────────────────────────────
    @staticmethod
    def create(title: str, body: str, created_by: str,
               created_by_role: str, target_audience: str,
               target_course_id: str | None = None,
               target_user_id: str | None = None,
               expires_at: str | None = None,
               pinned: bool = False) -> tuple[bool, str]:
        try:
            row = {
                "title":           title,
                "body":            body,
                "created_by":      created_by,
                "created_by_role": created_by_role,
                "target_audience": target_audience,
                "is_active":       True,
                "pinned":          pinned,
            }
            if target_course_id: row["target_course_id"] = target_course_id
            if target_user_id:   row["target_user_id"]   = target_user_id
            if expires_at:       row["expires_at"]        = expires_at
            r = supabase.table("announcements").insert(row).execute()
            if r.data:
                return True, "Announcement created."
            return False, "Insert returned no data."
        except Exception as e:
            logger.exception("create announcement failed")
            return False, str(e)

    # ── Update ────────────────────────────────────────────────────
    @staticmethod
    def update(ann_id: str, data: dict) -> tuple[bool, str]:
        try:
            r = supabase.table("announcements")\
                .update(data).eq("id", ann_id).execute()
            return (True, "Updated.") if r.data else (False, "No rows updated.")
        except Exception as e:
            logger.exception("update announcement failed")
            return False, str(e)

    @staticmethod
    def toggle_active(ann_id: str, active: bool) -> tuple[bool, str]:
        return AnnouncementService.update(ann_id, {"is_active": active})

    @staticmethod
    def delete(ann_id: str) -> tuple[bool, str]:
        try:
            supabase.table("announcements").delete().eq("id", ann_id).execute()
            return True, "Deleted."
        except Exception as e:
            logger.exception("delete announcement failed")
            return False, str(e)

    # ── Mark read ─────────────────────────────────────────────────
    @staticmethod
    def mark_read(ann_id: str, user_id: str) -> None:
        try:
            supabase.table("announcement_reads").upsert({
                "announcement_id": ann_id,
                "user_id": user_id,
            }, on_conflict="announcement_id,user_id").execute()
        except Exception:
            pass

    @staticmethod
    def get_read_ids(user_id: str) -> set:
        try:
            r = supabase.table("announcement_reads")\
                .select("announcement_id")\
                .eq("user_id", user_id).execute()
            return {row["announcement_id"] for row in (r.data or [])}
        except Exception:
            return set()


# ══════════════════════════════════════════════════════════════════
# MARQUEE TICKERS
# ══════════════════════════════════════════════════════════════════

class MarqueeService(BaseService):

    @staticmethod
    def get_all() -> list:
        try:
            r = supabase.table("marquee_tickers")\
                .select("*, course:target_course_id(name,code),"
                        "target_user:target_user_id(first_name,last_name,full_name)")\
                .order("created_at", desc=True).execute()
            return r.data or []
        except Exception:
            logger.exception("get_all marquee failed")
            return []

    @staticmethod
    def get_active_for_user(user_id: str, role: str,
                            enrolled_course_ids: list[str]) -> list:
        try:
            now = _now_iso()
            r = supabase.table("marquee_tickers")\
                .select("*")\
                .eq("is_active", True)\
                .lte("starts_at", now)\
                .or_(f"ends_at.is.null,ends_at.gt.{now}")\
                .execute()
            rows = r.data or []
            return [row for row in rows
                    if _matches_target(row, user_id, role, enrolled_course_ids)]
        except Exception:
            logger.exception("get_active_for_user marquee failed")
            return []

    @staticmethod
    def create(message: str, created_by: str, target_audience: str,
               target_course_id: str | None = None,
               target_user_id: str | None = None,
               bg_color: str = "#307890", text_color: str = "#ffffff",
               speed: str = "normal",
               starts_at: str | None = None,
               ends_at: str | None = None) -> tuple[bool, str]:
        try:
            row = {
                "message":         message,
                "created_by":      created_by,
                "target_audience": target_audience,
                "bg_color":        bg_color,
                "text_color":      text_color,
                "speed":           speed,
                "is_active":       True,
                "starts_at":       starts_at or _now_iso(),
            }
            if target_course_id: row["target_course_id"] = target_course_id
            if target_user_id:   row["target_user_id"]   = target_user_id
            if ends_at:          row["ends_at"]           = ends_at
            r = supabase.table("marquee_tickers").insert(row).execute()
            return (True, "Ticker created.") if r.data else (False, "Failed.")
        except Exception as e:
            logger.exception("create marquee failed")
            return False, str(e)

    @staticmethod
    def update(ticker_id: str, data: dict) -> tuple[bool, str]:
        try:
            r = supabase.table("marquee_tickers")\
                .update(data).eq("id", ticker_id).execute()
            return (True, "Updated.") if r.data else (False, "No rows.")
        except Exception as e:
            return False, str(e)

    @staticmethod
    def delete(ticker_id: str) -> tuple[bool, str]:
        try:
            supabase.table("marquee_tickers").delete().eq("id", ticker_id).execute()
            return True, "Deleted."
        except Exception as e:
            return False, str(e)


# ══════════════════════════════════════════════════════════════════
# LOGIN NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════

class NotificationService(BaseService):

    @staticmethod
    def get_all() -> list:
        try:
            r = supabase.table("login_notifications")\
                .select("*, course:target_course_id(name,code),"
                        "target_user:target_user_id(first_name,last_name,full_name)")\
                .order("created_at", desc=True).execute()
            return r.data or []
        except Exception:
            logger.exception("get_all notifications failed")
            return []

    @staticmethod
    def get_pending_for_user(user_id: str, role: str,
                             enrolled_course_ids: list[str]) -> list:
        """Returns notifications not yet seen by this user."""
        try:
            now = _now_iso()
            r = supabase.table("login_notifications")\
                .select("*")\
                .eq("is_active", True)\
                .lte("starts_at", now)\
                .or_(f"ends_at.is.null,ends_at.gt.{now}")\
                .execute()
            rows = r.data or []
            targeted = [row for row in rows
                        if _matches_target(row, user_id, role, enrolled_course_ids)]
            if not targeted:
                return []
            # Filter show_once — exclude already seen
            seen_r = supabase.table("notification_reads")\
                .select("login_notification_id")\
                .eq("user_id", user_id).execute()
            seen_ids = {s["login_notification_id"] for s in (seen_r.data or [])}
            return [row for row in targeted
                    if not row.get("show_once") or row["id"] not in seen_ids]
        except Exception:
            logger.exception("get_pending_for_user failed")
            return []

    @staticmethod
    def mark_seen(notif_id: str, user_id: str) -> None:
        try:
            supabase.table("notification_reads").upsert({
                "login_notification_id": notif_id,
                "user_id": user_id,
            }, on_conflict="login_notification_id,user_id").execute()
        except Exception:
            pass

    @staticmethod
    def create(title: str, message: str, created_by: str,
               target_audience: str, icon: str = "📢",
               target_course_id: str | None = None,
               target_user_id: str | None = None,
               starts_at: str | None = None,
               ends_at: str | None = None,
               show_once: bool = True) -> tuple[bool, str]:
        try:
            row = {
                "title":           title,
                "message":         message,
                "icon":            icon,
                "created_by":      created_by,
                "target_audience": target_audience,
                "is_active":       True,
                "show_once":       show_once,
                "starts_at":       starts_at or _now_iso(),
            }
            if target_course_id: row["target_course_id"] = target_course_id
            if target_user_id:   row["target_user_id"]   = target_user_id
            if ends_at:          row["ends_at"]           = ends_at
            r = supabase.table("login_notifications").insert(row).execute()
            return (True, "Notification created.") if r.data else (False, "Failed.")
        except Exception as e:
            logger.exception("create notification failed")
            return False, str(e)

    @staticmethod
    def update(notif_id: str, data: dict) -> tuple[bool, str]:
        try:
            r = supabase.table("login_notifications")\
                .update(data).eq("id", notif_id).execute()
            return (True, "Updated.") if r.data else (False, "No rows.")
        except Exception as e:
            return False, str(e)

    @staticmethod
    def delete(notif_id: str) -> tuple[bool, str]:
        try:
            supabase.table("login_notifications").delete().eq("id", notif_id).execute()
            return True, "Deleted."
        except Exception as e:
            return False, str(e)
