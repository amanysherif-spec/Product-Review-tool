import streamlit as st
import os
from groq import Groq

st.set_page_config(page_title="Product Review Moderation Tool", page_icon="🛡️")

# CSS لإخفاء كافة عناصر التحكم وشارات Streamlit وتعطيل التفاعل معها
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
EVALUATION CRITERIA FOR PRODUCT REVIEWS:

1. Community Guideline Violations:
   - Promotional or advertising content.
   - Offensive, abusive, or illegal language.
   - Hate speech or discriminatory remarks.
   - Personal or sensitive information (phone numbers, full names, addresses, emails).

2. Seller, Order, Shipping, or Packaging Feedback:
   - Seller performance or reputation.
   - Ordering or return experiences.
   - Shipping, packaging, or delivery speed.
   - Product damage or missing items.

3. Invalid Pricing or Availability Comments:
   - Mentions finding the product cheaper elsewhere or competitor pricing.
   - Complains about stock status, out-of-stock items, or store-level availability.

4. Conflicts of Interest & Anti-Manipulation:
   - Written by seller, competitor, employee, friend, family member, or business partner.
   - Posted in exchange for compensation or financial incentive.

5. Product-Focused Reviews (ALLOWED):
   - Focuses strictly on the product itself (quality, ease of use, value for money, performance, features, size, specs).
   - Expresses general price-to-value opinions (e.g., "Great quality for the price").
   - Expresses general product wishes or usage experience.
"""

if evaluate_btn:
    if review_text.strip():
        if not api_key:
            st.error("GROQ_API_KEY environment variable is missing.")
        else:
            try:
                prompt = f"""
                You are an automated compliance officer for an e-commerce platform.
                Evaluate the following customer review based strictly on the provided Product Review Guidelines.

                Guidelines:
                {GUIDELINES}

                Customer Review to evaluate: "{review_text}"

                OUTPUT REQUIREMENTS:
                Provide the evaluation strictly in BOTH English AND Arabic following this structure:

                Decision / القرار:
                [Start strictly with either: '✅ Allowed — it should not be removed / مسموح بها — لا يجب إزالتها' OR '❌ Not allowed — the review should be removed / غير مسموح بها — يجب إزالة المراجعة']

                Main Guideline / المرجع الرئيسي:
                [Specify the main section number and title, e.g., '2. Seller, Order, Shipping, or Packaging Feedback']

                Specific Sub-rule / النقطة الفرعية:
                [Specify the exact sub-point, e.g., 'Seller performance or reputation']

                Explanation / التوضيح:
                - English: [Brief clear explanation]
                - العربية: [توضيح مختصر وواضح بالعربية]
                """

                response = client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )

                result = response.choices[0].message.content

                st.markdown("### Result:")
                if "Allowed" in result or "مسموح بها" in result:
                    st.success(result)
                else:
                    st.error(result)

                # Fixed Link at the end of every result
                st.markdown("---")
                st.markdown("**Guidelines Reference / مرجع الإرشادات:**")
                st.markdown("https://help.noon.com/portal/en/kb/articles/noon-community-guidelines")

            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("Please enter a review first.")
