import streamlit as st
import os
from groq import Groq

st.set_page_config(page_title="Product Review Moderation Tool", page_icon="🛡️")

# CSS لإخفاء عناصر التحكم وشارات Streamlit وتعطيل النقر عليها
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
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.title("Product Review Moderation Tool")

api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

DEFAULT_MODEL = "qwen/qwen3.8-27b"

if "review_input" not in st.session_state:
    st.session_state.review_input = ""

def reset_field():
    st.session_state.review_input = ""

review_text = st.text_area("Enter Customer Review:", key="review_input", height=150)

col1, col2 = st.columns([1, 5])
with col1:
    evaluate_btn = st.button("Evaluate Review", type="primary")
with col2:
    st.button("Reset", on_click=reset_field)

# OFFICIAL NOON PRODUCT REVIEW GUIDELINES
GUIDELINES = """
OFFICIAL NOON PRODUCT REVIEW GUIDELINES ARTICLE:

WHAT IS ALLOWED (Product-Focused Content Standards):
- Honest feedback and direct personal experience with the product itself (e.g., product quality, usage, performance, defect/failure during operation, specification, or price-to-value relationship).

WHAT IS NOT ALLOWED (Violations & Removal Reasons):

1. Community Guideline Violations
- Point 1: Promotional or advertising content
- Point 2: Offensive, abusive, inappropriate, vulgar, or distasteful language (e.g., words like "مقرف", profane, disgusting, or insulting terms)
- Point 3: Hate speech or discriminatory remarks
- Point 4: Personal or sensitive information

2. Seller, Order, or Shipping Feedback
- Point 1: Seller performance or reputation
- Point 2: Ordering or return experiences
- Point 3: Shipping, packaging, or delivery speed
- Point 4: Product damage or missing items

3. Invalid Pricing or Availability Comments
- Point 1: Finding the product cheaper elsewhere or competitor pricing
- Point 2: Stock status, out-of-stock items, or store-level availability

4. Conflicts of Interest & Anti-Manipulation
- Point 1: Written by seller, competitor, employee, friend, family member, or business partner
- Point 2: Posted in exchange for compensation or financial incentive
"""

if evaluate_btn:
    if review_text.strip():
        if not api_key:
            st.error("GROQ_API_KEY environment variable is missing.")
        else:
            try:
                prompt = f"""
                You are an automated compliance officer for noon evaluating product reviews.
                Evaluate the customer review based STRICTLY on the official Product Review Guidelines below.

                Guidelines Article:
                {GUIDELINES}

                Customer Review: "{review_text}"

                RULES FOR OUTPUT GENERATION (STRICTLY NO "N/A"):

                1. IF THE REVIEW VIOLATES GUIDELINES (NOT ALLOWED):
                   - **Decision:** ❌ Not allowed — the review should be removed
                   - **Main Guideline Section:** State the exact section number and title from the violation list (e.g., '2. Seller, Order, or Shipping Feedback').
                   - **Specific Sub-rule:** State the exact point designation and text (e.g., 'Point 2: Ordering or return experiences').

                2. IF THE REVIEW IS VALID AND COMPLIANT (ALLOWED):
                   - **Decision:** ✅ Allowed — it should not be removed
                   - **Main Guideline Section:** State the relevant compliant section standard (e.g., 'Product-Focused Feedback (Product Quality & Performance)'). NEVER write N/A.
                   - **Specific Sub-rule:** State the closest relevant reason from the article allowing this feedback (e.g., 'Direct personal experience regarding product defect / operational failure during usage'). NEVER write N/A.

                3. CRITICAL INSTRUCTION FOR COMMENT:
                   - NEVER start with 'Dear Seller,' or any greeting/salutation.
                   - Start directly with the explanation text explaining clearly why the review is allowed or not allowed with reference to the guidelines.

                OUTPUT FORMAT TEMPLATE:

                * **Decision:** [Decision text]
                * **Main Guideline Section:** [Main Section text]
                * **Specific Sub-rule:** [Specific Sub-rule text]
                * **Comment:** [Explanation text starting directly without any salutation]
                """

                response = client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0
                )

                result = response.choices[0].message.content

                st.markdown("### Result:")
                st.markdown(result)

                # Fixed Reference Link at the bottom
                st.markdown("---")
                st.markdown("**Guidelines Reference:**")
                st.markdown("https://help.noon.com/portal/en/kb/articles/noon-community-guidelines")

            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("Please enter a review first.")
