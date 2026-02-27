"""
UCS6.0 Communications UI
- Admin: full management of announcements, marquee tickers, login notifications
- Faculty / Faculty Ultra: manage announcements for their courses
- All users: view announcements feed (called from their console)
- Marquee + popup notifications injected globally via render_comms_widgets()
"""
import streamlit as st
from datetime import datetime, timedelta, timezone
from services.communications_service import (
    AnnouncementService, MarqueeService, NotificationService
)
from services.course_service import CourseService
from services.supabase_client import supabase
from ui.styles import page_header, section_header, BRAND


# ── Helpers ───────────────────────────────────────────────────────

def _pname(p: dict) -> str:
    if not p:
        return "—"
    return (p.get("full_name") or
            f"{p.get('first_name','')} {p.get('last_name','')}").strip() or \
           p.get("email", "—")


def _fmt_dt(dt_str: str | None) -> str:
    if not dt_str:
        return "—"
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %H:%M")
    except Exception:
        return dt_str[:16]


def _audience_label(row: dict) -> str:
    ta = row.get("target_audience", "all")
    labels = {
        "all":           "🌐 Everyone",
        "faculty":       "👨‍🏫 Faculty",
        "faculty_ultra": "⭐ Faculty Ultra",
        "students":      "🎓 Students",
        "course":        f"📚 {(row.get('course') or {}).get('code','Course')}",
        "user":          f"👤 {_pname(row.get('target_user') or {})}",
    }
    return labels.get(ta, ta)


def _get_all_users() -> list:
    try:
        r = supabase.table("profiles")\
            .select("id,first_name,last_name,full_name,email,role")\
            .order("first_name").execute()
        return r.data or []
    except Exception:
        return []


def _get_all_courses() -> list:
    try:
        r = supabase.table("courses")\
            .select("id,name,code").order("code").execute()
        return r.data or []
    except Exception:
        return []


def _date_input_row(prefix: str) -> tuple[str | None, str | None]:
    """Returns (starts_at_iso, ends_at_iso) from two date inputs."""
    c1, c2 = st.columns(2)
    starts = c1.date_input("Start Date", value=datetime.now(timezone.utc).date(),
                            key=f"{prefix}_start")
    ends   = c2.date_input("End Date (optional)", value=None,
                            key=f"{prefix}_end")
    starts_iso = datetime.combine(starts, datetime.min.time())\
                         .replace(tzinfo=timezone.utc).isoformat() if starts else None
    ends_iso   = datetime.combine(ends, datetime.max.time().replace(microsecond=0))\
                         .replace(tzinfo=timezone.utc).isoformat() if ends else None
    return starts_iso, ends_iso


def _target_selector(prefix: str, include_course: bool = True,
                     courses: list | None = None,
                     users: list | None = None) -> tuple[str, str | None, str | None]:
    """Returns (target_audience, target_course_id, target_user_id)."""
    audience_opts = {
        "🌐 All Users":        "all",
        "👨‍🏫 Faculty":          "faculty",
        "⭐ Faculty Ultra":    "faculty_ultra",
        "🎓 Students":         "students",
    }
    if include_course:
        audience_opts["📚 Specific Course"] = "course"
    audience_opts["👤 Specific User"] = "user"

    sel_label = st.selectbox("Target Audience", list(audience_opts.keys()),
                              key=f"{prefix}_audience")
    ta = audience_opts[sel_label]
    tc = tu = None

    if ta == "course" and courses:
        course_map = {f"{c['code']} — {c['name']}": c["id"] for c in courses}
        c_sel = st.selectbox("Select Course", list(course_map.keys()),
                              key=f"{prefix}_course_sel")
        tc = course_map[c_sel]

    if ta == "user" and users:
        user_map = {f"{_pname(u)} ({u.get('role','')}) — {u.get('email','')}": u["id"]
                    for u in users}
        u_sel = st.selectbox("Select User", list(user_map.keys()),
                              key=f"{prefix}_user_sel")
        tu = user_map[u_sel]

    return ta, tc, tu


# ══════════════════════════════════════════════════════════════════
# ADMIN COMMUNICATIONS HUB
# ══════════════════════════════════════════════════════════════════

