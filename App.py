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

# Production fallback model
FALLBACK_MODEL = "openai/gpt-oss-20b"


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
OFFICIAL NOON PRODUCT REVIEW GUIDELINES:

Product reviews should focus solely on the customer's personal
experience with the product itself.

WHAT IS NOT ALLOWED:

1. Community Guideline Violations

Point 1: Promotional or advertising content
Point 2: Offensive, abusive, or illegal language
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


4. Conflicts of Interest

Point 1: Reviews involving friends, family members, employers,
employees, business partners, associates, competitors, or
content about one's own products or services.

Point 2: Reviews posted in exchange for compensation or
financial incentives.
"""


# =========================================================
# RULE DEFINITIONS
# =========================================================

RULES = {

    "1.1": {
        "section_number": 1,
        "section_title": "Community Guideline Violations",
        "point_number": 1,
        "point_text": "Promotional or advertising content"
    },

    "1.2": {
        "section_number": 1,
        "section_title": "Community Guideline Violations",
        "point_number": 2,
        "point_text": "Offensive, abusive, or illegal language"
    },

    "1.3": {
        "section_number": 1,
        "section_title": "Community Guideline Violations",
        "point_number": 3,
        "point_text": "Hate speech or discriminatory remarks"
    },

    "1.4": {
        "section_number": 1,
        "section_title": "Community Guideline Violations",
        "point_number": 4,
        "point_text": "Personal or sensitive information"
    },

    "2.1": {
        "section_number": 2,
        "section_title": "Seller, Order, or Shipping Feedback",
        "point_number": 1,
        "point_text": "Seller performance or reputation"
    },

    "2.2": {
        "section_number": 2,
        "section_title": "Seller, Order, or Shipping Feedback",
        "point_number": 2,
        "point_text": "Ordering or return experiences"
    },

    "2.3": {
        "section_number": 2,
        "section_title": "Seller, Order, or Shipping Feedback",
        "point_number": 3,
        "point_text": "Shipping, packaging, or delivery speed"
    },

    "2.4": {
        "section_number": 2,
        "section_title": "Seller, Order, or Shipping Feedback",
        "point_number": 4,
        "point_text": "Product damage or missing items"
    },

    "3.1": {
        "section_number": 3,
        "section_title": "Comments About Pricing or Availability",
        "point_number": 1,
        "point_text": "Finding the product cheaper elsewhere or competitor pricing"
    },

    "3.2": {
        "section_number": 3,
        "section_title": "Comments About Pricing or Availability",
        "point_number": 2,
        "point_text": "Stock status, out-of-stock items, or store-level availability"
    },

    "4.1": {
        "section_number": 4,
        "section_title": "Conflicts of Interest",
        "point_number": 1,
        "point_text": "Conflict of interest involving related parties or competitors"
    },

    "4.2": {
        "section_number": 4,
        "section_title": "Conflicts of Interest",
        "point_number": 2,
        "point_text": "Review posted in exchange for compensation or financial incentive"
    }
}


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

        "rule_id": {
            "type": "string",
            "enum": [
                "NONE",
                "1.1",
                "1.2",
                "1.3",
                "1.4",
                "2.1",
                "2.2",
                "2.3",
                "2.4",
                "3.1",
                "3.2",
                "4.1",
                "4.2"
            ]
        },

        "section_number": {
            "type": "integer",
            "enum": [
                0,
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
                0,
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
        "rule_id",
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

The rule_id MUST remain exactly one of the supplied rule IDs.

Do not use Arabic in the output.
"""

    return """
Return all textual fields in clear, professional Arabic.

The decision field MUST remain exactly:
ALLOWED
or
NOT_ALLOWED.

The rule_id MUST remain exactly one of the supplied rule IDs.

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
the official noon Product Review Guidelines provided below.

============================================================
OFFICIAL NOON GUIDELINES
============================================================

{GUIDELINES}

============================================================
CUSTOMER REVIEW
============================================================

"{review}"

============================================================
INDEPENDENT RULE ENGINE
============================================================

The application has independently checked the review.

Rule engine result:

{json.dumps(rule_engine_result, ensure_ascii=False, indent=2)}

If the rule engine identifies a confirmed violation, you MUST use
that violation.

You MUST NOT change a confirmed violation to ALLOWED.

============================================================
CRITICAL PRICE RULE
============================================================

Section 3 - Point 1 is a VIOLATION.

The following are NOT_ALLOWED:

- "Found it cheaper elsewhere."
- "Found it cheaper."
- "I found this cheaper somewhere else."
- "It is cheaper on another website."
- "The same product is cheaper at another store."
- "I found a lower price from another seller."
- "It's cheaper online."
- "It's cheaper on Amazon."
- "It's cheaper on another marketplace."
- "وجدته بسعر أرخص"
- "وجدتها بسعر أرخص"
- "لقيته بسعر أرخص"
- "لقيتها بسعر أرخص"
- "وجدته أرخص"
- "لقيته أرخص"
- "ارخص في مكان اخر"
- "ارخص في محل اخر"
- "ارخص عند بائع اخر"

IMPORTANT:

Even if the customer does NOT explicitly mention another store,
website, seller, or competitor, phrases such as:

"Found it cheaper"
"وجدته بسعر أرخص"
"لقيته أرخص"

indicate that the customer found the same product at a lower price
elsewhere and MUST be classified as:

NOT_ALLOWED

Rule ID:
3.1

Section:
Comments About Pricing or Availability

Point:
Finding the product cheaper elsewhere or competitor pricing.

============================================================
PRICE COMMENTS THAT ARE ALLOWED
============================================================

Do NOT remove ordinary opinions about price or value when there
is NO comparison with another store, website, seller, marketplace,
or competitor.

Examples:

- "Good value for money."
- "Great quality for the price."
- "The price is reasonable."
- "The price is too high."
- "The price is expensive."
- "Not worth the price."
- "غالي بالنسبة للجودة"
- "السعر غالي"
- "السعر مناسب"
- "قيمة جيدة مقابل السعر"

These are ALLOWED unless another guideline is violated.

============================================================
PRODUCT OPINIONS
============================================================

Normal opinions about the product itself are ALLOWED unless they
violate one of the official guidelines.

Examples:

- "I don't like it."
- "The product is not good."
- "It doesn't work."
- "The battery is weak."
- "The quality is poor."
- "I expected better."
- "The color is not nice."

Do NOT classify a normal product complaint as seller feedback.

============================================================
PRODUCT DAMAGE
============================================================

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
- متهالك

classify it as:

NOT_ALLOWED

Rule ID:
2.4

============================================================
MISSING ITEM
============================================================

If the customer clearly says that an item, component, accessory,
or part was missing from the order, classify it as:

NOT_ALLOWED

Rule ID:
2.4

============================================================
SELLER FEEDBACK
============================================================

If the review is specifically about:

- seller behavior
- seller performance
- seller reputation
- seller service

classify it as:

NOT_ALLOWED

Rule ID:
2.1

============================================================
ORDER / RETURN EXPERIENCE
============================================================

If the review specifically discusses:

- placing an order
- cancelling an order
- returning an order
- refund/order experience

classify it as:

NOT_ALLOWED

Rule ID:
2.2

============================================================
SHIPPING / DELIVERY / PACKAGING
============================================================

If the review specifically complains about:

- shipping
- delivery
- delivery speed
- packaging
- courier/delivery experience

classify it as:

NOT_ALLOWED

Rule ID:
2.3

============================================================
AVAILABILITY
============================================================

If the review is specifically about:

- out of stock
- unavailable
- stock status
- store availability
- product availability

classify it as:

NOT_ALLOWED

Rule ID:
3.2

General wishes about availability are allowed.

Example:

"Hope it comes in more colors."

This is ALLOWED.

============================================================
PROMOTIONAL CONTENT
============================================================

If the review contains advertising, promotional, marketing,
discount codes, contact information intended for promotion,
or attempts to direct customers to another business, classify it as:

NOT_ALLOWED

Rule ID:
1.1

============================================================
OFFENSIVE LANGUAGE
============================================================

If the review contains clearly vulgar, abusive, offensive,
inappropriate, or illegal language, classify it as:

NOT_ALLOWED

Rule ID:
1.2

Do NOT mark ordinary negative opinions as offensive.

============================================================
HATE SPEECH
============================================================

If the review contains hate speech or discriminatory remarks,
classify it as:

NOT_ALLOWED

Rule ID:
1.3

============================================================
PERSONAL INFORMATION
============================================================

If the review exposes personal or sensitive information,
classify it as:

NOT_ALLOWED

Rule ID:
1.4

============================================================
CONFLICT OF INTEREST
============================================================

Only classify under Section 4 when there is actual evidence or
a clear statement indicating a conflict involving:

- seller
- competitor
- employee
- employer
- friend
- family member
- business partner
- associate

or when the review was posted in exchange for compensation
or a financial incentive.

Do NOT assume a conflict of interest without evidence.

Rule ID:
4.1 or 4.2

============================================================
ALLOWED REVIEWS
============================================================

If the review does not violate any official guideline:

decision = ALLOWED

rule_id = NONE

section_number = 0

point_number = 0

section_title = "No violation"

point_text = "No guideline violation identified"

The reason and comment MUST clearly state that the review does
not violate the official guidelines.

============================================================
DO NOT INVENT RULES
============================================================

You MUST NOT create a new guideline.

You MUST select only from the official rules listed above.

============================================================
COMMENT REQUIREMENTS
============================================================

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
# TEXT NORMALIZATION
# =========================================================

def normalize_text(text):

    text = str(text).lower().strip()

    # Remove Arabic diacritics
    text = re.sub(
        r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]",
        "",
        text
    )

    # Normalize Arabic letter variants
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ة": "ه"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Normalize punctuation
    text = text.replace("،", " ")
    text = text.replace("؛", " ")
    text = text.replace("؟", " ")
    text = text.replace("ـ", "")

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# HARD RULE ENGINE
# =========================================================

def detect_hard_rules(review):

    text = normalize_text(review)

    violations = []


    # =====================================================
    # 2.4 PRODUCT DAMAGE
    # =====================================================

    damage_patterns = [

        r"\bbroken\b",
        r"\bdamaged\b",
        r"\bcrushed\b",
        r"\bdestroyed\b",
        r"\bcracked\b",
        r"\bphysically damaged\b",

        "مكسور",
        "تالف",
        "خربان",
        "مهلك",
        "متهالك"
    ]

    if any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in damage_patterns
    ):

        violations.append({
            "rule_id": "2.4",
            "type": "PRODUCT_DAMAGE",
            "decision": "NOT_ALLOWED",
            **RULES["2.4"]
        })


    # =====================================================
    # 2.4 MISSING ITEM
    # =====================================================

    missing_patterns = [

        r"\bmissing\b",
        r"\bmissing item\b",
        r"\bmissing items\b",
        r"\bmissing part\b",
        r"\bmissing parts\b",
        r"\bmissing accessory\b",
        r"\bmissing accessories\b",

        "ناقص",
        "ناقصه",
        "جزء ناقص",
        "قطعه ناقصه",
        "قطعه ناقصه"
    ]

    if any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in missing_patterns
    ):

        violations.append({
            "rule_id": "2.4",
            "type": "MISSING_ITEM",
            "decision": "NOT_ALLOWED",
            **RULES["2.4"]
        })


    # =====================================================
    # 3.1 PRICE / COMPETITOR PRICING
    # =====================================================

    price_patterns = [

        # English
        r"\bcheaper elsewhere\b",
        r"\bcheaper somewhere else\b",
        r"\bcheaper on another website\b",
        r"\bcheaper on another store\b",
        r"\bcheaper from another seller\b",
        r"\bcheaper at another store\b",
        r"\bfound it cheaper\b",
        r"\bfound this cheaper\b",
        r"\bfound it cheaper elsewhere\b",
        r"\bfound this cheaper elsewhere\b",
        r"\blower price elsewhere\b",
        r"\blower price somewhere else\b",
        r"\bmore expensive here\b",
        r"\bcheaper than here\b",
        r"\bcheaper than noon\b",
        r"\bcheaper online\b",
        r"\bcheaper on amazon\b",
        r"\bcheaper on another marketplace\b",

        # Arabic
        "ارخص في مكان اخر",
        "ارخص في مكان آخر",
        "ارخص بمكان اخر",
        "ارخص بمكان آخر",
        "ارخص في محل اخر",
        "ارخص في محل آخر",
        "ارخص عند بائع اخر",
        "ارخص عند بائع آخر",
        "ارخص عند غيركم",
        "ارخص برا",

        "سعره ارخص",
        "سعرها ارخص",

        "وجدته ارخص",
        "وجدتها ارخص",
        "وجدته بسعر ارخص",
        "وجدتها بسعر ارخص",

        "لقيته ارخص",
        "لقيتها ارخص",
        "لقيته بسعر ارخص",
        "لقيتها بسعر ارخص",

        "سعر اقل في مكان اخر",
        "سعر اقل في مكان آخر",
        "سعر اقل في محل اخر",
        "سعر اقل في محل آخر"
    ]

    if any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in price_patterns
    ):

        violations.append({
            "rule_id": "3.1",
            "type": "COMPETITOR_PRICE",
            "decision": "NOT_ALLOWED",
            **RULES["3.1"]
        })


    # =====================================================
    # 3.2 AVAILABILITY
    # =====================================================

    availability_patterns = [

        r"\bout of stock\b",
        r"\bout-of-stock\b",
        r"\bnot available\b",
        r"\bunavailable\b",
        r"\bno stock\b",

        "غير متوفر",
        "غير متاح",
        "نفذ من المخزون",
        "خلص من المخزون",
        "نفد المخزون",
        "المخزون خلص",
        "غير موجود بالمخزون"
    ]

    if any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in availability_patterns
    ):

        violations.append({
            "rule_id": "3.2",
            "type": "AVAILABILITY",
            "decision": "NOT_ALLOWED",
            **RULES["3.2"]
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
                    "You are a strict and highly accurate product review "
                    "moderation classifier. Follow the supplied noon "
                    "guidelines exactly. Never invent rules."
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

    for model in models:

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
                    or "invalid model" in error_text
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
                    or "500" in error_text
                ):

                    time.sleep(2 ** attempt)

                    continue


                # -------------------------------------------------
                # OTHER ERRORS
                # -------------------------------------------------

                if attempt == 1:

                    break


    raise last_error


# =========================================================
# VALIDATE AI RESULT
# =========================================================

def validate_result(result):

    required_fields = [

        "decision",
        "rule_id",
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


    valid_rule_ids = {
        "NONE",
        "1.1",
        "1.2",
        "1.3",
        "1.4",
        "2.1",
        "2.2",
        "2.3",
        "2.4",
        "3.1",
        "3.2",
        "4.1",
        "4.2"
    }

    if result["rule_id"] not in valid_rule_ids:

        raise ValueError(
            "Invalid rule ID returned by AI."
        )


    # ---------------------------------------------------------
    # ALLOWED RESULT VALIDATION
    # ---------------------------------------------------------

    if result["decision"] == "ALLOWED":

        if result["rule_id"] != "NONE":

            raise ValueError(
                "Allowed result must use rule_id NONE."
            )


    # ---------------------------------------------------------
    # NOT ALLOWED RESULT VALIDATION
    # ---------------------------------------------------------

    if result["decision"] == "NOT_ALLOWED":

        if result["rule_id"] == "NONE":

            raise ValueError(
                "Not allowed result must have a valid rule ID."
            )

        rule = RULES[result["rule_id"]]

        if result["section_number"] != rule["section_number"]:

            raise ValueError(
                "Section number does not match rule ID."
            )

        if result["point_number"] != rule["point_number"]:

            raise ValueError(
                "Point number does not match rule ID."
            )


    if not result["comment"].strip():

        raise ValueError(
            "Empty comment returned by AI."
        )


    return True


# =========================================================
# LANGUAGE TEXT FOR HARD RULES
# =========================================================

def hard_rule_comment(rule_id):

    if lang_option == "English":

        comments = {

            "2.4":
                "The review describes product damage or a missing item, "
                "which is not allowed under the product review guidelines.",

            "3.1":
                "The review states or indicates that the product was found "
                "at a cheaper price, which is not allowed under the pricing "
                "and availability guidelines.",

            "3.2":
                "The review comments on stock status or product availability, "
                "which is not allowed under the pricing and availability guidelines."
        }

        return comments.get(
            rule_id,
            "The review violates the applicable product review guideline."
        )


    comments = {

        "2.4":
            "توضح المراجعة وجود تلف في المنتج أو وجود عنصر مفقود، "
            "وهو أمر غير مسموح به وفقًا لإرشادات مراجعات المنتجات.",

        "3.1":
            "توضح المراجعة أن المنتج تم العثور عليه بسعر أقل، "
            "وهو أمر غير مسموح به وفقًا لإرشادات السعر والتوفر.",

        "3.2":
            "تتعلق المراجعة بحالة المخزون أو توفر المنتج، "
            "وهو أمر غير مسموح به وفقًا لإرشادات السعر والتوفر."
    }

    return comments.get(
        rule_id,
        "تخالف المراجعة إرشادات مراجعات المنتجات المعمول بها."
    )


# =========================================================
# APPLY HARD RULES
# =========================================================

def apply_hard_rules(ai_result, hard_rules):

    if not hard_rules:

        return ai_result


    # =====================================================
    # PRIORITY
    # =====================================================
    #
    # If multiple confirmed violations exist, use the first
    # detected rule. The deterministic engine has already
    # identified a confirmed violation.
    #

    rule = hard_rules[0]

    rule_id = rule["rule_id"]

    ai_result["decision"] = "NOT_ALLOWED"

    ai_result["rule_id"] = rule_id

    ai_result["section_number"] = rule["section_number"]

    ai_result["section_title"] = rule["section_title"]

    ai_result["point_number"] = rule["point_number"]

    ai_result["point_text"] = rule["point_text"]

    ai_result["reason"] = hard_rule_comment(
        rule_id
    )

    ai_result["comment"] = hard_rule_comment(
        rule_id
    )

    return ai_result


# =========================================================
# VALIDATE HARD RULE AGAINST AI
# =========================================================

def enforce_rule_consistency(result):

    rule_id = result["rule_id"]

    if result["decision"] == "NOT_ALLOWED":

        if rule_id not in RULES:

            raise ValueError(
                "Invalid rule mapping."
            )

        rule = RULES[rule_id]

        result["section_number"] = rule["section_number"]
        result["section_title"] = rule["section_title"]
        result["point_number"] = rule["point_number"]
        result["point_text"] = rule["point_text"]

    else:

        result["rule_id"] = "NONE"
        result["section_number"] = 0
        result["section_title"] = "No violation"
        result["point_number"] = 0
        result["point_text"] = "No guideline violation identified"

    return result


# =========================================================
# FORMAT FINAL RESULT
# =========================================================

def format_result(result):

    decision = result["decision"]

    rule_id = result["rule_id"]

    section_number = result["section_number"]
    section_title = result["section_title"]

    point_number = result["point_number"]
    point_text = result["point_text"]

    comment = result["comment"].strip()


    # ---------------------------------------------------------
    # Remove accidental greetings
    # ---------------------------------------------------------

    comment = re.sub(
        r"^(dear seller[,:\s]*|hi[,:\s]*|hello[,:\s]*|dear[,:\s]*)",
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


    # =========================================================
    # ENGLISH
    # =========================================================

    if lang_option == "English":

        if decision == "ALLOWED":

            decision_text = (
                "✅ Allowed — it should not be removed"
            )

            section_text = (
                "No guideline violation identified"
            )

            point_text_display = (
                "No applicable violation"
            )

        else:

            decision_text = (
                "❌ Not allowed — the review should be removed"
            )

            section_text = (
                f"{section_number}. {section_title}"
            )

            point_text_display = (
                f"Point {point_number}: {point_text}"
            )


        return f"""
