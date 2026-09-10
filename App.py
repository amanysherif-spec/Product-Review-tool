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

# نص إرشادات المقال الرسمي من noon بالضبط
ARTICLE_SECTIONS = """
EXACT ARTICLE SECTIONS & SUB-RULES FROM THE NOON GUIDELINES ARTICLE:

What Should a Review Include (Allowed & Valid Review Benchmarks):
- Section: What Should a Review Include | Point 1: What did you like about the product?
- Section: What Should a Review Include | Point 2: Is the product easy to use?
- Section: What Should a Review Include | Point 3: Does it offer good value for money?
- Section: What Should a Review Include | Point 4: Would you recommend it to others?
- Section: What Should a Review Include | Point 5: What should other customers know before buying this product?

What Is Not Allowed (Violations):
1. Community Guideline Violations:
   - Point 1: Promotional or advertising content
   - Point 2: Offensive, abusive, or illegal language
   - Point 3: Hate speech or discriminatory remarks
   - Point 4: Personal or sensitive information

2. Seller, Order, or Shipping Feedback:
   - Point 1: Seller performance or reputation
   - Point 2: Ordering or return experiences
   - Point 3: Shipping, packaging, or delivery speed
   - Point 4: Product damage or missing items

3. Comments About Pricing or Availability:
   - Point 1: Competitor pricing or price complaints like "Found it cheaper elsewhere"
   - Point 2: Stock status or store-level availability comments like "It's out of stock again"

4. Conflicts of Interest:
   - Point 1: Content created by friends, family members, employers, employees, business partners, or competitors
   - Point 2: Reviews posted in exchange for compensation of any kind
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
                * **Main Guideline Section:** [Must match exact section name from the article above. NEVER N/A]
                * **Specific Sub-rule:** [Must include exact Point designation and exact text from the article. NEVER N/A]
                * **Comment:** [Direct explanation quoting the review without greetings/salutations]
                """
            else:
                lang_instruction = """
                OUTPUT FORMAT (in Arabic):
                * **القرار:** ['✅ مسموح — لا ينبغي إزالته' OR '❌ غير مسموح — ينبغي إزالة المراجعة']
                * **القسم الرئيسي للإرشادات:** [يجب أن يطابق اسم القسم المذكور في المقال تماماً. يمنع كتابة N/A]
                * **القاعدة الفرعية:** [يجب تحديد رقم ونص النقطة بالضبط من المقال الرسمي. يمنع كتابة N/A]
                * **التعليق:** [شرح مباشر مع اقتباس النص بدون أي ألقاب أو مقدمات]
                """

            prompt = f"""
            You are a strict compliance officer evaluating product reviews for noon based ONLY on the provided article text:
            {ARTICLE_SECTIONS}

            Review: "{review_text}"

            {lang_instruction}

            MANDATORY INSTRUCTIONS:
            1. NEVER write 'N/A', 'None', or leave fields blank.
            2. If the review is ALLOWED and has no violations (e.g., "Very bad", "Good product"), map it to the closest matching point under the section "What Should a Review Include" (e.g., Point 1, Point 3, or Point 5) depending on whether it talks about general opinion, quality, value, or usage experience.
            3. If the review is NOT ALLOWED, map it directly to the violated section and point under "What Is Not Allowed" (Section 1, Section 2, Section 3, or Section 4).
            4. Copy the exact titles and point descriptions as written in the article context.
            5. No greetings in Comment. Start directly with the evaluation.
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
