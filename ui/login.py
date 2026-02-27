"""
Sylemax Login — clean white layout, everything above the fold.
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

    st.markdown(f"""
    <style>
    /* ── White page background ── */
    .stApp {{
        background: #ffffff !important;
    }}
    .main .block-container {{
        padding: 0 !important;
        max-width: 100% !important;
    }}

    /* ── Two-column full-height layout ── */
    .login-wrapper {{
        display: flex;
        min-height: 100vh;
        width: 100%;
    }}

    /* Left branding panel */
    .login-brand {{
        width: 42%;
        background: linear-gradient(160deg, {BRAND['deep']} 0%, {BRAND['core']} 55%, {BRAND['mid']} 100%);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        position: fixed;
        top: 0; left: 0;
        height: 100vh;
    }}
    .login-brand img {{
        width: 200px;
        filter: brightness(0) invert(1);
        opacity: 0.95;
        margin-bottom: 1.5rem;
    }}
    .login-brand-title {{
        font-family: 'DM Serif Display', serif;
        font-size: 1.8rem;
        color: white;
        text-align: center;
        line-height: 1.25;
        margin-bottom: 0.6rem;
    }}
    .login-brand-sub {{
        font-size: 0.78rem;
        color: rgba(255,255,255,0.65);
        text-align: center;
        letter-spacing: 0.10em;
        text-transform: uppercase;
    }}
    .login-brand-dots {{
        display: flex; gap: 8px; margin-top: 2rem;
    }}
    .login-brand-dot {{
        width: 8px; height: 8px; border-radius: 50%;
        background: rgba(255,255,255,0.35);
    }}
    .login-brand-dot.active {{
        background: rgba(255,255,255,0.9);
        width: 24px; border-radius: 4px;
    }}

    /* Right form panel */
    .login-form-panel {{
        margin-left: 42%;
        width: 58%;
        min-height: 100vh;
        background: #ffffff;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem 3rem;
    }}
    .login-form-inner {{
        width: 100%;
        max-width: 400px;
    }}
    .login-form-heading {{
        font-family: 'DM Serif Display', serif;
        font-size: 1.7rem;
        color: {BRAND['deep']};
        margin-bottom: 0.25rem;
        line-height: 1.2;
    }}
    .login-form-sub {{
        font-size: 0.80rem;
        color: {BRAND['text_light']};
        margin-bottom: 1.4rem;
    }}

    /* Streamlit widget overrides for login form */
    .stTabs [data-baseweb="tab-list"] {{
        background: {BRAND['pale']} !important;
        border-radius: 10px !important;
        padding: 3px !important;
        margin-bottom: 1.2rem !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-size: 0.85rem !important;
        padding: 0.38rem 1rem !important;
    }}
    [data-testid="stForm"] {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }}
    .stTextInput label, .stNumberInput label {{
        font-size: 0.80rem !important;
        font-weight: 600 !important;
        color: {BRAND['text_mid']} !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
    }}
    .stTextInput > div > div > input {{
        padding: 0.55rem 0.85rem !important;
        font-size: 0.90rem !important;
    }}
    [data-testid="baseButton-primary"] {{
        background: linear-gradient(135deg, {BRAND['core']}, {BRAND['deep']}) !important;
        color: white !important;
        border: none !important;
        padding: 0.6rem 1.5rem !important;
        font-size: 0.90rem !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 14px rgba(48,120,144,0.30) !important;
        letter-spacing: 0.02em !important;
    }}
    [data-testid="baseButton-primary"]:hover {{
        background: linear-gradient(135deg, {BRAND['deep']}, #0d3f52) !important;
        box-shadow: 0 6px 20px rgba(24,96,120,0.38) !important;
        transform: translateY(-1px) !important;
    }}

    /* Footer */
    .login-footer {{
        font-size: 0.68rem;
        color: {BRAND['text_light']};
        text-align: center;
        margin-top: 2rem;
        letter-spacing: 0.04em;
    }}
    </style>
    """, unsafe_allow_html=True)

    # ── Left branding panel (pure HTML, fixed) ────────────────────
    logo_html = (
        f'<img src="data:image/png;base64,{logo_b64}" alt="Sylemax"/>'
        if logo_b64 else
        f'<div style="font-family:DM Serif Display,serif;font-size:2.5rem;'
        f'color:white;letter-spacing:-0.03em;margin-bottom:1rem;">Sylemax</div>'
    )
    st.markdown(f"""
    <div class="login-brand">
        {logo_html}
        <div class="login-brand-title">Academic Management<br>Effortless &amp; Tailored</div>
        <div class="login-brand-sub">Powered by Sylemax</div>
        <div class="login-brand-dots">
            <div class="login-brand-dot active"></div>
            <div class="login-brand-dot"></div>
            <div class="login-brand-dot"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Right form panel spacer (pushes content right of fixed panel) ──
    st.markdown('<div style="margin-left:42%;padding:2rem 3rem;">', unsafe_allow_html=True)

    # Heading
    st.markdown(f"""
    <div style="max-width:400px;margin:0 auto;">
        <div class="login-form-heading">Welcome back</div>
        <div class="login-form-sub">Sign in to your Sylemax account to continue</div>
    </div>
    """, unsafe_allow_html=True)

    # Constrain width
    _, col, _ = st.columns([0.001, 10, 0.001])
    with col:
        tab_login, tab_register = st.tabs(["🔑 Sign In", "📝 Register as Faculty"])

        # ── Sign In ───────────────────────────────────────────────
        with tab_login:
            with st.form("login_form"):
                email    = st.text_input("Email Address", placeholder="your@email.com")
                password = st.text_input("Password", type="password",
                                          placeholder="Enter your password")
                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
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
                        st.rerun()
                    else:
                        st.error("Incorrect email or password. Please try again.")

        # ── Register ──────────────────────────────────────────────
        with tab_register:
            st.markdown(
                f"<p style='font-size:0.78rem;color:{BRAND['text_light']};"
                f"margin-bottom:0.8rem;'>Faculty registration is reviewed by an administrator.</p>",
                unsafe_allow_html=True
            )
            with st.form("register_form"):
                c1, c2       = st.columns(2)
                first_name   = c1.text_input("First Name *",  placeholder="John")
                last_name    = c2.text_input("Last Name *",   placeholder="Smith")
                employee_id  = st.text_input("Employee ID *", placeholder="EMP-12345")
                reg_email    = st.text_input("Email *",       placeholder="faculty@institution.edu")
                c3, c4       = st.columns(2)
                reg_password = c3.text_input("Password *",        type="password", placeholder="Min 8 chars")
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
                        st.success("✅ Registration submitted! Admin will review your account.")
                    else:
                        st.error("Registration failed. This email may already be registered.")

    st.markdown(
        f"<div class='login-footer'>© Sylemax · Academic Management · Effortless &amp; Tailored</div>",
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)


# Alias for backward compatibility
login_page = render_login
