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

# STRICT 4-SECTION ARTICLE GUIDELINES ONLY
GUIDELINES = """
OFFICIAL NOON COMMUNITY GUIDELINES FOR PRODUCT REVIEWS:

1. Community Guideline Violations
   Point 1: Promotional or advertising content
   Point 2: Offensive, abusive, inappropriate, vulgar, or distasteful language (e.g., words like "مقرف", profane, disgusting, or insulting terms)
   Point 3: Hate speech or discriminatory remarks
   Point 4: Personal or sensitive information

2. Seller, Order, or Shipping Feedback
   Point 1: Seller performance or reputation
   Point 2: Ordering or return experiences
   Point 3: Shipping, packaging, or delivery speed
   Point 4: Product damage or missing items

3. Invalid Pricing or Availability Comments
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
                prompt = f"""
                You are an automated compliance officer for noon evaluating product reviews.
                Evaluate the customer review based STRICTLY and ONLY on the official 4-section Guidelines Article below.

                Guidelines Article:
                {GUIDELINES}

                Customer Review: "{review_text}"

                STRICT SELECTION INSTRUCTIONS:
                1. Do NOT create, add, or invent any Section 5 or external text. Use ONLY Sections 1, 2, 3, or 4 and their exact points listed above.
                2. Select the closest and most relevant numbered Section and Point from the article:
                   - If the review is NOT ALLOWED: Select the exact violated Section (1 to 4) and its exact Point.
                   - If the review is ALLOWED: Select the closest Section and Point from the article that the review complies with or relates to, and explicitly state in the Comment why it does NOT violate that specific rule.
                3. Do NOT modify or paraphrase the Section titles or Point text in the output. Copy them verbatim.

                CRITICAL INSTRUCTION FOR COMMENT:
                - Do NOT write 'Dear Seller,' or any greeting/salutation.
                - Start directly with the professional explanation.

                OUTPUT FORMAT TEMPLATE:

                * **Decision:** [Must be strictly '❌ Not allowed — the review should be removed' OR '✅ Allowed — it should not be removed']
                * **Main Guideline Section:** [Exact Section title and number verbatim from the 4 sections]
                * **Specific Sub-rule:** [Exact Point designation and text verbatim from the 4 sections]
                * **Comment:** [Explanation starting directly without any salutation]
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
