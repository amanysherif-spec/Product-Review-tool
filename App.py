import streamlit as st
import os
from groq import Groq

st.set_page_config(page_title="Review Moderation Tool", page_icon="🛡️")

# CSS قوي لإخفاء شارة Streamlit السفلية تماماً مع تغطيتها
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
            
            /* إخفاء وتغطية شارة Streamlit السفلية */
            div[class*="viewerBadge"] {display: none !important; visibility: hidden !important;}
            div[class*="styles_viewerBadge"] {display: none !important; visibility: hidden !important;}
            a[href*="streamlit.io/cloud"] {display: none !important; visibility: hidden !important;}
            
            /* إخفاء شريط الإطار السفلي بالكامل */
            footer {display: none !important; visibility: hidden !important;}
            .stAppFooter {display: none !important; visibility: hidden !important;}
            
            /* طبقة بيضاء لإخفاء الزاوية اليمنى السفلية تماماً */
            body::after {
                content: "";
                position: fixed;
                bottom: 0;
                right: 0;
                width: 250px;
                height: 60px;
                background-color: white;
                z-index: 999999;
                pointer-events: none;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.title("Review Moderation Tool")

api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

# Fixed default model in background
DEFAULT_MODEL = "qwen/qwen3.8-27b"

# Initialize Session State for input clearing
if "review_input" not in st.session_state:
    st.session_state.review_input = ""

def reset_field():
    st.session_state.review_input = ""

review_text = st.text_area("Enter Customer Review:", key="review_input", height=150)

# Layout for Buttons
col1, col2 = st.columns([1, 5])
with col1:
    evaluate_btn = st.button("Evaluate Review", type="primary")
with col2:
    st.button("Reset", on_click=reset_field)

GUIDELINES = """
EVALUATION CRITERIA FOR PRODUCT REVIEWS:

1. NOT ALLOWED (Decision: ❌ Not allowed — the review should be removed) ONLY IF it violates any of the following:

   A. Community Guideline Violations:
      - Promotional or advertising content.
      - Offensive, abusive, or illegal language.
      - Hate speech or discriminatory remarks.
      - Personal or sensitive information (phone numbers, full names, addresses, emails).

   B. Seller, Order, Shipping, or Packaging Feedback:
      - Focuses on seller performance or seller reputation.
      - Mentions ordering, returns, or customer service experience.
      - Mentions shipping, courier, delivery speed, or packaging.
      - Reports product damage during transit or missing items from the package.

   C. Invalid Pricing or Availability Comments:
      - Mentions finding the product cheaper elsewhere or competitor pricing.
      - Complains about stock status, out-of-stock items, or store-level availability.

   D. Conflicts of Interest & Anti-Manipulation:
      - Written by seller, competitor, employee, friend, family member, or business partner.
      - Posted in exchange for compensation or financial incentive.

---

2. ALLOWED (Decision: ✅ Allowed — it should not be removed) IF:
   - It focuses strictly on the product itself (quality, ease of use, value for money, performance, features, size, specs).
   - It expresses general price-to-value opinions (e.g., "Great quality for the price").
   - It expresses general product wishes (e.g., "Hope it comes in more colors").
   - It is a negative or positive personal usage experience with the item.
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

                OUTPUT INSTRUCTIONS:
                - Line 1 MUST start strictly with either:
                  ✅ Allowed — it should not be removed.
                  OR
                  ❌ Not allowed — the review should be removed.
                
                - Line 2 MUST provide a brief, clear explanation in English citing the specific guideline section.
                """

                response = client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )

                result = response.choices[0].message.content

                st.markdown("### Result:")
                if "Allowed — it should not be removed" in result:
                    st.success(result)
                else:
                    st.error(result)

            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("Please enter a review first.")
