import streamlit as st
import os
import streamlit.components.v1 as components
import json
import re
import time
from groq import Groq


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Product Review Moderation Tool",
    page_icon="🛡️",
    layout="centered"
)


# =========================================================
# HIDE STREAMLIT UI
# =========================================================

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

div.stButton > button {
    width: 100%;
    white-space: nowrap;
}

</style>
"""

st.markdown(
    hide_st_style,
    unsafe_allow_html=True
)


# =========================================================
# TITLE
# =========================================================

st.title("Product Review Moderation Tool")


# =========================================================
# GROQ CONFIGURATION
# =========================================================

api_key = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=api_key) if api_key else None


# Production model
PRIMARY_MODEL = "openai/gpt-oss-120b"

# Backup model
FALLBACK_MODEL = "qwen/qwen3.6-27b"


# =========================================================
# SESSION STATE
# =========================================================

if "review_input" not in st.session_state:
    st.session_state.review_input = ""

if "result" not in st.session_state:
    st.session_state.result = None

if "comment_text" not in st.session_state:
    st.session_state.comment_text = ""


# =========================================================
# LANGUAGE
# =========================================================

lang_option = st.radio(
    "Select Output Language / اختر لغة الرد:",
    options=["English", "Arabic"],
    horizontal=True
)


# =========================================================
# RESET
# =========================================================

def reset_field():

    st.session_state.review_input = ""
    st.session_state.result = None
    st.session_state.comment_text = ""


# =========================================================
# REVIEW INPUT
# =========================================================

review_text = st.text_area(
    "Enter Customer Review:",
    key="review_input",
    height=150
)


# =========================================================
# BUTTONS
# =========================================================

col1, col2 = st.columns([2, 5])

with col1:

    evaluate_btn = st.button(
        "Evaluate Review",
        type="primary"
    )

with col2:

    st.button(
        "Reset",
        on_click=reset_field
    )


# =========================================================
# OFFICIAL NOON GUIDELINES
# =========================================================

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


# =========================================================
# JSON SCHEMA
# =========================================================

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {

        "decision": {
            "type": "string",
            "enum": [
                "ALLOWED",
                "NOT_ALLOWED"
            ]
        },

        "section_number": {
            "type": "integer",
            "enum": [
                1,
                2,
                3,
                4
            ]
        },

        "section_title": {
            "type": "string"
        },

        "point_number": {
            "type": "integer",
            "enum": [
                1,
                2,
                3,
                4
            ]
        },

        "point_text": {
            "type": "string"
        },

        "reason": {
            "type": "string"
        },

        "comment": {
            "type": "string"
        }

    },

    "required": [
        "decision",
        "section_number",
        "section_title",
        "point_number",
        "point_text",
        "reason",
        "comment"
    ],

    "additionalProperties": False
}


# =========================================================
# LANGUAGE INSTRUCTIONS
# =========================================================

def get_language_instruction():

    if lang_option == "English":

        return """
Return all textual fields in clear, professional English.

The decision field MUST remain exactly:
ALLOWED
or
NOT_ALLOWED.

Do not use Arabic in the output.
"""

    else:

        return """
Return all textual fields in clear, professional Arabic.

The decision field MUST remain exactly:
ALLOWED
or
NOT_ALLOWED.

Translate the section title, point text, reason and comment into
professional Arabic.

Do not use English explanations in those fields.
"""


# =========================================================
# BUILD AI PROMPT
# =========================================================

def build_prompt(review, rule_engine_result):

    return f"""
You are a highly accurate Product Review Moderation Officer for noon.

Your task is to evaluate ONE customer product review against ONLY
the official noon Community Guidelines provided below.

============================================================
OFFICIAL NOON GUIDELINES
============================================================

{GUIDELINES}

============================================================
CUSTOMER REVIEW
============================================================

"{review}"

============================================================
RULE ENGINE INFORMATION
============================================================

The application has independently checked the review.

Rule engine result:

{json.dumps(rule_engine_result, ensure_ascii=False)}

You MUST consider this information carefully.

If the rule engine identifies a confirmed violation, do NOT override
that confirmed violation.

If the rule engine identifies no confirmed violation, perform the
full contextual evaluation yourself.

