"""
Sylemax Login — compact, fully above the fold, no scroll needed.
"""
import streamlit as st
import base64
from pathlib import Path
from services.auth_service import AuthService
from ui.styles import BRAND


def _logo_b64() -> str:
    logo_path = Path(__file__).parent.parent / "assets" / "sylemax_logo.png"
    if logo_path.exists():
        return base64.b64encode(logo_path.read_bytes()).decode()
    return ""


def render_login() -> None:
    logo_b64 = _logo_b64()

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Serif+Display&display=swap');
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <style>
    html, body, [class*="css"] {{
        font-family: 'DM Sans', sans-serif !important;
    }}
    .stApp {{
        background: #eef5f6 !important;
    }}
    /* Tight centered container */
    .main .block-container {{
        padding-top: 1.2rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 440px !important;
        margin: 0 auto !important;
    }}
    /* Hide chrome */
    #MainMenu, footer, header,
    [data-testid="stToolbar"],
    [data-testid="stHeader"],
    [data-testid="stDecoration"],
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] {{
        display: none !important;
    }}
    /* Form */
    [data-testid="stForm"] {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }}
    /* Input labels — compact */
    .stTextInput label {{
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        color: {BRAND['text_mid']} !important;
        text-transform: uppercase !important;
        letter-spacing: 0.07em !important;
        margin-bottom: 2px !important;
    }}
    /* Input fields — compact height */
    .stTextInput > div > div > input {{
        border: 1.5px solid {BRAND['border']} !important;
        border-radius: 8px !important;
        padding: 0.42rem 0.8rem !important;
        font-size: 0.88rem !important;
        background: #ffffff !important;
        color: {BRAND['text_dark']} !important;
        height: 2.4rem !important;
    }}
    .stTextInput > div > div > input:focus {{
        border-color: {BRAND['core']} !important;
        box-shadow: 0 0 0 3px rgba(48,120,144,0.11) !important;
        outline: none !important;
    }}
    /* Remove default spacing between widgets */
    .stTextInput {{ margin-bottom: 0.5rem !important; }}
    div[data-testid="stVerticalBlock"] > div {{
        gap: 0 !important;
    }}
    /* PRIMARY BUTTON — force brand teal, kill red */
    .stButton > button,
    button[data-testid="baseButton-primary"],
    [data-testid="baseButton-primary"] {{
        background: {BRAND['core']} !important;
        background-color: {BRAND['core']} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.52rem 1.2rem !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        box-shadow: 0 3px 10px rgba(48,120,144,0.28) !important;
        transition: all 0.15s ease !important;
        width: 100% !important;
        margin-top: 0.5rem !important;
    }}
    .stButton > button:hover,
    [data-testid="baseButton-primary"]:hover {{
        background: {BRAND['deep']} !important;
        background-color: {BRAND['deep']} !important;
        box-shadow: 0 5px 16px rgba(24,96,120,0.36) !important;
        transform: translateY(-1px) !important;
    }}
    /* Tabs — compact */
    .stTabs [data-baseweb="tab-list"] {{
        background: #deeaec !important;
        border-radius: 8px !important;
        padding: 3px !important;
        border-bottom: none !important;
        gap: 2px !important;
        margin-bottom: 0.7rem !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 6px !important;
        padding: 0.3rem 0.9rem !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: {BRAND['text_mid']} !important;
        background: transparent !important;
        border: none !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: #ffffff !important;
        color: {BRAND['deep']} !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 4px rgba(24,96,120,0.10) !important;
    }}
    .stTabs [data-baseweb="tab-panel"] {{
        padding-top: 0.5rem !important;
    }}
    /* Alert boxes */
    [data-testid="stAlert"] {{
        border-radius: 7px !important;
        font-size: 0.82rem !important;
        padding: 0.5rem 0.8rem !important;
        margin-top: 0.4rem !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    # ── Logo — small and tight ─────────────────────────────────────
    if logo_b64:
        st.markdown(f"""
        <div style="text-align:center; padding: 0 0 0.4rem;">
            <img src="data:image/png;base64,{logo_b64}"
                 style="width:150px; height:auto;"
                 alt="Sylemax"/>
        </div>
        """, unsafe_allow_html=True)

    # ── Heading — compact ─────────────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center; margin-bottom:1rem;">
        <div style="font-family:'DM Serif Display',serif; font-size:1.45rem;
                    color:{BRAND['deep']}; line-height:1.2; margin-bottom:0.2rem;">
            Welcome back
        </div>
        <div style="font-size:0.75rem; color:{BRAND['text_light']};">
            Sign in to your Sylemax account to continue
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────
    tab_login, tab_register = st.tabs(["🔑  Sign In", "📝  Register as Faculty"])

    with tab_login:
        with st.form("login_form"):
            email    = st.text_input("Email Address", placeholder="your@email.com",
                                      label_visibility="visible")
            password = st.text_input("Password", type="password",
                                      placeholder="Enter your password")
            submitted = st.form_submit_button(
                "Sign In →", use_container_width=True, type="primary"
            )

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                with st.spinner("Signing in..."):
                    result = AuthService.login(email.strip(), password)
                if result and result.get("user"):
                    profile = result.get("profile", {}) or {}
                    st.session_state.user    = result["user"]
                    st.session_state.role    = profile.get("role", "student")
                    st.session_state.profile = profile
                    if result.get("access_token"):
                        st.query_params["at"] = result["access_token"]
                    if result.get("refresh_token"):
                        st.query_params["rt"] = result["refresh_token"]
                    st.rerun()
                else:
                    st.error("Incorrect email or password. Please try again.")

    with tab_register:
        st.markdown(
            f"<p style='font-size:0.73rem;color:{BRAND['text_light']};margin-bottom:0.5rem;'>"
            f"Faculty registration requires administrator approval.</p>",
            unsafe_allow_html=True
        )
        with st.form("register_form"):
            c1, c2       = st.columns(2)
            first_name   = c1.text_input("First Name *",  placeholder="John")
            last_name    = c2.text_input("Last Name *",   placeholder="Smith")
            employee_id  = st.text_input("Employee ID *", placeholder="EMP-12345")
            reg_email    = st.text_input("Email *",       placeholder="faculty@institution.edu")
            c3, c4       = st.columns(2)
            reg_password = c3.text_input("Password *",         type="password", placeholder="Min 8 chars")
            confirm_pw   = c4.text_input("Confirm Password *", type="password")
            reg_submitted = st.form_submit_button(
                "Submit Registration", use_container_width=True, type="primary"
            )

        if reg_submitted:
            if not all([first_name, last_name, employee_id, reg_email, reg_password]):
                st.error("All fields marked * are required.")
            elif reg_password != confirm_pw:
                st.error("Passwords do not match.")
            elif len(reg_password) < 8:
                st.error("Password must be at least 8 characters.")
            else:
                with st.spinner("Submitting..."):
                    result = AuthService.register_faculty(
                        email=reg_email.strip(),
                        password=reg_password,
                        first_name=first_name.strip(),
                        last_name=last_name.strip(),
                        employee_id=employee_id.strip(),
                    )
                if result:
                    st.success("✅ Registration submitted! An admin will review your account.")
                else:
                    st.error("Registration failed. This email may already be registered.")

    # ── Footer ────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center; margin-top:0.8rem; font-size:0.64rem;
                color:{BRAND['text_light']}; letter-spacing:0.04em;">
        © Sylemax · Academic Management · Effortless &amp; Tailored
    </div>
    """, unsafe_allow_html=True)


login_page = render_login
