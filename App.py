import streamlit as st
import os
from groq import Groq

st.set_page_config(page_title="Review Moderation Tool", page_icon="🛡️")
st.title("Review Moderation Tool")

review_text = st.text_area("Enter Customer Review:", height=150)

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

if st.button("Evaluate Review"):
    if review_text.strip():
        try:
            client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

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
            
            - Line 2 MUST provide a brief, clear explanation in Arabic citing the specific guideline section (e.g., "السبب: التقييم يركز على الشحن والتوصيل بدلا من خامة المنتج").
            """

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
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