"""
Sylemax Login — simple centered card on white background.
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

    # Inject fonts + full page styles BEFORE any widget
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display&display=swap');
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <style>
    html, body, [class*="css"] {{
        font-family: 'DM Sans', sans-serif !important;
    }}
    /* White page */
    .stApp {{
        background: #f0f6f7 !important;
    }}
    /* Remove default padding */
    .main .block-container {{
        padding-top: 2rem !important;
        padding-bottom: 1rem !important;
        max-width: 480px !important;
        margin: 0 auto !important;
    }}
    /* Hide all chrome */
    #MainMenu, footer, header,
    [data-testid="stToolbar"],
    [data-testid="stHeader"],
    [data-testid="stDecoration"] {{
        display: none !important;
        visibility: hidden !important;
    }}
    /* ── Form resets ── */
    [data-testid="stForm"] {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }}
    /* Input labels */
    .stTextInput label, .stTextArea label {{
        font-size: 0.74rem !important;
        font-weight: 600 !important;
        color: {BRAND['text_mid']} !important;
        text-transform: uppercase !important;
        letter-spacing: 0.07em !important;
    }}
    /* Input fields */
    .stTextInput > div > div > input {{
        border: 1.5px solid {BRAND['border']} !important;
        border-radius: 8px !important;
        padding: 0.52rem 0.85rem !important;
        font-size: 0.88rem !important;
        background: #ffffff !important;
        color: {BRAND['text_dark']} !important;
        transition: border-color 0.15s ease !important;
    }}
    .stTextInput > div > div > input:focus {{
        border-color: {BRAND['core']} !important;
        box-shadow: 0 0 0 3px rgba(48,120,144,0.12) !important;
        outline: none !important;
    }}
    /* ALL buttons — reset first then style */
    .stButton > button,
    [data-testid="baseButton-primary"],
    [data-testid="baseButton-secondary"] {{
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        border-radius: 8px !important;
        padding: 0.55rem 1.2rem !important;
        transition: all 0.15s ease !important;
        cursor: pointer !important;
    }}
    /* Primary = brand teal */
    [data-testid="baseButton-primary"] {{
        background: {BRAND['core']} !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 3px 10px rgba(48,120,144,0.28) !important;
    }}
    [data-testid="baseButton-primary"]:hover {{
        background: {BRAND['deep']} !important;
        box-shadow: 0 5px 16px rgba(24,96,120,0.36) !important;
        transform: translateY(-1px) !important;
    }}
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        background: #e8f2f4 !important;
        border-radius: 9px !important;
        padding: 3px !important;
        border-bottom: none !important;
        gap: 2px !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 7px !important;
        padding: 0.38rem 1rem !important;
        font-size: 0.83rem !important;
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
        padding-top: 1rem !important;
    }}
    /* Alert boxes */
    [data-testid="stAlert"] {{
        border-radius: 8px !important;
        font-size: 0.84rem !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    # ── Logo ──────────────────────────────────────────────────────
    if logo_b64:
        st.markdown(f"""
        <div style="text-align:center; padding: 0.5rem 0 0.25rem;">
            <img src="data:image/png;base64,{logo_b64}"
                 style="width:180px; height:auto;"
                 alt="Sylemax"/>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="text-align:center; padding: 1rem 0 0.5rem;">
            <span style="font-family:'DM Serif Display',serif; font-size:2rem;
                         color:{BRAND['deep']}; letter-spacing:-0.02em;">Sylemax</span>
        </div>
        """, unsafe_allow_html=True)

    # ── Heading ───────────────────────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center; margin-bottom:1.4rem;">
        <div style="font-family:'DM Serif Display',serif; font-size:1.55rem;
                    color:{BRAND['deep']}; line-height:1.2; margin-bottom:0.3rem;">
            Welcome back
        </div>
        <div style="font-size:0.78rem; color:{BRAND['text_light']};">
            Sign in to your Sylemax account to continue
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────
    tab_login, tab_register = st.tabs(["🔑  Sign In", "📝  Register as Faculty"])

    with tab_login:
        with st.form("login_form"):
            email    = st.text_input("Email Address", placeholder="your@email.com")
            password = st.text_input("Password", type="password",
                                      placeholder="Enter your password")
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
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
                    # Save tokens to URL so session survives browser refresh
                    if result.get("access_token"):
                        st.query_params["at"] = result["access_token"]
                    if result.get("refresh_token"):
                        st.query_params["rt"] = result["refresh_token"]
                    st.rerun()
                else:
                    st.error("Incorrect email or password. Please try again.")

    with tab_register:
        st.markdown(
            f"<p style='font-size:0.76rem; color:{BRAND['text_light']}; margin-bottom:0.6rem;'>"
            f"Faculty registration requires administrator approval before access is granted.</p>",
            unsafe_allow_html=True
        )
        with st.form("register_form"):
            c1, c2       = st.columns(2)
            first_name   = c1.text_input("First Name *",  placeholder="John")
            last_name    = c2.text_input("Last Name *",   placeholder="Smith")
            employee_id  = st.text_input("Employee ID *", placeholder="EMP-12345")
            reg_email    = st.text_input("Email *",       placeholder="faculty@institution.edu")
            c3, c4       = st.columns(2)
            reg_password = c3.text_input("Password *",         type="password",
                                          placeholder="Min 8 chars")
            confirm_pw   = c4.text_input("Confirm Password *", type="password")
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
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
    <div style="text-align:center; margin-top:1.5rem; font-size:0.67rem;
                color:{BRAND['text_light']}; letter-spacing:0.04em;">
        © Sylemax · Academic Management · Effortless &amp; Tailored
    </div>
    """, unsafe_allow_html=True)


# Backward compat alias
login_page = render_login
