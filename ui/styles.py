"""
Sylemax Brand Styles — Phase 5 UI Polish
Primary palette extracted from Sylemax logo:
  Deep teal:    #186078
  Core teal:    #307890
  Mid teal:     #489090
  Light teal:   #78a8a8
  Accent green: #60a890
"""
import streamlit as st
import base64
from pathlib import Path

BRAND = {
    "deep":       "#186078",
    "core":       "#307890",
    "mid":        "#489090",
    "light":      "#78a8a8",
    "accent":     "#60a890",
    "pale":       "#e8f4f4",
    "white":      "#ffffff",
    "text_dark":  "#0d2f3a",
    "text_mid":   "#2a5a6e",
    "text_light": "#5a8a96",
    "bg":         "#f4fafa",
    "bg_card":    "#ffffff",
    "border":     "#d0e8e8",
    "success":    "#2e9e6e",
    "warning":    "#e8a020",
    "error":      "#d04040",
    "info":       "#307890",
}


def _logo_b64() -> str:
    logo_path = Path(__file__).parent.parent / "assets" / "sylemax_logo.png"
    if logo_path.exists():
        return base64.b64encode(logo_path.read_bytes()).decode()
    return ""


def inject_global_css() -> None:
    logo_b64 = _logo_b64()
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Serif+Display:ital@0;1&display=swap');

    :root {{
        --deep:       {BRAND['deep']};
        --core:       {BRAND['core']};
        --mid:        {BRAND['mid']};
        --light:      {BRAND['light']};
        --accent:     {BRAND['accent']};
        --pale:       {BRAND['pale']};
        --bg:         {BRAND['bg']};
        --bg-card:    {BRAND['bg_card']};
        --border:     {BRAND['border']};
        --text-dark:  {BRAND['text_dark']};
        --text-mid:   {BRAND['text_mid']};
        --text-light: {BRAND['text_light']};
        --success:    {BRAND['success']};
        --warning:    {BRAND['warning']};
        --error:      {BRAND['error']};
        --radius:     10px;
        --radius-lg:  16px;
        --shadow:     0 2px 12px rgba(24,96,120,0.10);
        --shadow-lg:  0 8px 32px rgba(24,96,120,0.14);
        --transition: 0.18s ease;
    }}

    html, body, [class*="css"] {{
        font-family: 'DM Sans', sans-serif !important;
        color: var(--text-dark) !important;
    }}

    .stApp {{ background: var(--bg) !important; }}

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, var(--deep) 0%, #1e7090 55%, var(--core) 100%) !important;
        border-right: none !important;
        box-shadow: 4px 0 24px rgba(24,96,120,0.20) !important;
    }}
    [data-testid="stSidebar"] * {{ color: rgba(255,255,255,0.92) !important; }}
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown span {{
        color: rgba(255,255,255,0.72) !important;
        font-size: 0.78rem !important;
    }}
    [data-testid="stSidebar"] .stRadio label {{
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: var(--radius) !important;
        padding: 10px 14px !important;
        margin-bottom: 4px !important;
        transition: var(--transition) !important;
        cursor: pointer !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        color: rgba(255,255,255,0.88) !important;
    }}
    [data-testid="stSidebar"] .stRadio label:hover {{
        background: rgba(255,255,255,0.14) !important;
        border-color: rgba(255,255,255,0.25) !important;
        transform: translateX(3px) !important;
    }}
    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child {{
        display: none !important;
    }}
    [data-testid="stSidebar"] hr {{
        border-color: rgba(255,255,255,0.15) !important;
        margin: 10px 0 !important;
    }}
    .sidebar-user-badge {{
        background: rgba(255,255,255,0.11);
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: var(--radius);
        padding: 12px 14px;
        margin-bottom: 14px;
    }}
    .sidebar-user-badge .user-name {{
        font-size: 0.93rem; font-weight: 600; color: white !important;
    }}
    .sidebar-user-badge .user-role {{
        font-size: 0.70rem; color: rgba(255,255,255,0.60) !important;
        text-transform: uppercase; letter-spacing: 0.09em; margin-top: 2px;
    }}

    /* ── Content ── */
    .main .block-container {{
        padding: 1.8rem 2.2rem 3rem !important;
        max-width: 1180px !important;
    }}
    h1 {{
        font-family: 'DM Serif Display', serif !important;
        font-size: 1.95rem !important; font-weight: 400 !important;
        color: var(--deep) !important; letter-spacing: -0.02em !important;
        margin-bottom: 0.2rem !important; line-height: 1.2 !important;
    }}
    h2 {{
        font-family: 'DM Sans', sans-serif !important;
        font-size: 1.25rem !important; font-weight: 600 !important;
        color: var(--core) !important;
    }}
    h3 {{
        font-family: 'DM Sans', sans-serif !important;
        font-size: 1.02rem !important; font-weight: 600 !important;
        color: var(--text-dark) !important;
    }}

    /* ── Section header ── */
    .sx-section-header {{
        border-left: 3px solid var(--core);
        padding-left: 12px;
        margin: 1.4rem 0 0.7rem;
    }}
    .sx-section-header h3 {{
        margin: 0 !important; font-size: 0.98rem !important;
        font-weight: 600 !important; color: var(--deep) !important;
    }}
    .sx-section-header p {{
        margin: 2px 0 0 !important; font-size: 0.76rem !important;
        color: var(--text-light) !important;
    }}

    /* ── Page header strip ── */
    .sx-page-header {{
        background: linear-gradient(135deg, var(--deep) 0%, var(--core) 100%);
        border-radius: var(--radius-lg); padding: 1.4rem 1.8rem;
        margin-bottom: 1.4rem; color: white;
        display: flex; align-items: center; gap: 1rem;
        box-shadow: var(--shadow-lg);
    }}
    .sx-page-header h1 {{
        color: white !important;
        font-family: 'DM Serif Display', serif !important;
        font-size: 1.55rem !important; margin: 0 !important;
    }}
    .sx-page-header p {{
        color: rgba(255,255,255,0.72) !important;
        font-size: 0.80rem !important; margin: 4px 0 0 !important;
    }}
    .sx-page-header .page-icon {{ font-size: 1.9rem; line-height: 1; }}

    /* ── Stat card ── */
    .sx-stat-card {{
        background: var(--bg-card); border: 1px solid var(--border);
        border-radius: var(--radius-lg); padding: 1.1rem 1.3rem;
        box-shadow: var(--shadow); transition: all var(--transition);
        border-top: 3px solid var(--core);
    }}
    .sx-stat-card:hover {{
        box-shadow: var(--shadow-lg); transform: translateY(-2px);
        border-top-color: var(--deep);
    }}
    .sx-stat-card .stat-label {{
        font-size: 0.70rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.08em; color: var(--text-light); margin-bottom: 5px;
    }}
    .sx-stat-card .stat-value {{
        font-family: 'DM Serif Display', serif; font-size: 2.1rem;
        color: var(--deep); line-height: 1; margin-bottom: 3px;
    }}
    .sx-stat-card .stat-sub {{ font-size: 0.76rem; color: var(--text-light); }}

    /* ── Metrics ── */
    [data-testid="metric-container"] {{
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-lg) !important;
        padding: 1rem 1.2rem !important;
        box-shadow: var(--shadow) !important;
        transition: all var(--transition) !important;
    }}
    [data-testid="metric-container"]:hover {{
        box-shadow: var(--shadow-lg) !important;
        transform: translateY(-1px) !important;
        border-color: var(--light) !important;
    }}
    [data-testid="metric-container"] [data-testid="stMetricLabel"] {{
        font-size: 0.73rem !important; font-weight: 600 !important;
        text-transform: uppercase !important; letter-spacing: 0.06em !important;
        color: var(--text-light) !important;
    }}
    [data-testid="metric-container"] [data-testid="stMetricValue"] {{
        font-family: 'DM Serif Display', serif !important;
        font-size: 1.85rem !important; color: var(--deep) !important;
    }}

    /* ── Buttons ── */
    .stButton > button {{
        border-radius: var(--radius) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important; font-size: 0.86rem !important;
        padding: 0.48rem 1.15rem !important;
        transition: all var(--transition) !important;
        border: 1.5px solid var(--border) !important;
        background: var(--bg-card) !important;
        color: var(--text-dark) !important;
        box-shadow: 0 1px 4px rgba(24,96,120,0.07) !important;
    }}
    .stButton > button:hover {{
        border-color: var(--core) !important; color: var(--core) !important;
        box-shadow: 0 2px 10px rgba(48,120,144,0.18) !important;
        transform: translateY(-1px) !important;
    }}
    [data-testid="baseButton-primary"] {{
        background: linear-gradient(135deg, var(--core), var(--deep)) !important;
        color: white !important; border-color: transparent !important;
        box-shadow: 0 3px 12px rgba(48,120,144,0.30) !important;
    }}
    [data-testid="baseButton-primary"]:hover {{
        background: linear-gradient(135deg, var(--deep), #0e4a5a) !important;
        box-shadow: 0 5px 18px rgba(24,96,120,0.38) !important;
        transform: translateY(-2px) !important;
    }}

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {{
        border-radius: var(--radius) !important;
        border: 1.5px solid var(--border) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.87rem !important;
        background: var(--bg-card) !important;
        transition: border-color var(--transition) !important;
    }}
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: var(--core) !important;
        box-shadow: 0 0 0 3px rgba(48,120,144,0.12) !important;
    }}

    /* ── Expanders ── */
    [data-testid="stExpander"] {{
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-lg) !important;
        box-shadow: var(--shadow) !important;
        margin-bottom: 0.55rem !important;
        overflow: hidden !important;
    }}
    [data-testid="stExpander"]:hover {{
        border-color: var(--light) !important;
        box-shadow: var(--shadow-lg) !important;
    }}
    [data-testid="stExpander"] summary {{
        padding: 0.8rem 1.1rem !important;
        font-weight: 500 !important; font-size: 0.89rem !important;
        color: var(--text-dark) !important;
    }}
    [data-testid="stExpander"] summary:hover {{
        background: var(--pale) !important; color: var(--deep) !important;
    }}

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {{
        background: var(--pale) !important;
        border-radius: var(--radius-lg) !important;
        padding: 4px !important; gap: 2px !important;
        border-bottom: none !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: var(--radius) !important;
        padding: 0.42rem 1rem !important;
        font-size: 0.84rem !important; font-weight: 500 !important;
        color: var(--text-mid) !important;
        background: transparent !important; border: none !important;
        transition: all var(--transition) !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: var(--bg-card) !important;
        color: var(--deep) !important; font-weight: 600 !important;
        box-shadow: var(--shadow) !important;
    }}
    .stTabs [data-baseweb="tab-panel"] {{ padding-top: 1.2rem !important; }}

    /* ── DataFrames ── */
    [data-testid="stDataFrame"] {{
        border-radius: var(--radius-lg) !important; overflow: hidden !important;
        border: 1px solid var(--border) !important; box-shadow: var(--shadow) !important;
    }}

    /* ── Forms ── */
    [data-testid="stForm"] {{
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-lg) !important;
        padding: 1.2rem !important; box-shadow: var(--shadow) !important;
    }}

    /* ── File uploader ── */
    [data-testid="stFileUploader"] {{
        background: var(--pale) !important;
        border: 2px dashed var(--light) !important;
        border-radius: var(--radius-lg) !important;
    }}
    [data-testid="stFileUploader"]:hover {{
        border-color: var(--core) !important; background: #dff0f0 !important;
    }}

    /* ── Badges ── */
    .sx-grade-badge {{
        display: inline-block; padding: 3px 10px; border-radius: 20px;
        font-size: 0.76rem; font-weight: 700; letter-spacing: 0.04em;
    }}
    .sx-grade-a  {{ background:#d4f5e0; color:#1a7040; }}
    .sx-grade-b  {{ background:#d4e8f5; color:#1a4870; }}
    .sx-grade-c  {{ background:#fdf3d4; color:#7a5c00; }}
    .sx-grade-d  {{ background:#fde8d4; color:#7a3a00; }}
    .sx-grade-f  {{ background:#fdd4d4; color:#7a0000; }}

    .sx-status {{
        display: inline-block; padding: 3px 10px; border-radius: 20px;
        font-size: 0.70rem; font-weight: 600; letter-spacing: 0.05em;
        text-transform: uppercase;
    }}
    .sx-status-draft     {{ background:#e8e8e8; color:#555; }}
    .sx-status-submitted {{ background:#fef3d4; color:#7a5c00; }}
    .sx-status-approved  {{ background:#d4e8f5; color:#1a4870; }}
    .sx-status-released  {{ background:#d4f5e0; color:#1a7040; }}

    /* ── Dividers ── */
    hr {{
        border:none !important; border-top:1px solid var(--border) !important;
        margin: 1.1rem 0 !important;
    }}

    /* ── Scrollbar ── */
    ::-webkit-scrollbar {{ width:6px; height:6px; }}
    ::-webkit-scrollbar-track {{ background: var(--pale); }}
    ::-webkit-scrollbar-thumb {{ background: var(--light); border-radius:3px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--core); }}

    /* ── Hide clutter ── */
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    [data-testid="stToolbar"] {{ display: none; }}
    </style>
    """, unsafe_allow_html=True)


def page_header(icon: str, title: str, subtitle: str = "") -> None:
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(f"""
    <div class="sx-page-header">
        <div class="page-icon">{icon}</div>
        <div><h1>{title}</h1>{sub}</div>
    </div>
    """, unsafe_allow_html=True)


def section_header(title: str, subtitle: str = "") -> None:
    sub = f'<p>{subtitle}</p>' if subtitle else ''
    st.markdown(f"""
    <div class="sx-section-header"><h3>{title}</h3>{sub}</div>
    """, unsafe_allow_html=True)


def stat_card(label: str, value: str, sub: str = "") -> None:
    st.markdown(f"""
    <div class="sx-stat-card">
        <div class="stat-label">{label}</div>
        <div class="stat-value">{value}</div>
        {"<div class='stat-sub'>" + sub + "</div>" if sub else ""}
    </div>
    """, unsafe_allow_html=True)


def grade_badge(letter: str) -> str:
    if not letter or letter == "—":
        return letter or "—"
    cls = "a" if letter.startswith("A") else \
          "b" if letter.startswith("B") else \
          "c" if letter.startswith("C") else \
          "d" if letter.startswith("D") else "f"
    return f'<span class="sx-grade-badge sx-grade-{cls}">{letter}</span>'


def status_badge(status: str) -> str:
    icons = {"draft":"✏️","submitted":"📤","approved":"✅","released":"📢"}
    icon = icons.get(status, "")
    return f'<span class="sx-status sx-status-{status}">{icon} {status.capitalize()}</span>'


def render_sidebar_logo() -> None:
    logo_b64 = _logo_b64()
    if logo_b64:
        st.sidebar.markdown(f"""
        <div style="text-align:center;padding:1rem 0.5rem 0.5rem;">
            <img src="data:image/png;base64,{logo_b64}"
                 style="width:140px;filter:brightness(0) invert(1);opacity:0.95;"
                 alt="Sylemax"/>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.sidebar.markdown("""
        <div style="text-align:center;padding:1.2rem 0 0.5rem;">
            <span style="font-family:'DM Serif Display',serif;font-size:1.6rem;
                         color:white;letter-spacing:-0.02em;">Sylemax</span><br>
            <span style="font-size:0.66rem;color:rgba(255,255,255,0.5);
                         letter-spacing:0.12em;text-transform:uppercase;">
                Academic Management
            </span>
        </div>
        """, unsafe_allow_html=True)
    st.sidebar.markdown(
        "<hr style='border-color:rgba(255,255,255,0.15);margin:8px 0 12px;'/>",
        unsafe_allow_html=True
    )


def render_sidebar_user(name: str, role: str) -> None:
    labels = {
        "admin":"Administrator","faculty":"Faculty",
        "faculty_ultra":"Faculty Ultra ⭐","student":"Student",
    }
    st.sidebar.markdown(f"""
    <div class="sidebar-user-badge">
        <div class="user-name">👤 {name}</div>
        <div class="user-role">{labels.get(role, role.title())}</div>
    </div>
    """, unsafe_allow_html=True)