**Decision:** {decision_text}

**Rule ID:** {rule_id}

**Main Guideline Section:** {section_text}

**Specific Sub-rule:** {point_text_display}

**Comment:** {comment}
"""


    # =========================================================
    # ARABIC
    # =========================================================

    if decision == "ALLOWED":

        decision_text = (
            "✅ مسموح — لا ينبغي إزالته"
        )

        section_text = (
            "لا توجد مخالفة لإرشادات المراجعات"
        )

        point_text_display = (
            "لا توجد مخالفة تنطبق على المراجعة"
        )

    else:

        decision_text = (
            "❌ غير مسموح — ينبغي إزالة المراجعة"
        )


        section_translation = {

            1: "مخالفات إرشادات المجتمع",

            2: "ملاحظات البائع أو الطلب أو الشحن",

            3: "التعليقات المتعلقة بالسعر أو التوفر",

            4: "تعارض المصالح"
        }


        point_translation = {

            (1, 1):
                "المحتوى الترويجي أو الإعلاني",

            (1, 2):
                "اللغة المسيئة أو البذيئة أو غير اللائقة",

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
                "تعارض المصالح مع الأطراف ذات الصلة أو المنافسين",

            (4, 2):
                "نشر المراجعة مقابل تعويض أو حافز مالي"
        }


        section_text = (
            f"{section_number}. "
            f"{section_translation.get(section_number, section_title)}"
        )

        point_text_display = (
            f"النقطة {point_number}: "
            f"{point_translation.get((section_number, point_number), point_text)}"
        )


    return f"""
