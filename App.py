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

# القواعد بنفس المصطلحات المكتوبة في الصورة تماماً
GUIDELINES_TEXT = """
1. Community Guideline Violations: Point 1: Promotional or advertising content | Point 2: Offensive, abusive, inappropriate, vulgar, or distasteful language | Point 3: Hate speech or discriminatory remarks | Point 4: Personal or sensitive information
2. Seller, Order, or Shipping Feedback: Point 1: Seller performance or reputation | Point 2: Ordering or return experiences | Point 3: Shipping, packaging, or delivery speed | Point 4: Product damage or missing items
3. Comments About Pricing or Availability: Point 1: Competitor pricing or comparisons | Point 2: Stock status or store-level availability
4. Conflicts of Interest: Point 1: Created by friends, family, employers, or competitors | Point 2: Posted in exchange for compensation
"""

if evaluate_btn:
    if review_text.strip():
        if not api_key:
            st.error("GROQ_API_KEY environment variable is missing.")
        else:
            if lang_option == "English":
                lang_instruction = """
You MUST output EXACTLY 4 bullet points using markdown (`* `). Do not output plain sentences.

* **Decision:** [Strictly '✅ Allowed — it should not be removed' OR '❌ Not allowed — the review should be removed']
* **Main Guideline Section:** [Section Name e.g. '1. Community Guideline Violations' OR 'N/A' if Allowed]
* **Specific Sub-rule:** [Sub-rule text e.g. 'Point 2: Offensive, abusive, inappropriate, vulgar, or distasteful language' OR 'N/A' if Allowed]
* **Comment:** [Detailed explanation mentioning the specific review text without any greetings]
"""
            else:
                lang_instruction = """
يجب إخراج التقييم في 4 نقاط دقيقة باستخدام Markdown (`* `):

* **القرار:** ['✅ مسموح — لا ينبغي إزالته' أو '❌ غير مسموح — ينبغي إزالة المراجعة']
* **القسم الرئيسي للإرشادات:** [اسم القسم المخالف أو 'لا يوجد' إذا كان مسموحاً]
* **القاعدة الفرعية:** [اسم ونص القاعدة الفرعية المخالفة أو 'لا يوجد' إذا كان مسموحاً]
* **التعليق:** [شرح تفصيلي مع اقتباس النص بدون أي مقدمات أو ألقاب]
"""

            prompt = f"""
You are a strict product review compliance officer evaluating customer reviews based on these exact rules:
{GUIDELINES_TEXT}

Review to evaluate: "{review_text}"

{lang_instruction}

STRICT CRITERIA:
1. Normal negative feedback about product quality/usability (e.g. "Very bad", "Poor product") is ALLOWED. Main Guideline Section and Specific Sub-rule MUST be N/A.
2. If the review contains vulgar words, insults, or profanity (e.g., "زبالة"), it is NOT ALLOWED under Section 1, Point 2.
3. Every single field MUST be printed on a NEW LINE as a Bullet Point (`* `).
"""

            try:
                available_models = client.models.list().data
                active_text_models = [
                    m.id for m in available_models 
                    if not any(excluded in m.id.lower() for excluded in ["whisper", "orpheus", "guard", "vision"])
                ]
            except Exception:
                active_text_models = []

            success = False
            last_error = ""

            for model_id in active_text_models:
                try:
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.0,
                        max_tokens=300
                    )
                    st.session_state.result_text = response.choices[0].message.content
                    success = True
                    break
                except Exception as e:
                    last_error = str(e)
                    continue

            if not success:
                st.error(f"Execution Error: {last_error if last_error else 'No active text models found'}")
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
