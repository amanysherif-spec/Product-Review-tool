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

GUIDELINES = """
OFFICIAL NOON PRODUCT REVIEW GUIDELINES:

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

5. Product-Focused Reviews (Allowed)
   Point 1: Focuses strictly on the product itself (quality, performance, specs, value for money)
   Point 2: Expresses general price-to-value opinions or usage experience
"""

if evaluate_btn:
    if review_text.strip():
        if not api_key:
            st.error("GROQ_API_KEY environment variable is missing.")
        else:
            try:
                prompt = f"""
                You are an automated compliance officer for noon evaluating product reviews.
                Evaluate the following customer review based strictly on the provided official Product Review Guidelines.

                Guidelines:
                {GUIDELINES}

                Customer Review to evaluate: "{review_text}"

                CRITICAL INSTRUCTION FOR VULGAR / OFFENSIVE / DISTASTEFUL LANGUAGE:
                - Any review containing abusive, vulgar, inappropriate, disgusting, or distasteful words (such as "مقرف", abusive expressions, or foul phrasing) MUST be marked as NOT ALLOWED under '1. Community Guideline Violations' - 'Point 2: Offensive, abusive, inappropriate, vulgar, or distasteful language'.

                STRICT INSTRUCTIONS FOR SECTION & SUB-RULE TITLES:
                - For 'Main Guideline Section', use the exact section number and title as written in the article (e.g., '2. Seller, Order, or Shipping Feedback').
                - For 'Specific Sub-rule', use the exact point number and text as written in the article (e.g., 'Point 2: Ordering or return experiences').
                - Do NOT alter, abbreviate, or rephrase the section or sub-rule titles in any way.

                OUTPUT FORMAT RULES:
                Output strictly in English using standard Markdown formatting line by line.

                Follow this exact template:

                * **Decision:** [Must be strictly '❌ Not allowed — the review should be removed' OR '✅ Allowed — it should not be removed']
                * **Main Guideline Section:** [Exact section title and number from article]
                * **Specific Sub-rule:** [Exact point number and text from article]
                * **Comment:** [Write a professional explanation addressed to the seller detailing whether the review can or cannot be removed according to noon's guidelines, explicitly referencing the exact section and point number. DO NOT write 'Dear Seller,' or any greeting/salutation at the beginning. Start directly with the explanation text.]
                """

                response = client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
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
