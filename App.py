import streamlit as st
import os
import streamlit.components.v1 as components
import json
import time
from groq import Groq


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Product Review Moderation Tool",
    page_icon="🛡️",
    layout="centered"
)


# ============================================================
# HIDE STREAMLIT UI ELEMENTS
# ============================================================

hide_st_style = """
<style>

#MainMenu {
    visibility: hidden;
}

header {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

[data-testid="stToolbar"] {
    visibility: hidden !important;
}

[data-testid="stStatusWidget"] {
    visibility: hidden !important;
}

[data-testid="stAppDeployButton"] {
    display: none !important;
}

.stAppDeployButton {
    display: none !important;
}

#stDecoration {
    display: none !important;
}

div[class*="stAppViewerToolbar"] {
    display: none !important;
}

[data-testid="stViewerBadge"] {
    display: none !important;
}

.stAppViewerToolbar {
    display: none !important;
}

div[class*="viewerBadge"] {
    display: none !important;
}

div[class*="styles_viewerBadge"] {
    display: none !important;
}

a[href*="streamlit.io/cloud"] {
    display: none !important;
}

div[class*="viewerBadge"] *,
div[class*="styles_viewerBadge"] *,
a[href*="streamlit.io"],
a[href*="github.com"] {
    pointer-events: none !important;
    cursor: default !important;
}

.stAppFooter {
    display: none !important;
}

footer {
    display: none !important;
}

div.stButton > button {
    width: 100%;
    white-space: nowrap;
}

</style>
"""

st.markdown(hide_st_style, unsafe_allow_html=True)


# ============================================================
# TITLE
# ============================================================

st.title("Product Review Moderation Tool")


# ============================================================
# GROQ CONFIGURATION
# ============================================================

api_key = os.environ.get("GROQ_API_KEY")

if api_key:
    client = Groq(
        api_key=api_key,
        timeout=60.0,
        max_retries=0
    )
else:
    client = None


# Primary model + fallback model
MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b"
]


# ============================================================
# SESSION STATE
# ============================================================

if "review_input" not in st.session_state:
    st.session_state.review_input = ""

if "result" not in st.session_state:
    st.session_state.result = None

if "raw_result" not in st.session_state:
    st.session_state.raw_result = ""


# ============================================================
# RESET
# ============================================================

def reset_field():
    st.session_state.review_input = ""
    st.session_state.result = None
    st.session_state.raw_result = ""


# ============================================================
# LANGUAGE
# ============================================================

lang_option = st.radio(
    "Select Output Language / اختر لغة الرد:",
    options=["English", "Arabic"],
    horizontal=True
)


# ============================================================
# REVIEW INPUT
# ============================================================

review_text = st.text_area(
    "Enter Customer Review:",
    key="review_input",
    height=150
)


# ============================================================
# BUTTONS
# ============================================================

col1, col2 = st.columns([2, 5])

with col1:
    evaluate_btn = st.button(
        "Evaluate Review",
        type="primary",
        use_container_width=True
    )

with col2:
    st.button(
        "Reset",
        on_click=reset_field,
        use_container_width=True
    )


# ============================================================
# OFFICIAL NOON GUIDELINES
# ============================================================

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


# ============================================================
# JSON SCHEMA
# ============================================================

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": [
                "ALLOWED",
                "NOT_ALLOWED"
            ]
        },
        "section": {
            "type": "string"
        },
        "point": {
            "type": "string"
        },
        "comment": {
            "type": "string"
        }
    },
    "required": [
        "decision",
        "section",
        "point",
        "comment"
    ],
    "additionalProperties": False
}


# ============================================================
# SYSTEM / EVALUATION PROMPT
# ============================================================