============================================================
IMPORTANT CLASSIFICATION RULES
============================================================

1. PRODUCT OPINIONS

Normal opinions about the product itself are ALLOWED unless they
violate one of the official guidelines.

Examples that should NOT automatically be removed:

- "I don't like it."
- "The product is not good."
- "It doesn't work."
- "The battery is weak."
- "The quality is poor."
- "I expected better."
- "The color is not nice."

Do NOT classify a normal product complaint as seller feedback.

------------------------------------------------------------

2. PRODUCT DAMAGE

If the review clearly says that the physical product arrived:

- broken
- damaged
- crushed
- destroyed
- cracked
- physically damaged
- مكسور
- تالف
- خربان
- مهلك

then classify it as:

NOT_ALLOWED

Section 2:
Seller, Order, or Shipping Feedback

Point 4:
Product damage or missing items

------------------------------------------------------------

3. MISSING ITEM

If the customer clearly says that an item, component,
accessory, or part was missing from the order, classify it as:

NOT_ALLOWED

Section 2:
Seller, Order, or Shipping Feedback

Point 4:
Product damage or missing items

------------------------------------------------------------

4. SELLER FEEDBACK

If the review is specifically about:

- seller behavior
- seller performance
- seller reputation
- seller service

classify it under:

Section 2 - Point 1

------------------------------------------------------------

5. ORDER / RETURN EXPERIENCE

If the review specifically discusses:

- placing an order
- cancelling an order
- returning an order
- refund/order experience

classify it under:

Section 2 - Point 2

------------------------------------------------------------

6. SHIPPING / DELIVERY / PACKAGING

If the review specifically complains about:

- shipping
- delivery
- delivery speed
- packaging
- courier/delivery experience

classify it under:

Section 2 - Point 3

------------------------------------------------------------

7. PRICE

If the customer says the same product is cheaper elsewhere,
or compares the product price with another store/seller,
classify it under:

Section 3 - Point 1

------------------------------------------------------------

8. AVAILABILITY

If the review is about:

- out of stock
- unavailable
- store availability
- product availability

classify it under:

Section 3 - Point 2

------------------------------------------------------------

9. PROMOTIONAL CONTENT

If the review contains advertising, promotional or marketing
content, classify it under:

Section 1 - Point 1

------------------------------------------------------------

10. OFFENSIVE LANGUAGE

If the review contains clearly vulgar, abusive, offensive,
inappropriate, or distasteful language, classify it under:

Section 1 - Point 2

Do not mark ordinary negative opinions as offensive.

------------------------------------------------------------

11. HATE SPEECH

If the review contains hate speech or discriminatory remarks,
classify it under:

Section 1 - Point 3

------------------------------------------------------------

12. PERSONAL INFORMATION

If the review exposes personal or sensitive information,
classify it under:

Section 1 - Point 4

------------------------------------------------------------

13. CONFLICT OF INTEREST

Only classify under Section 4 when there is actual evidence
or a clear statement indicating:

- seller
- competitor
- employee
- friend
- family member
- business partner

or that the review was posted in exchange for compensation
or a financial incentive.

Do NOT assume a conflict of interest without evidence.

------------------------------------------------------------

14. ALLOWED REVIEWS

If the review does not violate any guideline:

decision = ALLOWED

Select the closest relevant guideline section and point,
but clearly explain in the reason and comment that the review
does NOT violate that guideline.

------------------------------------------------------------

15. DO NOT INVENT RULES

You MUST NOT create a new guideline.

You MUST select the section and point from the official article only.

------------------------------------------------------------

16. COMMENT

The comment must:

- directly explain the decision
- be professional
- be concise
- contain no greeting
- contain no salutation
- not start with "Dear Seller"
- not start with "Hi"
- not start with "Hello"
- not start with "Dear"
- not start with "عزيزي البائع"
- not start with "مرحباً"

Start directly with the explanation.

============================================================
LANGUAGE
============================================================

