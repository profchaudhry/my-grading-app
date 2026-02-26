"""
Sylemax Login — Phase 5 branded login page.
"""
import streamlit as st
import base64
from pathlib import Path
from services.auth_service import AuthService
from ui.styles import inject_global_css, BRAND


def _logo_b64() -> str:
    logo_path = Path(__file__).parent.parent / "assets" / "sylemax_logo.png"
    if logo_path.exists():
        return base64.b64encode(logo_path.read_bytes()).decode()
    return ""


def render_login() -> None:
    inject_global_css()
    logo_b64 = _logo_b64()

    # Full-page branded background
    st.markdown(f"""
    <style>
    .stApp {{
        background: linear-gradient(145deg, {BRAND['deep']} 0%, {BRAND['core']} 45%, {BRAND['mid']} 100%) !important;
        min-height: 100vh;
    }}
    .main .block-container {{
        padding: 2rem 1rem !important;
        max-width: 460px !important;
        margin: 0 auto !important;
    }}
    .login-card {{
        background: rgba(255,255,255,0.97);
        border-radius: 20px;
        padding: 2.5rem 2.2rem 2rem;
        box-shadow: 0 24px 80px rgba(24,96,120,0.35), 0 4px 20px rgba(0,0,0,0.12);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.8);
    }}
    .login-logo {{
        text-align: center;
        margin-bottom: 1.6rem;
    }}
    .login-logo img {{
        width: 180px;
        margin-bottom: 0.5rem;
    }}
    .login-tagline {{
        font-size: 0.75rem;
        color: {BRAND['text_light']};
        text-align: center;
        letter-spacing: 0.10em;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }}
    .login-divider {{
        display: flex; align-items: center; gap: 12px;
        margin: 1rem 0;
    }}
    .login-divider-line {{
        flex: 1; height: 1px;
        background: {BRAND['border']};
    }}
    .login-divider-text {{
        font-size: 0.72rem; color: {BRAND['text_light']};
        text-transform: uppercase; letter-spacing: 0.06em;
    }}
    /* Override form inside card */
    [data-testid="stForm"] {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        background: {BRAND['pale']} !important;
        border-radius: 10px !important;
        padding: 3px !important;
        margin-bottom: 1.2rem;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-size: 0.86rem !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    # Center vertically with spacer
    st.markdown("<div style='height:3vh'></div>", unsafe_allow_html=True)

    # Login card
    st.markdown('<div class="login-card">', unsafe_allow_html=True)

    # Logo
    if logo_b64:
        st.markdown(f"""
        <div class="login-logo">
            <img src="data:image/png;base64,{logo_b64}" alt="Sylemax"/>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="text-align:center;margin-bottom:1.5rem;">
            <div style="font-family:'DM Serif Display',serif;font-size:2.2rem;
                        color:{BRAND['deep']};letter-spacing:-0.03em;">Sylemax</div>
            <div style="font-size:0.72rem;color:{BRAND['text_light']};
                        letter-spacing:0.12em;text-transform:uppercase;">
                Academic Management · Effortless & Tailored
            </div>
        </div>
        """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["🔑 Sign In", "📝 Register as Faculty"])

    # ── Sign In ───────────────────────────────────────────────────
    with tab_login:
        with st.form("login_form"):
            st.markdown(f"<p style='font-size:0.78rem;color:{BRAND['text_light']};margin-bottom:1rem;text-align:center;'>Welcome back — sign in to continue</p>", unsafe_allow_html=True)
            email    = st.text_input("Email Address", placeholder="your@email.com")
            password = st.text_input("Password", type="password",
                                      placeholder="Enter your password")
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "Sign In →", use_container_width=True, type="primary"
            )

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                with st.spinner("Signing in..."):
                    result = AuthService.login(email.strip(), password)
                if result.get("success"):
                    st.session_state.user    = result["user"]
                    st.session_state.session = result["session"]
                    st.session_state.role    = result["role"]
                    st.session_state.profile = result.get("profile")
                    st.rerun()
                else:
                    st.error(result.get("error", "Login failed. Please check your credentials."))

    # ── Register ──────────────────────────────────────────────────
    with tab_register:
        st.markdown(f"<p style='font-size:0.78rem;color:{BRAND['text_light']};margin-bottom:1rem;text-align:center;'>Faculty registration requires admin approval</p>", unsafe_allow_html=True)
        with st.form("register_form"):
            c1, c2 = st.columns(2)
            first_name   = c1.text_input("First Name *",  placeholder="John")
            last_name    = c2.text_input("Last Name *",   placeholder="Smith")
            employee_id  = st.text_input("Employee ID *", placeholder="EMP-12345")
            reg_email    = st.text_input("Email Address *", placeholder="faculty@institution.edu")
            c3, c4       = st.columns(2)
            reg_password = c3.text_input("Password *",   type="password", placeholder="Min 8 chars")
            confirm_pw   = c4.text_input("Confirm Password *", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
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
                with st.spinner("Submitting registration..."):
                    result = AuthService.register_faculty(
                        email=reg_email.strip(),
                        password=reg_password,
                        first_name=first_name.strip(),
                        last_name=last_name.strip(),
                        employee_id=employee_id.strip(),
                    )
                if result.get("success"):
                    st.success(
                        "✅ Registration submitted! An administrator will review and approve your account."
                    )
                else:
                    st.error(result.get("error","Registration failed. This email may already be registered."))

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <p style="text-align:center;margin-top:1.2rem;
              font-size:0.68rem;color:rgba(255,255,255,0.45);
              letter-spacing:0.06em;">
        © Sylemax · Academic Management · Effortless &amp; Tailored
    </p>
    """, unsafe_allow_html=True)


# Alias for backward compatibility
login_page = render_login