def build_prompt(review, language):

    if language == "English":

        language_instruction = """
Return the final JSON values in clear, professional English.

The "decision" value MUST be exactly:
ALLOWED
or
NOT_ALLOWED

The "section" and "point" must use the exact official English
wording from the guidelines when the review is NOT_ALLOWED.

If the review is ALLOWED:
- Set "section" to "N/A"
- Set "point" to "N/A"
- Explain clearly in the comment why the review is allowed.

The comment MUST:
- Start directly with the explanation.
- NOT contain greetings.
- NOT contain salutations.
- NOT contain "Dear Seller", "Hi", "Hello", etc.
"""

    else:

        language_instruction = """
Return the final JSON values in clear, professional Arabic.

The "decision" value MUST still be exactly:
ALLOWED
or
NOT_ALLOWED

For NOT_ALLOWED:
- Translate the section and point accurately into Arabic.
- Keep the meaning exactly aligned with the official guideline.

For ALLOWED:
- Set "section" to "غير منطبق"
- Set "point" to "غير منطبق"
- Explain clearly in Arabic why the review is allowed.

The comment MUST:
- Start directly with the explanation.
- NOT contain greetings.
- NOT contain salutations.
- NOT contain "عزيزي البائع".
- NOT contain "مرحباً".
- NOT contain any opening greeting.
"""

    prompt = f"""
You are an automated compliance officer for noon product reviews.

Evaluate the customer review STRICTLY according to the official
Noon Community Guidelines provided below.

OFFICIAL GUIDELINES:
{GUIDELINES}

CUSTOMER REVIEW:
"{review}"

{language_instruction}

============================================================
DECISION RULES
============================================================

1. PROMOTIONAL / ADVERTISING

If the review contains promotional or advertising content,
mark it NOT_ALLOWED under:

Section 1 - Point 1.

------------------------------------------------------------

2. OFFENSIVE / VULGAR LANGUAGE

If the review contains vulgar, offensive, abusive,
inappropriate, or clearly distasteful language,
mark it NOT_ALLOWED under:

Section 1 - Point 2.

Do not classify ordinary negative opinions as offensive language.

------------------------------------------------------------

3. HATE / DISCRIMINATION

If the review contains hate speech or discriminatory remarks,
mark it NOT_ALLOWED under:

Section 1 - Point 3.

------------------------------------------------------------

4. PERSONAL / SENSITIVE INFORMATION

If the review exposes personal or sensitive information,
mark it NOT_ALLOWED under:

Section 1 - Point 4.

------------------------------------------------------------

5. SELLER / ORDER / SHIPPING FEEDBACK

If the review is about:

- Seller performance or reputation
- Ordering or return experience
- Shipping
- Packaging
- Delivery speed

mark it NOT_ALLOWED under the corresponding Section 2 point.

------------------------------------------------------------

6. PRODUCT DAMAGE / MISSING ITEMS

Mark the review NOT_ALLOWED under:

Section 2 - Point 4

ONLY when the customer actually reports that the received
product was:

- Broken
- Damaged
- Crushed
- Destroyed
- Missing an item

Examples include:
"product arrived broken"
"the item was damaged"
"المنتج وصل مكسور"
"المنتج تالف"
"المنتج مهلك"

IMPORTANT:

Do NOT trigger the damage rule when the word is only:

- Hypothetical
- Negated
- Used as a comparison
- Used to say that the product was NOT damaged

For example:

"The product was not damaged."

This must NOT be classified as a damage violation.

Also:

"I was worried it would arrive broken, but it arrived perfectly."

This must NOT be classified as a damage violation.

------------------------------------------------------------

7. PRICE / CHEAPER ELSEWHERE

If the review says that the customer found the same product
cheaper elsewhere or mentions competitor pricing,

mark it NOT_ALLOWED under:

Section 3 - Point 1.

Examples:

"Found it cheaper elsewhere"
"I found this cheaper on another website"
"Too expensive, I can buy it cheaper somewhere else"

------------------------------------------------------------

8. AVAILABILITY

If the review is about stock availability, out-of-stock status,
or store-level availability,

mark it NOT_ALLOWED under:

Section 3 - Point 2.

------------------------------------------------------------

9. CONFLICT OF INTEREST / MANIPULATION

If the review was written by a seller, competitor, employee,
friend, family member, or business partner,

mark it NOT_ALLOWED under:

Section 4 - Point 1.

If the review was posted in exchange for compensation
or a financial incentive,

mark it NOT_ALLOWED under:

Section 4 - Point 2.

------------------------------------------------------------

10. NORMAL PRODUCT OPINIONS

Negative opinions about the actual product itself are NOT
automatically violations.

Examples:

"I don't like the product."
"It is not effective."
"The product is too small."
"I expected it to be bigger."
"The quality is poor."
"The product is expensive."

These should normally be ALLOWED unless the review also
violates one of the official guidelines.

------------------------------------------------------------

11. IMPORTANT DECISION RULE

Do NOT mark a review NOT_ALLOWED merely because:

- It is negative.
- The customer is disappointed.
- The customer says the product is expensive.
- The customer says the product is small.
- The customer dislikes the product.
- The customer says the product does not work.

A violation must actually match one of the official guidelines.

------------------------------------------------------------

12. ALLOWED REVIEWS

If the review does not violate any official guideline:

decision = ALLOWED

section = N/A
point = N/A

Do NOT invent a violation just to select a section.

------------------------------------------------------------

Return ONLY valid JSON matching the required schema.
Do not return Markdown.
Do not return explanations outside the JSON.
"""

    return prompt


# ============================================================
# CALL GROQ WITH RETRY + FALLBACK
# ============================================================

