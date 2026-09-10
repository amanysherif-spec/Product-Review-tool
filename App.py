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
    "Select Output Language / اختر لغة الرد:",
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
OFFICIAL NOON COMMUNITY GUIDELINES FOR PRODUCT REVIEWS:

1. Community Guideline Violations
   Point 1: Promotional or advertising content
   Point 2: Offensive, abusive, inappropriate, vulgar, or distasteful language
   Point 3: Hate speech or discriminatory remarks
   Point 4: Personal or sensitive information

2. Seller, Order, or Shipping Feedback
   Point 1: Seller performance or reputation
   Point 2: Ordering or return experiences
   Point 3: Shipping, packaging, or delivery speed
   Point 4: Product damage or missing items

3. Comments About Pricing or Availability
   Point 1: Finding the product cheaper elsewhere or competitor pricing
   Point 2: Stock status, out-of-stock items, or store-level availability

4. Conflicts of Interest & Anti-Manipulation
   Point 1: Written by seller, competitor, employee, friend, family member, or business partner
   Point 2: Posted in exchange for compensation or financial incentive
"""

if evaluate_btn:
    if review_text.strip():
        if not api_key:
            st.error("GROQ_API_KEY environment variable is missing.")
        else:
            if lang_option == "English":
                lang_instruction = """
                OUTPUT FORMAT (Use strict Markdown bullet points on separate lines):
                * **Decision:** [Must be '✅ Allowed — it should not be removed' OR '❌ Not allowed — the review should be removed']
                * **Main Guideline Section:** [Exact Section title verbatim, or N/A if allowed]
                * **Specific Sub-rule:** [Exact Point designation and text verbatim, or N/A if allowed]
                * **Comment:** [Explanation text starting directly without any greeting or salutation]
                """
            else:
                lang_instruction = """
                OUTPUT FORMAT (Use strict Markdown bullet points on separate lines in Arabic):
                * **القرار:** ['✅ مسموح — لا ينبغي إزالته' أو '❌ غير مسموح — ينبغي إزالة المراجعة']
                * **القسم الرئيسي للإرشادات:** [اسم القسم المخالف، أو N/A إذا كان مسموحاً]
                * **القاعدة الفرعية:** [النقطة المخالفة، أو N/A إذا كان مسموحاً]
                * **التعليق:** [شرح مباشر بدون أي مقدمات أو ألقاب]
                """

            prompt = f"""
            You are an automated compliance officer for noon evaluating product reviews.
            Evaluate the customer review strictly based on these rules:

            Guidelines Article:
            {GUIDELINES}

            Customer Review to evaluate: "{review_text}"

            {lang_instruction}

            EVALUATION RULES:
            1. Simple negative product ratings (e.g., "Very bad", "Bad product", "Poor quality", "سيء جداً") are 100% ALLOWED.
            2. Mark NOT ALLOWED under Section 1 - Point 2 ONLY if there are explicit vulgar words, profanity, or insult phrases (e.g., "زبالة", "حرامية", "شتيمة").
            3. Mark NOT ALLOWED under Section 2 - Point 4 if the product arrived broken, damaged, or destroyed.
            4. If the review is ALLOWED, set Main Guideline Section and Specific Sub-rule to 'N/A' (or 'لا يوجد').
            5. Do NOT write greetings or salutations in the Comment.
            """

            # قائمة النماذج المستقرة مع ترتيب أفضليتها
            preferred_models = [
                "llama-3.3-70b-versatile",
                "llama3-70b-8192",
                "mixtral-8x7b-32768"
            ]

            success = False
            last_error = ""

            for model_id in preferred_models:
                try:
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.0
                    )
                    st.session_state.result_text = response.choices[0].message.content
                    success = True
                    break
                except Exception as e:
                    last_error = str(e)
                    continue

            if not success:
                st.error(f"Execution Error: {last_error if last_error else 'Unable to process request.'}")
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