def render_admin_communications(admin_user_id: str) -> None:
    page_header("📣", "Communications", "UCS6.0 — Announcements, Tickers & Notifications")

    tab_ann, tab_mq, tab_notif = st.tabs([
        "📋 Announcements",
        "📰 Marquee Tickers",
        "🔔 Login Notifications",
    ])

    courses = _get_all_courses()
    users   = _get_all_users()

    with tab_ann:
        _admin_announcements(admin_user_id, courses, users)

    with tab_mq:
        _admin_marquee(admin_user_id, courses, users)

    with tab_notif:
        _admin_notifications(admin_user_id, courses, users)


# ── ADMIN: Announcements ──────────────────────────────────────────

def _admin_announcements(admin_id: str, courses: list, users: list) -> None:
    section_header("Create Announcement")

    with st.form("admin_ann_form"):
        title   = st.text_input("Title *", placeholder="e.g. Semester Registration Open")
        body    = st.text_area("Message *", height=120,
                               placeholder="Write your announcement here...")
        ta, tc, tu = _target_selector("adm_ann", courses=courses, users=users)
        c1, c2  = st.columns(2)
        pinned  = c1.checkbox("📌 Pin to top")
        exp_on  = c2.checkbox("Set expiry date")
        expires = None
        if exp_on:
            exp_date = st.date_input("Expires on", key="adm_ann_exp")
            expires  = datetime.combine(exp_date, datetime.max.time().replace(microsecond=0))\
                               .replace(tzinfo=timezone.utc).isoformat()
        submitted = st.form_submit_button("📣 Post Announcement", use_container_width=True)

    if submitted:
        if not title or not body:
            st.error("Title and message are required.")
        else:
            ok, msg = AnnouncementService.create(
                title=title, body=body,
                created_by=admin_id, created_by_role="admin",
                target_audience=ta,
                target_course_id=tc, target_user_id=tu,
                expires_at=expires, pinned=pinned,
            )
            if ok:
                st.success("✅ Announcement posted!")
                st.rerun()
            else:
                st.error(f"Failed: {msg}")

    st.divider()
    section_header("All Announcements")
    rows = AnnouncementService.get_all()
    _render_announcement_list(rows, editable=True)


# ── ADMIN: Marquee ────────────────────────────────────────────────

def _admin_marquee(admin_id: str, courses: list, users: list) -> None:
    section_header("Create Marquee Ticker")

    with st.form("admin_mq_form"):
        message = st.text_input("Ticker Message *",
                                 placeholder="⚡ Important: Registration closes Friday at 5pm!")
        ta, tc, tu = _target_selector("adm_mq", courses=courses, users=users)
        starts_iso, ends_iso = _date_input_row("adm_mq_dt")
        c1, c2, c3 = st.columns(3)
        speed      = c1.selectbox("Speed", ["slow", "normal", "fast"], index=1,
                                   key="adm_mq_speed")
        bg_color   = c2.color_picker("Background Colour", value="#307890",
                                      key="adm_mq_bg")
        txt_color  = c3.color_picker("Text Colour", value="#ffffff",
                                      key="adm_mq_txt")
        submitted  = st.form_submit_button("📰 Create Ticker", use_container_width=True)

    if submitted:
        if not message:
            st.error("Ticker message is required.")
        else:
            ok, msg = MarqueeService.create(
                message=message, created_by=admin_id,
                target_audience=ta, target_course_id=tc, target_user_id=tu,
                bg_color=bg_color, text_color=txt_color, speed=speed,
                starts_at=starts_iso, ends_at=ends_iso,
            )
            if ok:
                st.success("✅ Ticker created!")
                st.rerun()
            else:
                st.error(f"Failed: {msg}")

    st.divider()
    section_header("All Marquee Tickers")
    rows = MarqueeService.get_all()
    _render_marquee_list(rows)


# ── ADMIN: Login Notifications ────────────────────────────────────

def _admin_notifications(admin_id: str, courses: list, users: list) -> None:
    section_header("Create Login Notification")

    ICONS = ["📢", "⚠️", "ℹ️", "🎉", "📅", "🔔", "✅", "❗"]

    with st.form("admin_notif_form"):
        title   = st.text_input("Notification Title *",
                                 placeholder="e.g. System Maintenance Tonight")
        message = st.text_area("Message *", height=100,
                                placeholder="Details of the notification...")
        c1, c2  = st.columns([1, 3])
        icon    = c1.selectbox("Icon", ICONS, key="adm_notif_icon")
        ta, tc, tu = _target_selector("adm_notif", courses=courses, users=users)
        starts_iso, ends_iso = _date_input_row("adm_notif_dt")
        show_once = st.checkbox("Show once per user (don't show again after dismissed)",
                                 value=True)
        submitted = st.form_submit_button("🔔 Create Notification", use_container_width=True)

    if submitted:
        if not title or not message:
            st.error("Title and message are required.")
        else:
            ok, msg = NotificationService.create(
                title=title, message=message, created_by=admin_id,
                target_audience=ta, icon=icon,
                target_course_id=tc, target_user_id=tu,
                starts_at=starts_iso, ends_at=ends_iso,
                show_once=show_once,
            )
            if ok:
                st.success("✅ Notification created!")
                st.rerun()
            else:
                st.error(f"Failed: {msg}")

    st.divider()
    section_header("All Login Notifications")
    rows = NotificationService.get_all()
    _render_notification_list(rows)


