# EVALUATE REVIEW BUTTON - RED TEXT
# ------------------------------------------------------------

st.markdown(
    """
    <style>
    div[data-testid="stHorizontalBlock"]
    div[data-testid="stColumn"]:first-child
    div[data-testid="stButton"] button {
        color: red !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
