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

# Exact Official Guidelines text matching the Help Article
GUIDELINES = """
OFFICIAL NOON COMMUNITY GUIDELINES FOR PRODUCT REVIEWS:

Section 1: Community Guideline Violations
- Point 1: Promotional or advertising content
- Point 2: Offensive, abusive, inappropriate, vulgar, or distasteful language
- Point 3: Hate speech or discriminatory remarks
- Point 4: Personal or sensitive information

Section 2: Seller, Order, or Shipping Feedback
- Point 1: Seller performance or reputation
- Point 2: Ordering or return experiences
- Point 3: Shipping, packaging, or delivery speed
- Point 4: Product damage or missing items

Section 3: Invalid Pricing or Availability Comments
- Point 1: Finding the product cheaper elsewhere or competitor pricing
- Point 2: Stock status, out-of-stock items, or store-level availability

Section 4: Conflicts of Interest & Anti-Manipulation
- Point 1: Written by seller, competitor, employee, friend, family member, or business partner
- Point 2: Posted in exchange for compensation or financial incentive

Section 5: Product-Focused Reviews
- Point 1: Focuses strictly on the product itself (quality, performance, specs, value for money)
- Point 2: Expresses general price-to-value opinions or usage experience
"""

if evaluate_btn:
    if review_text.strip():
        if not api_key:
            st.error("GROQ_API_KEY environment variable is missing.")
        else:
            try:
                prompt = f"""
                You are an automated compliance officer for noon evaluating product reviews.
                Evaluate the customer review based STRICTLY and EXACTLY on the official Product Review Article provided below.

                Guidelines Article:
                {GUIDELINES}

                Customer Review: "{review_text}"

                STRICT RULES FOR SECTION AND SUB-RULE CITATIONS:
                1. You MUST copy the exact text and numbers from the guidelines article above without any modification, addition, or paraphrasing.
                2. 'Main Guideline Section' must be verbatim (e.g., 'Section 2: Seller, Order, or Shipping Feedback' or 'Section 1: Community Guideline Violations').
                3. 'Specific Sub-rule' must be verbatim (e.g., 'Point 2: Ordering or return experiences' or 'Point 2: Offensive, abusive, inappropriate, vulgar, or distasteful language').

                CRITICAL INSTRUCTIONS FOR COMMENT FIELD:
                - Do NOT include any greetings or salutations such as 'Dear Seller,', 'Hi,', or 'Hello'.
                - Start the Comment immediately with the explanation text.
                - Explicitly quote the exact Section name and Point number in the explanation so the seller can reference the exact article rule.

                OUTPUT FORMAT RULES:
                Output strictly in English using standard Markdown formatting line by line.

                Follow this exact template:

                * **Decision:** [Must be strictly '❌ Not allowed — the review should be removed' OR '✅ Allowed — it should not be removed']
                * **Main Guideline Section:** [Exact Section title and number from article]
                * **Specific Sub-rule:** [Exact Point designation and text from article]
                * **Comment:** [Explanation text starting directly without any salutation or 'Dear Seller,']
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