# ══════════════════════════════════════════════════════════════════
# FACULTY / FACULTY ULTRA COMMUNICATIONS
# ══════════════════════════════════════════════════════════════════

def render_faculty_communications(faculty_user_id: str, role: str) -> None:
    page_header("📣", "Communications", "Post announcements for your courses")

    # Get courses assigned to this faculty
    assignments = CourseService.get_faculty_courses(faculty_user_id)
    if not assignments:
        st.info("You have no assigned courses. Announcements can only be posted for your courses.")
        return

    courses = [a["courses"] for a in assignments if a.get("courses")]

    section_header("Create Course Announcement")

    with st.form("fac_ann_form"):
        title      = st.text_input("Title *", placeholder="e.g. Assignment 2 deadline extended")
        body       = st.text_area("Message *", height=120)
        course_map = {f"{c['code']} — {c['name']}": c["id"] for c in courses}
        c_sel      = st.selectbox("Course *", list(course_map.keys()), key="fac_ann_course")
        tc         = course_map[c_sel]
        pinned     = st.checkbox("📌 Pin to top")
        submitted  = st.form_submit_button("📣 Post Announcement", use_container_width=True)

    if submitted:
        if not title or not body:
            st.error("Title and message are required.")
        else:
            ok, msg = AnnouncementService.create(
                title=title, body=body,
                created_by=faculty_user_id, created_by_role=role,
                target_audience="course",
                target_course_id=tc,
                pinned=pinned,
            )
            if ok:
                st.success("✅ Announcement posted to course!")
                st.rerun()
            else:
                st.error(f"Failed: {msg}")

    st.divider()
    section_header("My Announcements")
    rows = AnnouncementService.get_for_faculty_courses(
        faculty_user_id, [c["id"] for c in courses]
    )
    _render_announcement_list(rows, editable=True, created_by_filter=faculty_user_id)


# ══════════════════════════════════════════════════════════════════
# STUDENT ANNOUNCEMENTS FEED
# ══════════════════════════════════════════════════════════════════

def render_student_announcements(user_id: str, role: str,
                                  enrolled_course_ids: list[str]) -> None:
    page_header("📋", "Announcements", "Notices and updates from your institution")

    rows = AnnouncementService.get_for_user(user_id, role, enrolled_course_ids)
    read_ids = AnnouncementService.get_read_ids(user_id)

    if not rows:
        st.info("No announcements at this time.")
        return

    # Mark all visible as read
    for row in rows:
        if row["id"] not in read_ids:
            AnnouncementService.mark_read(row["id"], user_id)

    for row in rows:
        _render_announcement_card(row, show_audience=False, unread=row["id"] not in read_ids)


# ══════════════════════════════════════════════════════════════════
# GLOBAL WIDGETS — marquee + login popup
# Called from app.py after login, before routing
# ══════════════════════════════════════════════════════════════════

def render_comms_widgets(user_id: str, role: str,
                          enrolled_course_ids: list[str]) -> None:
    """Inject marquee ticker and popup notification if applicable."""
    _render_marquee_widget(user_id, role, enrolled_course_ids)
    _render_login_popup(user_id, role, enrolled_course_ids)