{get_language_instruction()}
"""


# =========================================================
# HARD RULE ENGINE
# =========================================================

def normalize_text(text):

    text = text.lower().strip()

    # Normalize Arabic variants
    text = text.replace("أ", "ا")
    text = text.replace("إ", "ا")
    text = text.replace("آ", "ا")

    # Normalize spaces
    text = re.sub(r"\s+", " ", text)

    return text


def detect_hard_rules(review):

    text = normalize_text(review)

    violations = []


    # -----------------------------------------------------
    # PRODUCT DAMAGE
    # -----------------------------------------------------

    damage_patterns = [

        r"\bbroken\b",
        r"\bdamaged\b",
        r"\bcrushed\b",
        r"\bdestroyed\b",
        r"\bcracked\b",
        r"\bphysically damaged\b",

        r"\bmكسور\b",
        r"\bمكسور\b",
        r"\bتالف\b",
        r"\bخربان\b",
        r"\bمهلك\b",
        r"\bمتهالك\b"
    ]


    if any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in damage_patterns
    ):

        violations.append({
            "type": "PRODUCT_DAMAGE",
            "decision": "NOT_ALLOWED",
            "section_number": 2,
            "section_title": "Seller, Order, or Shipping Feedback",
            "point_number": 4,
            "point_text": "Product damage or missing items"
        })


    # -----------------------------------------------------
    # MISSING ITEM
    # -----------------------------------------------------

    missing_patterns = [

        r"\bmissing\b",
        r"\bmissing item\b",
        r"\bmissing items\b",
        r"\bmissing part\b",
        r"\bmissing parts\b",
        r"\bmissing accessory\b",
        r"\bmissing accessories\b",

        r"\bناقص\b",
        r"\bناقصه\b",
        r"\bناقصه\b",
        r"\bجزء ناقص\b",
        r"\bقطعه ناقصه\b"
    ]


    if any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in missing_patterns
    ):

        violations.append({
            "type": "MISSING_ITEM",
            "decision": "NOT_ALLOWED",
            "section_number": 2,
            "section_title": "Seller, Order, or Shipping Feedback",
            "point_number": 4,
            "point_text": "Product damage or missing items"
        })


    # -----------------------------------------------------
    # PRICE / COMPETITOR
    # -----------------------------------------------------

    price_patterns = [

        r"cheaper elsewhere",
        r"cheaper somewhere else",
        r"cheaper on another",
        r"lower price elsewhere",
        r"found it cheaper",
        r"more expensive here",
        r"expensive compared",

        r"ارخص في مكان اخر",
        r"ارخص في مكان آخر",
        r"ارخص برا",
        r"سعره ارخص"
    ]


    if any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in price_patterns
    ):

        violations.append({
            "type": "PRICE",
            "decision": "NOT_ALLOWED",
            "section_number": 3,
            "section_title": "Comments About Pricing or Availability",
            "point_number": 1,
            "point_text": "Finding the product cheaper elsewhere or competitor pricing"
        })


    # -----------------------------------------------------
    # AVAILABILITY
    # -----------------------------------------------------

    availability_patterns = [

        r"out of stock",
        r"out-of-stock",
        r"not available",
        r"unavailable",

        r"غير متوفر",
        r"غير متاح",
        r"نفذ من المخزون",
        r"خلص من المخزون"
    ]


    if any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in availability_patterns
    ):

        violations.append({
            "type": "AVAILABILITY",
            "decision": "NOT_ALLOWED",
            "section_number": 3,
            "section_title": "Comments About Pricing or Availability",
            "point_number": 2,
            "point_text": "Stock status, out-of-stock items, or store-level availability"
        })


    return violations


# =========================================================
# CALL GROQ
# =========================================================

def call_model(model, prompt):

    response = client.chat.completions.create(

        model=model,

        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict product review moderation "
                    "classifier. Follow the supplied guidelines exactly."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0,

        max_tokens=1000,

        reasoning_effort="medium",

        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "product_review_moderation",
                "strict": True,
                "schema": REVIEW_SCHEMA
            }
        }
    )

    content = response.choices[0].message.content

    return json.loads(content)


# =========================================================
# RETRY + FALLBACK SYSTEM
# =========================================================

def evaluate_with_reliability(prompt):

    models = [
        PRIMARY_MODEL,
        FALLBACK_MODEL
    ]

    last_error = None


    for model_index, model in enumerate(models):

        # Try each model up to 2 times
        for attempt in range(2):

            try:

                result = call_model(
                    model,
                    prompt
                )

                return result, model


            except Exception as e:

                last_error = e

                error_text = str(e).lower()


                # -------------------------------------------------
                # MODEL DECOMMISSION / NOT FOUND
                # -------------------------------------------------

                if (
                    "decommissioned" in error_text
                    or "model_not_found" in error_text
                    or "model not found" in error_text
                ):

                    break


                # -------------------------------------------------
                # RATE LIMIT / TEMPORARY ERROR
                # -------------------------------------------------

                if (
                    "429" in error_text
                    or "rate limit" in error_text
                    or "timeout" in error_text
                    or "temporarily unavailable" in error_text
                    or "503" in error_text
                    or "502" in error_text
                ):

                    time.sleep(2 ** attempt)

                    continue


                # Other errors
                if attempt == 1:

                    break


        # Move to fallback model

    raise last_error


# =========================================================
# VALIDATE AI RESULT
# =========================================================

def validate_result(result):

    required_fields = [

        "decision",
        "section_number",
        "section_title",
        "point_number",
        "point_text",
        "reason",
        "comment"

    ]


    for field in required_fields:

        if field not in result:

            raise ValueError(
                f"Missing field from AI response: {field}"
            )


    if result["decision"] not in [
        "ALLOWED",
        "NOT_ALLOWED"
    ]:

        raise ValueError(
            "Invalid decision returned by AI."
        )


    if result["section_number"] not in [
        1, 2, 3, 4
    ]:

        raise ValueError(
            "Invalid section number."
        )


    if result["point_number"] not in [
        1, 2, 3, 4
    ]:

        raise ValueError(
            "Invalid point number."
        )


    if not result["comment"].strip():

        raise ValueError(
            "Empty comment returned by AI."
        )


    return True


# =========================================================
# APPLY HARD RULES
# =========================================================

def apply_hard_rules(ai_result, hard_rules):

    if not hard_rules:

        return ai_result


    # If there are confirmed hard violations,
    # use the deterministic rule rather than allowing
    # the AI to override it.

    rule = hard_rules[0]


    ai_result["decision"] = "NOT_ALLOWED"

    ai_result["section_number"] = rule["section_number"]

    ai_result["section_title"] = rule["section_title"]

    ai_result["point_number"] = rule["point_number"]

    ai_result["point_text"] = rule["point_text"]


    return ai_result


# =========================================================
# FORMAT FINAL RESULT
# =========================================================

def format_result(result):

    decision = result["decision"]

    section_number = result["section_number"]
    section_title = result["section_title"]

    point_number = result["point_number"]
    point_text = result["point_text"]

    comment = result["comment"].strip()


    # Remove accidental greetings
    comment = re.sub(
        r"^(dear seller[,:\s]*|hi[,:\s]*|hello[,:\s]*)",
        "",
        comment,
        flags=re.IGNORECASE
    )

    comment = re.sub(
        r"^(عزيزي البائع[,:\s]*|مرحبا[,:\s]*|مرحباً[,:\s]*)",
        "",
        comment,
        flags=re.IGNORECASE
    )


    if lang_option == "English":

        if decision == "ALLOWED":

            decision_text = (
                "✅ Allowed — it should not be removed"
            )

        else:

            decision_text = (
                "❌ Not allowed — the review should be removed"
            )


        return f"""
