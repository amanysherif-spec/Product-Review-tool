import streamlit as st
import os
import pandas as pd
import io
from groq import Groq

st.set_page_config(page_title="Product Review Moderation Tool", page_icon="🛡️")

# CSS لإخفاء عناصر التحكم وتعديل أبعاد الأزرار لعدم قطع النصوص
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
if "last_result" not in st.session_state:
    st.session_state.last_result = None

def reset_field():
    st.session_state.review_input = ""
    st.session_state.last_result = None

review_text = st.text_area("Enter Customer Review:", key="review_input", height=150)

# تعديل أبعاد الأعمدة لإعطاء المساحة الكافية للزر الرئيسي
col1, col2, col3 = st.columns([2, 1, 4])
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
            try:
                prompt = f"""
                You are an automated compliance officer for noon evaluating product reviews.
                Evaluate the customer review based STRICTLY and VERBATIM on the official Guidelines Article provided below.

                Guidelines Article:
                {GUIDELINES}

                Customer Review to evaluate: "{review_text}"

                STRICT VERBATIM SELECTION RULES:
                1. You MUST copy the exact text and section numbers from the Guidelines Article above for 'Main Guideline Section' and 'Specific Sub-rule'. Do NOT alter, abbreviate, rephrase, or change any words (e.g., use '3. Comments About Pricing or Availability' EXACTLY as written).
                2. Evaluate the review against the article:
                   - If the review is NOT ALLOWED: Select the exact violated Section and Point.
                   - If the review is ALLOWED: Select the closest and most relevant Section and Point from the article that the review touches upon or complies with, and explicitly explain in the Comment why the review does NOT violate that rule.
                3. CRITICAL SECURITY RULE: Any review containing vulgar, offensive, or distasteful language (e.g., words like "مقرف", abusive slang, or insults) MUST be marked as NOT ALLOWED under '1. Community Guideline Violations' - 'Point 2: Offensive, abusive, inappropriate, vulgar, or distasteful language'.

                CRITICAL INSTRUCTION FOR COMMENT:
                - Do NOT include any greetings or salutations like 'Dear Seller,', 'Hi,', or 'Hello'.
                - Start directly with the professional explanation text.

                OUTPUT FORMAT TEMPLATE:

                Decision: [Must be strictly '❌ Not allowed — the review should be removed' OR '✅ Allowed — it should not be removed']
                Main Guideline Section: [Exact Section number and title verbatim from the article]
                Specific Sub-rule: [Exact Point designation and text verbatim from the article]
                Comment: [Explanation text starting directly without any greeting or salutation]
                """

                response = client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0
                )

                raw_output = response.choices[0].message.content
                st.session_state.last_result = raw_output

            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("Please enter a review first.")

if st.session_state.last_result:
    st.markdown("### Result:")
    st.markdown(st.session_state.last_result)

    # تجهيز البيانات للتحميل
    lines = [line.strip() for line in st.session_state.last_result.split('\n') if line.strip()]
    parsed_data = {"Review": review_text}
    
    for line in lines:
        if line.startswith("Decision:") or line.startswith("* **Decision:**"):
            parsed_data["Decision"] = line.split(":", 1)[1].strip().replace("**", "")
        elif line.startswith("Main Guideline Section:") or line.startswith("* **Main Guideline Section:**"):
            parsed_data["Main Guideline Section"] = line.split(":", 1)[1].strip().replace("**", "")
        elif line.startswith("Specific Sub-rule:") or line.startswith("* **Specific Sub-rule:**"):
            parsed_data["Specific Sub-rule"] = line.split(":", 1)[1].strip().replace("**", "")
        elif line.startswith("Comment:") or line.startswith("* **Comment:**"):
            parsed_data["Comment"] = line.split(":", 1)[1].strip().replace("**", "")

    df = pd.DataFrame([parsed_data])

    # تحويل البيانات إلى CSV
    csv_data = df.to_csv(index=False).encode('utf-8-sig')

    # تحويل البيانات إلى Excel
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Moderation Result')
    excel_data = excel_buffer.getvalue()

    st.markdown("---")
    st.markdown("**Download Result:**")
    dl_col1, dl_col2, _ = st.columns([2, 2, 3])
    
    with dl_col1:
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name="moderation_result.csv",
            mime="text/csv"
        )
    with dl_col2:
        st.download_button(
            label="📊 Download Excel",
            data=excel_data,
            file_name="moderation_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.markdown("---")
    st.markdown("**Guidelines Reference:**")
    st.markdown("https://help.noon.com/portal/en/kb/articles/noon-community-guidelines")