**القرار:** {decision_text}

**معرّف القاعدة:** {rule_id}

**القسم الرئيسي للإرشادات:** {section_text}

**القاعدة الفرعية:** {point_text_display}

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

                # =================================================
                # STEP 1
                # Deterministic Rule Engine
                # =================================================

                hard_rules = detect_hard_rules(
                    review_text
                )


                rule_engine_result = {
                    "confirmed_violations": hard_rules
                }


                # =================================================
                # STEP 2
                # AI Evaluation
                # =================================================

                prompt = build_prompt(
                    review_text,
                    rule_engine_result
                )


                ai_result, used_model = evaluate_with_reliability(
                    prompt
                )


                # =================================================
                # STEP 3
                # Validate AI Response
                # =================================================

                validate_result(
                    ai_result
                )


                # =================================================
                # STEP 4
                # Enforce Rule Consistency
                # =================================================

                ai_result = enforce_rule_consistency(
                    ai_result
                )


                # =================================================
                # STEP 5
                # Apply Deterministic Rules
                # =================================================

                final_result = apply_hard_rules(
                    ai_result,
                    hard_rules
                )


                # =================================================
                # STEP 6
                # Final Validation
                # =================================================

                validate_result(
                    final_result
                )


                # =================================================
                # STEP 7
                # Format
                # =================================================

                formatted_result = format_result(
                    final_result
                )


                # =================================================
                # STEP 8
                # Save
                # =================================================

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