**Decision:** {decision_text}

**Main Guideline Section:** {section_number}. {section_title}

**Specific Sub-rule:** Point {point_number}: {point_text}

**Comment:** {comment}
"""


    else:

        if decision == "ALLOWED":

            decision_text = (
                "✅ مسموح — لا ينبغي إزالته"
            )

        else:

            decision_text = (
                "❌ غير مسموح — ينبغي إزالة المراجعة"
            )


        section_translation = {
            1: "مخالفات إرشادات المجتمع",
            2: "ملاحظات البائع أو الطلب أو الشحن",
            3: "التعليقات المتعلقة بالسعر أو التوفر",
            4: "تعارض المصالح والتلاعب"
        }


        point_translation = {

            (1, 1):
                "المحتوى الترويجي أو الإعلاني",

            (1, 2):
                "اللغة المسيئة أو غير اللائقة أو البذيئة",

            (1, 3):
                "خطاب الكراهية أو التعليقات التمييزية",

            (1, 4):
                "المعلومات الشخصية أو الحساسة",

            (2, 1):
                "أداء البائع أو سمعته",

            (2, 2):
                "تجارب الطلب أو الإرجاع",

            (2, 3):
                "الشحن أو التغليف أو سرعة التوصيل",

            (2, 4):
                "تلف المنتج أو العناصر المفقودة",

            (3, 1):
                "العثور على المنتج بسعر أقل في مكان آخر أو مقارنة أسعار المنافسين",

            (3, 2):
                "حالة المخزون أو عدم توفر المنتج",

            (4, 1):
                "كتابة المراجعة من البائع أو المنافس أو الموظف أو شخص ذي صلة",

            (4, 2):
                "نشر المراجعة مقابل تعويض أو حافز مالي"
        }


        translated_section = section_translation.get(
            section_number,
            section_title
        )


        translated_point = point_translation.get(
            (section_number, point_number),
            point_text
        )


        return f"""
