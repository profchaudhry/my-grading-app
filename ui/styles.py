import streamlit as st

def load_styles():
    st.markdown("""
        <style>
            .main-title {
                font-size: 40px;
                font-weight: 700;
                text-align: center;
                margin-top: 40px;
            }
            .sub-title {
                font-size: 18px;
                text-align: center;
                color: gray;
                margin-bottom: 40px;
            }
        </style>
    """, unsafe_allow_html=True)
