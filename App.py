import streamlit as st
import os
import streamlit.components.v1 as components
import re
from groq import Groq

st.set_page_config(page_title="Product Review Moderation Tool", page_icon="🛡️")

# CSS لإخفاء عناصر التحكم وتعديل أبعاد الزر الرئيسي لمنع قص النص
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

            /* تحسين عرض الأزرار لمنع قص النص */
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

DEFAULT_MODEL = "qwen/qwen3.8-27b"

if "review_input" not in st.session_state:
    st.session_state.review_input = ""
if "result_text" not in st.session_state:
    st.session_state.result_text = ""

def reset_field():
    st.session_state.review_input = ""
    st.session_state.result_text = ""

# اختيار لغة الرد
lang_option = st.radio(
    "Select Output Language / اختر لغة الرد:",
    options=["English", "Arabic"],
    horizontal=True
)

review_text = st.text_area("Enter Customer Review:", key="review_input", height=150)

# تنظيم أبعاد الأزرار
col1, col2 = st.columns([2, 5])
with col1:
    evaluate_btn = st.button("Evaluate Review", type="primary")
with col2:
    st.button("Reset", on_click=reset_field)

# EXACT VERBATIM NOON ARTICLE GUIDELINES
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
            try:
                lang_instruction = (
                    "Output the response in English, maintaining exact guideline titles verbatim."
                    if lang_option == "English"
                    else "Output the evaluation and Comment in professional Arabic, while strictly keeping the Decision exact format."
                )

                prompt = f"""
                You are an automated compliance officer for noon evaluating product reviews.
                Evaluate the customer review based STRICTLY and VERBATIM on the official Guidelines Article provided below.

                Guidelines Article:
                {GUIDELINES}

                Customer Review to evaluate: "{review_text}"

                LANGUAGE INSTRUCTION:
                {lang_instruction}

                STRICT VERBATIM SELECTION RULES:
                1. You MUST copy the exact text and section numbers from the Guidelines Article above for 'Main Guideline Section' and 'Specific Sub-rule'. Do NOT alter, abbreviate, rephrase, or change any words.
                2. Evaluate the review against the article:
                   - If the review is NOT ALLOWED: Select the exact violated Section and Point.
                   - If the review is ALLOWED: Select the closest and most relevant Section and Point from the article that the review touches upon or complies with, and explicitly explain in the Comment why the review does NOT violate that rule.
                3. CRITICAL SECURITY RULE: Any review containing vulgar, offensive, or distasteful language (e.g., words like "مقرف", abusive slang, or insults) MUST be marked as NOT ALLOWED under '1. Community Guideline Violations' - 'Point 2: Offensive, abusive, inappropriate, vulgar, or distasteful language'.

                CRITICAL INSTRUCTION FOR COMMENT:
                - Do NOT include any greetings or salutations like 'Dear Seller,', 'Hi,', 'مرحباً عزيزي البائع' or 'عزيزي البائع'.
                - Start directly with the professional explanation text.

                OUTPUT FORMAT TEMPLATE:

                * **Decision:** [Must be STRICTLY either '✅ Allowed — it should not be removed' OR '❌ Not allowed — the review should be removed']
                * **Main Guideline Section:** [Exact Section number and title]
                * **Specific Sub-rule:** [Exact Point designation and text]
                * **Comment:** [Explanation text starting directly without any greeting or salutation]
                """

                response = client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0
                )

                st.session_state.result_text = response.choices[0].message.content

            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("Please enter a review first.")

if st.session_state.result_text:
    st.markdown("### Result:")
    st.markdown(st.session_state.result_text)

    # استخراج نص الـ Comment فقط لنسخه
    comment_text = ""
    match = re.search(r"Comment:\*\*\s*(.*)", st.session_state.result_text, re.DOTALL)
    if not match:
        match = re.search(r"Comment:\s*(.*)", st.session_state.result_text, re.DOTALL)
    
    if match:
        comment_text = match.group(1).strip()
    else:
        comment_text = st.session_state.result_text

    # تجهيز النص للـ JavaScript
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

    # Fixed Reference Link at the bottom
    st.markdown("---")
    st.markdown("**Guidelines Reference:**")
    st.markdown("https://help.noon.com/portal/en/kb/articles/noon-community-guidelines")