def _render_marquee_widget(user_id: str, role: str,
                            enrolled_course_ids: list[str]) -> None:
    tickers = MarqueeService.get_active_for_user(user_id, role, enrolled_course_ids)
    if not tickers:
        return

    speed_map = {"slow": "40s", "normal": "22s", "fast": "12s"}
    for t in tickers:
        duration = speed_map.get(t.get("speed", "normal"), "22s")
        bg  = t.get("bg_color",  "#307890")
        txt = t.get("text_color","#ffffff")
        msg = t.get("message","")
        st.markdown(f"""
        <div style="
            background:{bg}; color:{txt};
            padding:0.45rem 0; overflow:hidden;
            border-radius:6px; margin-bottom:0.5rem;
            box-shadow:0 2px 8px rgba(0,0,0,0.12);
        ">
            <div style="
                display:inline-block;
                white-space:nowrap;
                animation:marquee-scroll {duration} linear infinite;
                font-size:0.87rem; font-weight:500; padding-left:100%;
            ">
                &nbsp;&nbsp;&nbsp;{msg}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{msg}&nbsp;&nbsp;&nbsp;
            </div>
        </div>
        <style>
        @keyframes marquee-scroll {{
            0%   {{ transform: translateX(0); }}
            100% {{ transform: translateX(-50%); }}
        }}
        </style>
        """, unsafe_allow_html=True)


def _render_login_popup(user_id: str, role: str,
                         enrolled_course_ids: list[str]) -> None:
    """Show unseen login notifications as Streamlit dialogs/modals."""
    # Use session_state to only check once per session
    if st.session_state.get("_notifs_checked"):
        return
    st.session_state["_notifs_checked"] = True

    pending = NotificationService.get_pending_for_user(
        user_id, role, enrolled_course_ids
    )
    if not pending:
        return

    # Store in session state and show first one
    if "_pending_notifs" not in st.session_state:
        st.session_state["_pending_notifs"] = pending
        st.session_state["_notif_idx"]      = 0

    _show_next_notification(user_id)


def _show_next_notification(user_id: str) -> None:
    pending = st.session_state.get("_pending_notifs", [])
    idx     = st.session_state.get("_notif_idx", 0)
    if idx >= len(pending):
        return

    notif = pending[idx]

    @st.dialog(f"{notif.get('icon','📢')} {notif['title']}")
    def _popup():
        st.markdown(f"""
        <div style="font-size:0.92rem; color:{BRAND['text_dark']};
                    line-height:1.6; margin-bottom:1rem;">
            {notif['message']}
        </div>
        """, unsafe_allow_html=True)
        if notif.get("expires_at"):
            st.caption(f"Valid until: {_fmt_dt(notif['expires_at'])}")
        c1, c2 = st.columns(2)
        if c1.button("✅ Got it", use_container_width=True, key=f"notif_ok_{idx}"):
            NotificationService.mark_seen(notif["id"], user_id)
            st.session_state["_notif_idx"] = idx + 1
            st.rerun()
        remaining = len(pending) - idx - 1
        if remaining > 0:
            c2.caption(f"{remaining} more notification(s)")

    _popup()


# ══════════════════════════════════════════════════════════════════
# SHARED LIST RENDERERS
# ══════════════════════════════════════════════════════════════════

def _render_announcement_card(row: dict, show_audience: bool = True,
                               unread: bool = False) -> None:
    is_pinned = row.get("pinned", False)
    is_active = row.get("is_active", True)
    border_color = BRAND["core"] if is_active else "#aaaaaa"
    pin_badge = "📌 " if is_pinned else ""
    unread_dot = "🔵 " if unread else ""

    with st.expander(
        f"{unread_dot}{pin_badge}{row['title']}  "
        f"{'· ' + _audience_label(row) if show_audience else ''}  "
        f"· {_fmt_dt(row['created_at'])}",
        expanded=unread,
    ):
        st.markdown(f"""
        <div style="
            border-left:3px solid {border_color};
            padding:0.6rem 0.8rem;
            background:{'#f8fbfb' if is_active else '#f5f5f5'};
            border-radius:0 6px 6px 0;
            font-size:0.90rem; line-height:1.6;
            color:{BRAND['text_dark']};
            margin-bottom:0.5rem;
        ">{row['body']}</div>
        """, unsafe_allow_html=True)

        meta = []
        creator = row.get("creator") or {}
        if creator:
            meta.append(f"By: {_pname(creator)}")
        if row.get("expires_at"):
            meta.append(f"Expires: {_fmt_dt(row['expires_at'])}")
        if show_audience:
            meta.append(f"Audience: {_audience_label(row)}")
        if meta:
            st.caption("  ·  ".join(meta))