def evaluate_with_groq(prompt):

    if not client:
        raise RuntimeError(
            "GROQ_API_KEY environment variable is missing."
        )

    last_error = None

    for model_index, model in enumerate(MODELS):

        # Try each model up to 2 times
        for attempt in range(2):

            try:

                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.0,
                    max_completion_tokens=1000,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "review_moderation",
                            "strict": True,
                            "schema": RESPONSE_SCHEMA
                        }
                    }
                )

                content = response.choices[0].message.content

                if not content:
                    raise ValueError(
                        f"{model} returned an empty response."
                    )

                # Validate JSON
                result = json.loads(content)

                # Validate required fields
                required_fields = [
                    "decision",
                    "section",
                    "point",
                    "comment"
                ]

                for field in required_fields:
                    if field not in result:
                        raise ValueError(
                            f"Missing field: {field}"
                        )

                # Validate decision
                if result["decision"] not in [
                    "ALLOWED",
                    "NOT_ALLOWED"
                ]:
                    raise ValueError(
                        "Invalid decision returned by model."
                    )

                return result, model

            except Exception as e:

                last_error = e

                # Wait before retry
                if attempt == 0:
                    time.sleep(1)

        # Move to fallback model
        if model_index < len(MODELS) - 1:
            continue

    raise RuntimeError(
        f"All AI models failed. Last error: {last_error}"
    )


# ============================================================
# FORMAT RESULT
# ============================================================

def format_result(result, language):

    decision = result["decision"]
    section = result["section"]
    point = result["point"]
    comment = result["comment"].strip()

    if language == "English":

        if decision == "ALLOWED":
            decision_text = "✅ Allowed — it should not be removed"
        else:
            decision_text = "❌ Not allowed — the review should be removed"

        formatted = f"""
**Decision:** {decision_text}

**Main Guideline Section:** {section}

**Specific Sub-rule:** {point}

**Comment:** {comment}
"""

    else:

        if decision == "ALLOWED":
            decision_text = "✅ مسموح — لا ينبغي إزالته"
        else:
            decision_text = "❌ غير مسموح — ينبغي إزالة المراجعة"

        formatted = f"""
**القرار:** {decision_text}

**القسم الرئيسي للإرشادات:** {section}

**القاعدة الفرعية:** {point}

**التعليق:** {comment}
"""

    return formatted


# ============================================================
# EVALUATE BUTTON
# ============================================================

if evaluate_btn:

    if not review_text.strip():

        st.warning(
            "Please enter a review first."
            if lang_option == "English"
            else "يرجى إدخال مراجعة أولاً."
        )

    elif not api_key:

        st.error(
            "GROQ_API_KEY environment variable is missing."
            if lang_option == "English"
            else "متغير GROQ_API_KEY غير موجود."
        )

    else:

        with st.spinner(
            "Evaluating review..."
            if lang_option == "English"
            else "جاري تقييم المراجعة..."
        ):

            try:

                prompt = build_prompt(
                    review_text.strip(),
                    lang_option
                )

                result, used_model = evaluate_with_groq(prompt)

                st.session_state.result = result
                st.session_state.raw_result = format_result(
                    result,
                    lang_option
                )

                # Store which model successfully responded
                st.session_state.used_model = used_model

            except Exception as e:

                st.session_state.result = None
                st.session_state.raw_result = ""

                st.error(
                    (
                        "The evaluation could not be completed. "
                        f"Please try again.\n\nError: {str(e)}"
                    )
                    if lang_option == "English"
                    else
                    (
                        "تعذر إكمال تقييم المراجعة. "
                        f"يرجى المحاولة مرة أخرى.\n\nالخطأ: {str(e)}"
                    )
                )


# ============================================================
# DISPLAY RESULT
# ============================================================

if st.session_state.result:

    st.markdown("### Result:")

    st.markdown(
        st.session_state.raw_result
    )

    # ========================================================
    # COMMENT ONLY
    # ========================================================

    comment_text = st.session_state.result.get(
        "comment",
        ""
    ).strip()

    if comment_text:

        # Safely encode the text for JavaScript
        escaped_comment = json.dumps(
            comment_text,
            ensure_ascii=False
        )

        copy_button_text = (
            "📋 Copy Comment"
            if lang_option == "English"
            else "📋 نسخ التعليق"
        )

        success_message = (
            "Comment copied to clipboard!"
            if lang_option == "English"
            else "تم نسخ التعليق!"
        )

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
            margin-bottom: 10px;
            width: 180px;">
            {copy_button_text}
        </button>

        <script>

        function copyToClipboard() {{

            const text = {escaped_comment};

            navigator.clipboard.writeText(text)
                .then(function() {{

                    alert("{success_message}");

                }})
                .catch(function(err) {{

                    console.error(
                        "Could not copy comment:",
                        err
                    );

                }});

        }}

        </script>
        """

        components.html(
            copy_button_html,
            height=65
        )


    # ========================================================
    # MODEL INFORMATION
    # ========================================================

    if "used_model" in st.session_state:

        st.caption(
            f"Model used: {st.session_state.used_model}"
        )


    # ========================================================
    # GUIDELINES REFERENCE
    # ========================================================

    st.markdown("---")

    st.markdown(
        "**Guidelines Reference:**"
    )

    st.markdown(
        "https://help.noon.com/portal/en/kb/articles/product-review-guidelines"
    )