**القرار:** {decision_text}

**القسم الرئيسي للإرشادات:** {section_number}. {translated_section}

**القاعدة الفرعية:** النقطة {point_number}: {translated_point}

**التعليق:** {comment}
"""


# =========================================================
# EXTRACT COMMENT
# =========================================================

def extract_comment(formatted_result):

    match = re.search(
        r"\*\*(?:Comment|التعليق):\*\*\s*(.*)",
        formatted_result,
        re.DOTALL
    )


    if match:

        return match.group(1).strip()


    return formatted_result.strip()


# =========================================================
# EVALUATE
# =========================================================

if evaluate_btn:

    if not review_text.strip():

        st.warning(
            "Please enter a review first."
        )

    elif not api_key:

        st.error(
            "GROQ_API_KEY environment variable is missing."
        )

    else:

        try:

            with st.spinner(
                "Evaluating review..."
            ):

                # ---------------------------------------------
                # Step 1: Deterministic rules
                # ---------------------------------------------

                hard_rules = detect_hard_rules(
                    review_text
                )


                rule_engine_result = {
                    "confirmed_violations": hard_rules
                }


                # ---------------------------------------------
                # Step 2: AI evaluation
                # ---------------------------------------------

                prompt = build_prompt(
                    review_text,
                    rule_engine_result
                )


                ai_result, used_model = evaluate_with_reliability(
                    prompt
                )


                # ---------------------------------------------
                # Step 3: Validate
                # ---------------------------------------------

                validate_result(
                    ai_result
                )


                # ---------------------------------------------
                # Step 4: Apply deterministic rules
                # ---------------------------------------------

                final_result = apply_hard_rules(
                    ai_result,
                    hard_rules
                )


                # ---------------------------------------------
                # Step 5: Format
                # ---------------------------------------------

                formatted_result = format_result(
                    final_result
                )


                # ---------------------------------------------
                # Step 6: Save
                # ---------------------------------------------

                st.session_state.result = formatted_result

                st.session_state.comment_text = extract_comment(
                    formatted_result
                )


        except Exception as e:

            st.error(
                "The review could not be evaluated.\n\n"
                f"Error: {e}"
            )


# =========================================================
# DISPLAY RESULT
# =========================================================

if st.session_state.result:

    st.markdown("### Result:")

    st.markdown(
        st.session_state.result
    )


    # =====================================================
    # COPY COMMENT
    # =====================================================

    comment_text = (
        st.session_state.comment_text
    )


    # Safe JavaScript escaping
    escaped_comment = json.dumps(
        comment_text,
        ensure_ascii=False
    )


    copy_button_html = f"""
    <button
        onclick="copyToClipboard()"
        style="
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
        "
    >
        📋 Copy Comment
    </button>

    <script>

    function copyToClipboard() {{

        const text = {escaped_comment};

        navigator.clipboard.writeText(text)
            .then(function() {{

                alert("Comment copied to clipboard!");

            }})
            .catch(function(err) {{

                console.error(
                    "Could not copy comment: ",
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


    # =====================================================
    # GUIDELINES REFERENCE
    # =====================================================

    st.markdown("---")

    st.markdown(
        "**Guidelines Reference:**"
    )

    st.markdown(
        "https://help.noon.com/portal/en/kb/articles/product-review-guidelines"
    )