def _render_announcement_list(rows: list, editable: bool = False,
                               created_by_filter: str | None = None) -> None:
    if not rows:
        st.info("No announcements yet.")
        return

    for row in rows:
        with st.expander(
            f"{'📌 ' if row.get('pinned') else ''}"
            f"{'🟢' if row.get('is_active') else '🔴'} "
            f"{row['title']}  ·  {_audience_label(row)}  ·  {_fmt_dt(row['created_at'])}",
        ):
            st.markdown(f"""
            <div style="background:#f8fbfb;border-left:3px solid {BRAND['core']};
                        padding:0.6rem 0.8rem;border-radius:0 6px 6px 0;
                        font-size:0.89rem;line-height:1.6;">
                {row['body']}
            </div>
            """, unsafe_allow_html=True)

            creator = row.get("creator") or {}
            meta_parts = [f"By: {_pname(creator)}",
                          f"Posted: {_fmt_dt(row['created_at'])}"]
            if row.get("expires_at"):
                meta_parts.append(f"Expires: {_fmt_dt(row['expires_at'])}")
            st.caption("  ·  ".join(meta_parts))

            if editable and (not created_by_filter or row.get("created_by") == created_by_filter):
                c1, c2, c3 = st.columns(3)
                is_active   = row.get("is_active", True)
                toggle_lbl  = "🔴 Deactivate" if is_active else "🟢 Activate"
                if c1.button(toggle_lbl, key=f"ann_tog_{row['id']}",
                              use_container_width=True):
                    AnnouncementService.toggle_active(row["id"], not is_active)
                    st.rerun()
                pin_lbl = "📌 Unpin" if row.get("pinned") else "📌 Pin"
                if c2.button(pin_lbl, key=f"ann_pin_{row['id']}",
                              use_container_width=True):
                    AnnouncementService.update(row["id"],
                                               {"pinned": not row.get("pinned")})
                    st.rerun()
                if c3.button("🗑️ Delete", key=f"ann_del_{row['id']}",
                              use_container_width=True):
                    AnnouncementService.delete(row["id"])
                    st.rerun()


def _render_marquee_list(rows: list) -> None:
    if not rows:
        st.info("No tickers yet.")
        return
    for row in rows:
        bg  = row.get("bg_color",  "#307890")
        txt = row.get("text_color","#ffffff")
        active = row.get("is_active", True)
        with st.expander(
            f"{'🟢' if active else '🔴'} {row['message'][:60]}{'...' if len(row['message'])>60 else ''}  "
            f"·  {_audience_label(row)}",
        ):
            st.markdown(f"""
            <div style="background:{bg};color:{txt};padding:0.5rem 1rem;
                        border-radius:6px;font-size:0.88rem;margin-bottom:0.5rem;">
                {row['message']}
            </div>
            """, unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            col1.caption(f"Speed: {row.get('speed','normal')}  ·  From: {_fmt_dt(row.get('starts_at'))}")
            col2.caption(f"Until: {_fmt_dt(row.get('ends_at'))}  ·  Audience: {_audience_label(row)}")
            ca, cb = st.columns(2)
            lbl = "🔴 Deactivate" if active else "🟢 Activate"
            if ca.button(lbl, key=f"mq_tog_{row['id']}", use_container_width=True):
                MarqueeService.update(row["id"], {"is_active": not active})
                st.rerun()
            if cb.button("🗑️ Delete", key=f"mq_del_{row['id']}", use_container_width=True):
                MarqueeService.delete(row["id"])
                st.rerun()


def _render_notification_list(rows: list) -> None:
    if not rows:
        st.info("No login notifications yet.")
        return
    for row in rows:
        active = row.get("is_active", True)
        with st.expander(
            f"{'🟢' if active else '🔴'} {row.get('icon','📢')} {row['title']}  "
            f"·  {_audience_label(row)}  ·  {_fmt_dt(row.get('starts_at'))}"
        ):
            st.markdown(f"""
            <div style="background:#f8fbfb;border-left:3px solid {BRAND['core']};
                        padding:0.6rem 0.8rem;border-radius:0 6px 6px 0;
                        font-size:0.89rem;line-height:1.6;">
                {row['message']}
            </div>
            """, unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            col1.caption(f"Audience: {_audience_label(row)}  ·  Show once: {row.get('show_once',True)}")
            col2.caption(f"Active: {_fmt_dt(row.get('starts_at'))} → {_fmt_dt(row.get('ends_at'))}")
            ca, cb = st.columns(2)
            lbl = "🔴 Deactivate" if active else "🟢 Activate"
            if ca.button(lbl, key=f"notif_tog_{row['id']}", use_container_width=True):
                NotificationService.update(row["id"], {"is_active": not active})
                st.rerun()
            if cb.button("🗑️ Delete", key=f"notif_del_{row['id']}", use_container_width=True):
                NotificationService.delete(row["id"])
                st.rerun()
