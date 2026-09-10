import streamlit as st
import os
import streamlit.components.v1 as components
import re
from groq import Groq

st.set_page_config(page_title="Product Review Moderation Tool", page_icon="🛡️")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            [data-testid="stToolbar"] {visibility: hidden !important;}
            [data-testid="stStatusWidget"] {visibility: hidden !important;}
            [data-testid="stAppDeployButton"] {display: none !important;}
            .stAppDeployButton {display: none !important;}
            #stDecoration {display: none !important;}
            
            div[class*="stAppViewerToolbar"] {display: none !important;}
            [data-testid="stViewerBadge"] {display: none !important;}
            .stAppViewerToolbar {display: none !important;}
            div[class*="viewerBadge"] {display: none !important;}
            div[class*="styles_viewerBadge"] {display: none !important;}
            a[href*="streamlit.io/cloud"] {display: none !important;}
            
            div[class*="viewerBadge"] *,
            div[class*="styles_viewerBadge"] *,
            a[href*="streamlit.io"],
            a[href*="github.com"] {
                pointer-events: none !important;
                cursor: default !important;
            }

            .stAppFooter {display: none !important;}
            footer {display: none !important;}

            div.stButton > button {
                width: 100%;
                white-space: nowrap;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.title("Product Review Moderation Tool")

api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

if "review_input" not in st.session_state:
    st.session_state.review_input = ""
if "result_text" not in st.session_state:
    st.session_state.result_text = ""

lang_option = st.radio(
    "Select Output Language:",
    options=["English", "Arabic"],
    horizontal=True
)

def reset_field():
    st.session_state.review_input = ""
    st.session_state.result_text = ""

review_text = st.text_area("Enter Customer Review:", key="review_input", height=150)

col1, col2 = st.columns([2, 5])
with col1:
    evaluate_btn = st.button("Evaluate Review", type="primary")
with col2:
    st.button("Reset", on_click=reset_field)

GUIDELINES = """
1. Community Guideline Violations: Point 1: Promotional content | Point 2: Offensive/abusive/vulgar language | Point 3: Hate speech | Point 4: Personal info
2. Seller/Order/Shipping Feedback: Point 1: Seller performance | Point 2: Order/return experience | Point 3: Shipping/packaging/delivery | Point 4: Product damage or missing items
3. Pricing/Availability: Point 1: Competitor pricing | Point 2: Stock status
4. Conflicts of Interest: Point 1: Posted by seller/friend/family | Point 2: Paid review
"""

if evaluate_btn:
    if review_text.strip():
        if not api_key:
            st.error("GROQ_API_KEY environment variable is missing.")
        else:
            if lang_option == "English":
                lang_instruction = """
                OUTPUT FORMAT:
                * **Decision:** [Strictly '✅ Allowed — it should not be removed' OR '❌ Not allowed — the review should be removed']
                * **Main Guideline Section:** [Section number & name]
                * **Specific Sub-rule:** [Point designation & text]
                * **Comment:** [Direct explanation without greetings/salutations]
                """
            else:
                lang_instruction = """
                OUTPUT FORMAT (in Arabic):
                * **القرار:** ['✅ مسموح — لا ينبغي إزالته' OR '❌ غير مسموح — ينبغي إزالة المراجعة']
                * **القسم الرئيسي للإرشادات:** [اسم ورقم القسم]
                * **القاعدة الفرعية:** [رقم ونص القاعدة الفرعية]
                * **التعليق:** [شرح مباشر بدون أي مقدمات أو ألقاب]
                """

            prompt = f"""
            You are a compliance officer evaluating product reviews for noon based on these rules:
            {GUIDELINES}

            Review: "{review_text}"

            {lang_instruction}

            RULES:
            1. If broken/damaged/not working upon arrival, mark NOT ALLOWED under Section 2 - Point 4.
            2. If offensive/vulgar, mark NOT ALLOWED under Section 1 - Point 2.
            3. No greetings in Comment. Start directly with evaluation.
            """

            try:
                # الاستدلال المباشر بالنموذج الرسمي الشغال حالياً بدون قائمة أو تخمين
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=250
                )
                st.session_state.result_text = response.choices[0].message.content

            except Exception as e:
                st.error(f"Execution Error: {e}")
    else:
        st.warning("Please enter a review first.")

if st.session_state.result_text:
    st.markdown("### Result:")
    st.markdown(st.session_state.result_text)

    comment_text = ""
    match = re.search(r"(?:Comment|التعليق):\*\*\s*(.*)", st.session_state.result_text, re.DOTALL)
    if not match:
        match = re.search(r"(?:Comment|التعليق):\s*(.*)", st.session_state.result_text, re.DOTALL)
    
    if match:
        comment_text = match.group(1).strip()
    else:
        comment_text = st.session_state.result_text

    escaped_comment = comment_text.replace("`", "'").replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
    
    copy_button_html = f"""
    <button onclick="copyToClipboard()" style="
        background-color: #2e7d32;
        color: white;
        border: none;
        padding: 8px 16px;
        font-size: 14px;
        font-weight: bold;
        border-radius: 4px;
        cursor: pointer;
        margin-top: 10px;
        margin-bottom: 10px;">
        📋 Copy Comment
    </button>
    <script>
    function copyToClipboard() {{
        const text = "{escaped_comment}";
        navigator.clipboard.writeText(text).then(function() {{
            alert('Comment copied to clipboard!');
        }}, function(err) {{
            console.error('Could not copy comment: ', err);
        }});
    }}
    </script>
    """
    components.html(copy_button_html, height=65)

    st.markdown("---")
    st.markdown("**Guidelines Reference:**")
    st.markdown("https://help.noon.com/portal/en/kb/articles/product-review-guidelines")
