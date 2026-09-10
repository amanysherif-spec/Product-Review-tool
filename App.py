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
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}

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
# GROQ
# =========================================================

api_key = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=api_key) if api_key else None


# =========================================================
# MODELS
# =========================================================

PRIMARY_MODEL = "openai/gpt-oss-120b"
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
# CANONICAL RULE DATABASE
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
        "point_text": "Offensive, abusive, inappropriate, vulgar, or distasteful language"
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
        "section_title": "Conflicts of Interest & Anti-Manipulation",
        "point_number": 1,
        "point_text": "Written by seller, competitor, employee, friend, family member, or business partner"
    },

    "4.2": {
        "section_number": 4,
        "section_title": "Conflicts of Interest & Anti-Manipulation",
        "point_number": 2,
        "point_text": "Posted in exchange for compensation or financial incentive"
    }
}


VALID_RULE_IDS = list(RULES.keys())


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
            "enum": VALID_RULE_IDS
        },

        "section_number": {
            "type": "integer",
            "enum": [1, 2, 3, 4]
        },

        "section_title": {
            "type": "string"
        },

        "point_number": {
            "type": "integer",
            "enum": [1, 2, 3, 4]
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
# LANGUAGE
# =========================================================

def get_language_instruction():

    if lang_option == "English":

        return """
Return all textual fields in clear, professional English.

The decision MUST be exactly:

ALLOWED
or
NOT_ALLOWED.

Do not use Arabic.
"""

    return """
Return all textual fields in clear, professional Arabic.

The decision MUST be exactly:

ALLOWED
or
NOT_ALLOWED.

Do not use English explanations.
"""


# =========================================================
# NORMALIZE TEXT
# =========================================================

def normalize_text(text):

    if not text:
        return ""

    text = text.lower()

    # Remove Arabic diacritics
    text = re.sub(
        r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]",
        "",
        text
    )

    # Remove tatweel
    text = text.replace("ـ", "")

    # Arabic normalization
    text = text.replace("أ", "ا")
    text = text.replace("إ", "ا")
    text = text.replace("آ", "ا")
    text = text.replace("ى", "ي")
    text = text.replace("ة", "ه")

    # Normalize punctuation
    text = re.sub(
        r"[،,؛;:!?؟()\[\]{}\"'`]+",
        " ",
        text
    )

    # Normalize dashes
    text = re.sub(
        r"[-–—]+",
        " ",
        text
    )

    # Normalize spaces
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# HELPER
# =========================================================

def make_violation(
    violation_type,
    rule_id,
    matched_pattern=None
):

    return {
        "type": violation_type,
        "decision": "NOT_ALLOWED",
        "rule_id": rule_id,
        "matched_pattern": matched_pattern,
        **RULES[rule_id]
    }


# =========================================================
# HARD RULE ENGINE
# =========================================================

def detect_hard_rules(review):

    text = normalize_text(review)

    violations = []


    # =====================================================
    # 1. PRODUCT DAMAGE
    # =====================================================

    damage_patterns = [

        r"\bbroken\b",
        r"\bdamaged\b",
        r"\bcrushed\b",
        r"\bdestroyed\b",
        r"\bcracked\b",
        r"\bphysically damaged\b",

        r"\bmكسور\b",
        r"\bمكسور\b",
        r"\bمكسوره\b",
        r"\bتالف\b",
        r"\bتالفة\b",
        r"\bخربان\b",
        r"\bخربانه\b",
        r"\bمهلك\b",
        r"\bمهلكه\b",
        r"\bمتهالك\b",
        r"\bمتهالكه\b"
    ]

    for pattern in damage_patterns:

        if re.search(pattern, text, re.IGNORECASE):

            violations.append(
                make_violation(
                    "PRODUCT_DAMAGE",
                    "2.4",
                    pattern
                )
            )

            break


    # =====================================================
    # 2. MISSING ITEM / PART
    # =====================================================

    missing_patterns = [

        r"\bmissing\b",
        r"\bmissing item\b",
        r"\bmissing items\b",
        r"\bmissing part\b",
        r"\bmissing parts\b",
        r"\bmissing accessory\b",
        r"\bmissing accessories\b",
        r"\bmissing component\b",
        r"\bmissing components\b",

        r"\bناقص\b",
        r"\bناقصه\b",
        r"\bناقصه\b",
        r"\bجزء ناقص\b",
        r"\bقطع ناقصه\b",
        r"\bقطعه ناقصه\b",
        r"\bاكسسوار ناقص\b",
        r"\bملحق ناقص\b"
    ]

    for pattern in missing_patterns:

        if re.search(pattern, text, re.IGNORECASE):

            violations.append(
                make_violation(
                    "MISSING_ITEM",
                    "2.4",
                    pattern
                )
            )

            break


    # =====================================================
    # 3. PRICE COMPARISON
    # =====================================================

    price_patterns = [

        # English
        r"\bcheaper elsewhere\b",
        r"\bcheaper somewhere else\b",
        r"\bcheaper on another\b",
        r"\bcheaper at another\b",
        r"\bcheaper from another\b",
        r"\bcheaper on a different\b",
        r"\bfound it cheaper elsewhere\b",
        r"\bfound it cheaper somewhere else\b",
        r"\bfound the same product cheaper\b",
        r"\bfound the same item cheaper\b",
        r"\bfound this product cheaper\b",
        r"\bfound this item cheaper\b",
        r"\blower price elsewhere\b",
        r"\blower price somewhere else\b",
        r"\blower price at another\b",
        r"\blower price on another\b",
        r"\bmore expensive here than\b",
        r"\bcheaper than noon\b",
        r"\bcheaper at another store\b",
        r"\bcheaper on another website\b",
        r"\bcheaper on another site\b",
        r"\bsame product is cheaper\b",
        r"\bsame item is cheaper\b",

        # Arabic
        r"\barخص في مكان اخر\b",
        r"\barخص في مكان ثاني\b",
        r"\barخص في مكان تاني\b",
        r"\barخص برا\b",
        r"\bسعره ارخص في مكان اخر\b",
        r"\bسعره ارخص في مكان ثاني\b",
        r"\bسعره ارخص برا\b",
        r"\bلقيته ارخص\b",
        r"\bلقيته ارخص في مكان اخر\b",
        r"\bلقيته ارخص في مكان ثاني\b",
        r"\bلقيته ارخص برا\b",
        r"\bوجدته ارخص\b",
        r"\bوجدته ارخص في مكان اخر\b",
        r"\bوجدته ارخص في مكان ثاني\b",
        r"\bوجدته بسعر ارخص\b",
        r"\bوجدته بسعر ارخص في مكان اخر\b",
        r"\bوجدته بسعر ارخص في مكان ثاني\b",
        r"\bنفس المنتج ارخص\b",
        r"\bنفس المنتج ارخص في مكان اخر\b",
        r"\bنفس المنتج ارخص برا\b",
        r"\bسعر ارخص خارج\b"
    ]

    for pattern in price_patterns:

        if re.search(pattern, text, re.IGNORECASE):

            violations.append(
                make_violation(
                    "PRICE_COMPARISON",
                    "3.1",
                    pattern
                )
            )

            break


    # =====================================================
    # 4. AVAILABILITY
    # =====================================================

    availability_patterns = [

        # English
        r"\bout of stock\b",
        r"\bout-of-stock\b",
        r"\bunavailable\b",
        r"\bnot available\b",
        r"\bcurrently unavailable\b",
        r"\bno stock\b",
        r"\bno longer available\b",
        r"\bback in stock\b",
        r"\bwhen will it be available\b",

        # Arabic
        r"\bغير متوفر\b",
        r"\bغير متاح\b",
        r"\bنفذ من المخزون\b",
        r"\bخلص من المخزون\b",
        r"\bخلص المخزون\b",
        r"\bمش متوفر\b",
        r"\bمش متاح\b",
        r"\bمفيش مخزون\b",
        r"\bلا يوجد مخزون\b"
    ]

    for pattern in availability_patterns:

        if re.search(pattern, text, re.IGNORECASE):

            violations.append(
                make_violation(
                    "AVAILABILITY",
                    "3.2",
                    pattern
                )
            )

            break


    # =====================================================
    # 5. SHIPPING / DELIVERY / PACKAGING
    # =====================================================

    shipping_patterns = [

        # English
        r"\bshipping was late\b",
        r"\blate shipping\b",
        r"\bshipping delay\b",
        r"\bshipping delayed\b",
        r"\bdelivery was late\b",
        r"\blate delivery\b",
        r"\bdelivery delay\b",
        r"\bdelayed delivery\b",
        r"\bcourier was late\b",
        r"\bpackage arrived late\b",
        r"\bpoor packaging\b",
        r"\bbad packaging\b",
        r"\bpackaging was bad\b",
        r"\bpackage was badly packed\b",

        # Arabic
        r"\bالشحن اتاخر\b",
        r"\bالشحن تاخر\b",
        r"\bالتوصيل اتاخر\b",
        r"\bالتوصيل تاخر\b",
        r"\bالتوصيل متاخر\b",
        r"\bالشحن متاخر\b",
        r"\bتاخير الشحن\b",
        r"\bتاخير التوصيل\b",
        r"\bالتغليف سيئ\b",
        r"\bالتغليف وحش\b",
        r"\bالتغليف ضعيف\b"
    ]

    for pattern in shipping_patterns:

        if re.search(pattern, text, re.IGNORECASE):

            violations.append(
                make_violation(
                    "SHIPPING_DELIVERY",
                    "2.3",
                    pattern
                )
            )

            break


    # =====================================================
    # IMPORTANT:
    # We intentionally DO NOT classify words such as:
    #
    # battery
    # charging
    # quality
    # useful
    # effective
    # not good
    #
    # as violations.
    #
    # These normally describe the product itself.
    # =====================================================


    return violations


# =========================================================
# PRODUCT OPINION DETECTION
# =========================================================

def looks_like_product_opinion(review):

    text = normalize_text(review)

    product_patterns = [

        # English
        r"\bi dont like\b",
        r"\bi do not like\b",
        r"\bnot good\b",
        r"\bnot useful\b",
        r"\bnot effective\b",
        r"\bdoesnt work\b",
        r"\bdoes not work\b",
        r"\bnot working\b",
        r"\bpoor quality\b",
        r"\bbad quality\b",
        r"\blow quality\b",
        r"\bweak battery\b",
        r"\bbattery drains\b",
        r"\bbattery drain\b",
        r"\bbattery dies\b",
        r"\bdoesnt charge\b",
        r"\bdoes not charge\b",
        r"\bcharging is slow\b",
        r"\bnot worth it\b",
        r"\bnot worth the price\b",
        r"\bexpected better\b",
        r"\btoo small\b",
        r"\btoo large\b",
        r"\bcolor is not\b",
        r"\bcolour is not\b",
        r"\bthe product is bad\b",
        r"\bthe product is not good\b",

        # Arabic
        r"\bلم يعجبني المنتج\b",
        r"\bمش عاجبني المنتج\b",
        r"\bغير مجدي\b",
        r"\bمش مجدي\b",
        r"\bمش مفيد\b",
        r"\bغير مفيد\b",
        r"\bمش فعال\b",
        r"\bغير فعال\b",
        r"\bلا يعمل\b",
        r"\bمش بيشتغل\b",
        r"\bمش شغال\b",
        r"\bالجوده ضعيفه\b",
        r"\bجوده ضعيفه\b",
        r"\bالبطاريه ضعيفه\b",
        r"\bالبطاريه بتخلص بسرعه\b",
        r"\bالبطاريه تخلص بسرعه\b",
        r"\bالبطاريه تفضي بسرعه\b",
        r"\bالشحن بطيء\b",
        r"\bالشحن بطئ\b",
        r"\bمش بيشحن\b",
        r"\bلا يشحن\b",
        r"\bمش مستاهل\b",
        r"\bكنت متوقع افضل\b",
        r"\bالمنتج وحش\b",
        r"\bالمنتج مش كويس\b"
    ]

    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in product_patterns
    )


# =========================================================
# DEFAULT CLOSEST RULE
# =========================================================

def get_closest_rule(review):

    text = normalize_text(review)


    # Product opinion gets 2.4 as the closest
    # product-specific reference.
    #
    # IMPORTANT:
    # This DOES NOT mean that the review violates 2.4.
    #

    if looks_like_product_opinion(review):
        return "2.4"


    # Price/value
    if any(
        word in text
        for word in [
            "price",
            "expensive",
            "value",
            "سعر",
            "غالي",
            "قيمه"
        ]
    ):
        return "3.1"


    # Availability
    if any(
        word in text
        for word in [
            "stock",
            "available",
            "مخزون",
            "متوفر",
            "متاح"
        ]
    ):
        return "3.2"


    # Seller
    if any(
        word in text
        for word in [
            "seller",
            "seller service",
            "بائع",
            "البائع"
        ]
    ):
        return "2.1"


    # Order / return
    if any(
        word in text
        for word in [
            "order",
            "return",
            "refund",
            "cancel",
            "طلب",
            "ارجاع",
            "استرجاع",
            "الغاء"
        ]
    ):
        return "2.2"


    # Shipping
    if any(
        word in text
        for word in [
            "shipping",
            "delivery",
            "courier",
            "packaging",
            "شحن",
            "توصيل",
            "مندوب",
            "تغليف"
        ]
    ):
        return "2.3"


    # Default closest guideline
    return "2.4"


# =========================================================
# BUILD AI PROMPT
# =========================================================

def build_prompt(review, hard_rules):

    closest_rule = get_closest_rule(review)

    return f"""
You are an expert noon Product Review Moderation Officer.

Your job is to classify ONE customer review according to the
official noon Product Review Guidelines.

The most important requirement is HIGH PRECISION.

Do NOT classify a review as a violation merely because it is
negative, angry, disappointed, or critical.

A customer is allowed to express a negative opinion about the
PRODUCT ITSELF.

============================================================
OFFICIAL GUIDELINES
============================================================

{GUIDELINES}

============================================================
CUSTOMER REVIEW
============================================================

"{review}"

============================================================
DETERMINISTIC RULE ENGINE
============================================================

The application independently detected the following:

{json.dumps(hard_rules, ensure_ascii=False, indent=2)}

If the deterministic engine contains a confirmed violation,
you MUST return NOT_ALLOWED using that exact Rule ID.

============================================================
CRITICAL DISTINCTION
============================================================

PRODUCT FEEDBACK IS ALLOWED.

Examples:

"I don't like the product."
"I don't think it is useful."
"The quality is poor."
"The battery is weak."
"The battery drains quickly."
"It does not charge well."
"It doesn't work."
"The product is disappointing."
"I expected better."

These are opinions about the product itself.

They are NOT automatically:

- Community Guideline Violations
- Seller feedback
- Shipping feedback
- Ordering feedback

Do NOT classify ordinary product criticism under Section 1.

============================================================
VERY IMPORTANT BATTERY / CHARGING RULE
============================================================

Words such as:

battery
charging
charge
battery life
drains quickly
dies quickly
weak battery
slow charging

do NOT mean shipping or delivery.

For example:

"The battery drains within minutes."

→ ALLOWED

For example:

"The product does not hold a charge."

→ ALLOWED

Only classify shipping/delivery when the review is actually
about shipping, courier, delivery speed, or packaging.

============================================================
PRICE RULE
============================================================

These are NOT_ALLOWED under Rule 3.1:

"Found it cheaper elsewhere."
"Found this product cheaper somewhere else."
"It is cheaper on another website."
"I found a lower price elsewhere."
"The same product is cheaper at another store."
"وجدته بسعر ارخص."
"لقيته ارخص."
"نفس المنتج ارخص في مكان اخر."
"لقيته ارخص برا."

Rule:

3.1

Finding the product cheaper elsewhere or competitor pricing.

However, these are ALLOWED:

"The price is high."
"Too expensive."
"Not worth the price."
"Good value for money."
"Great quality for the price."

Do NOT confuse general price opinion with competitor price
comparison.

============================================================
DAMAGE RULE
============================================================

NOT_ALLOWED only when the customer says the physical product
was broken, damaged, cracked, crushed, destroyed, etc.

Rule:

2.4

============================================================
MISSING ITEM RULE
============================================================

NOT_ALLOWED when an item, component, accessory, or part is
actually missing.

Rule:

2.4

============================================================
SHIPPING RULE
============================================================

NOT_ALLOWED when the review discusses:

- shipping
- delivery
- courier
- delivery speed
- packaging

Rule:

2.3

Do NOT confuse product charging with shipping.

============================================================
AVAILABILITY RULE
============================================================

NOT_ALLOWED when the review discusses current:

- stock
- out of stock
- unavailable
- store-level availability

Rule:

3.2

A general wish such as:

"I hope it comes in more colors."

is ALLOWED.

============================================================
COMMUNITY GUIDELINES
============================================================

Section 1 should ONLY be used when there is an actual
Community Guideline violation.

1.1 = promotional/advertising content

1.2 = clearly offensive, abusive, vulgar, inappropriate,
or distasteful language

1.3 = hate speech/discrimination

1.4 = personal or sensitive information

IMPORTANT:

Negative sentiment is NOT offensive language.

"I hate this product."

can still be a product opinion.

Do not classify ordinary product dissatisfaction as 1.2.

============================================================
CONFLICT OF INTEREST
============================================================

Use Section 4 ONLY if there is actual evidence or a clear
statement of:

- seller involvement
- competitor involvement
- employee involvement
- friend/family involvement
- business partner involvement
- financial compensation
- financial incentive

Never assume a conflict.

============================================================
ALLOWED REVIEWS
============================================================

If the review does NOT violate any official rule:

decision MUST be:

ALLOWED

The Rule ID MUST still be selected.

The Rule ID is only the CLOSEST RELEVANT guideline reference.

It does NOT mean the review violates that rule.

NEVER return:

NONE
NO VIOLATION
N/A
No guideline
No applicable rule
0
empty rule

Valid Rule IDs ONLY:

1.1
1.2
1.3
1.4
2.1
2.2
2.3
2.4
3.1
3.2
4.1
4.2

============================================================
CLOSEST RULE FALLBACK
============================================================

The application suggests this closest Rule ID:

{closest_rule}

If the review is ALLOWED and no more relevant rule exists,
you may use this Rule ID.

Again:

ALLOWED + Rule ID does NOT mean the Rule was violated.

The reason MUST explicitly say that the review is allowed
because it concerns the product itself and does not violate
the selected guideline.

============================================================
RULE MAPPING
============================================================

1.1 → Section 1 Point 1
1.2 → Section 1 Point 2
1.3 → Section 1 Point 3
1.4 → Section 1 Point 4

2.1 → Section 2 Point 1
2.2 → Section 2 Point 2
2.3 → Section 2 Point 3
2.4 → Section 2 Point 4

3.1 → Section 3 Point 1
3.2 → Section 3 Point 2

4.1 → Section 4 Point 1
4.2 → Section 4 Point 2

The Rule ID is the source of truth.

============================================================
REASON
============================================================

The reason must explain WHY the decision was made.

For ALLOWED product opinions, explicitly explain that the
review focuses on the product itself and does not violate
the selected guideline.

For NOT_ALLOWED reviews, identify the actual prohibited
content.

============================================================
COMMENT
============================================================

The comment must:

- be professional
- be concise
- be specific
- directly explain the decision
- contain no greeting
- contain no salutation

Do not start with:

Dear Seller
Hi
Hello
Dear
عزيزي البائع
مرحباً

============================================================
LANGUAGE
============================================================

{get_language_instruction()}
"""


# =========================================================
# CALL GROQ
# =========================================================

def call_model(model, prompt):

    if not client:
        raise RuntimeError(
            "Groq client is not configured."
        )

    response = client.chat.completions.create(

        model=model,

        messages=[
            {
                "role": "system",
                "content": (
                    "You are a high-precision noon product review "
                    "moderation classifier. "
                    "Follow the official rules exactly. "
                    "Do not invent violations. "
                    "Product dissatisfaction is not automatically "
                    "a guideline violation. "
                    "Every result must contain a valid Rule ID."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0,

        max_tokens=1200,

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

    if not content:
        raise ValueError(
            "Empty response received from the model."
        )

    return json.loads(content)


# =========================================================
# RELIABLE MODEL EVALUATION
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

                # Model unavailable
                if (
                    "decommissioned" in error_text
                    or "model_not_found" in error_text
                    or "model not found" in error_text
                    or "does not exist" in error_text
                ):
                    break

                # Temporary / rate limit
                temporary_error = (
                    "429" in error_text
                    or "rate limit" in error_text
                    or "timeout" in error_text
                    or "temporarily unavailable" in error_text
                    or "503" in error_text
                    or "502" in error_text
                    or "500" in error_text
                )

                if temporary_error:

                    if attempt < 1:

                        time.sleep(
                            2 ** attempt
                        )

                        continue

                    break

                if attempt == 1:
                    break

    if last_error:
        raise last_error

    raise RuntimeError(
        "Unable to evaluate the review."
    )


# =========================================================
# VALIDATE RESULT
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

    if result["rule_id"] not in RULES:
        raise ValueError(
            "Invalid Rule ID returned by AI."
        )

    rule = RULES[
        result["rule_id"]
    ]

    if (
        result["section_number"]
        != rule["section_number"]
    ):
        raise ValueError(
            "Section number does not match Rule ID."
        )

    if (
        result["point_number"]
        != rule["point_number"]
    ):
        raise ValueError(
            "Point number does not match Rule ID."
        )

    if not str(result["reason"]).strip():
        raise ValueError(
            "Empty reason returned by AI."
        )

    if not str(result["comment"]).strip():
        raise ValueError(
            "Empty comment returned by AI."
        )

    return True


# =========================================================
# ENFORCE CANONICAL RULE
# =========================================================

def enforce_rule_consistency(result):

    rule_id = result["rule_id"]

    if rule_id not in RULES:
        raise ValueError(
            "Invalid Rule ID."
        )

    rule = RULES[rule_id]

    result["section_number"] = rule["section_number"]
    result["section_title"] = rule["section_title"]
    result["point_number"] = rule["point_number"]
    result["point_text"] = rule["point_text"]

    return result


# =========================================================
# HARD RULE COMMENT GENERATOR
# =========================================================

def hard_rule_text(rule_id):

    if lang_option == "English":

        messages = {

            "2.4":
                (
                    "The review reports product damage or a "
                    "missing item/component, which is not allowed "
                    "under Section 2, Point 4."
                ),

            "3.1":
                (
                    "The review compares the product price with "
                    "a cheaper price elsewhere or another seller, "
                    "store, website, or competitor. This is not "
                    "allowed under Section 3, Point 1."
                ),

            "3.2":
                (
                    "The review refers to product availability, "
                    "stock status, or the product being unavailable. "
                    "This is not allowed under Section 3, Point 2."
                ),

            "2.3":
                (
                    "The review discusses shipping, delivery, "
                    "delivery speed, courier service, or packaging. "
                    "This is not allowed under Section 2, Point 3."
                )
        }

        return messages.get(
            rule_id,
            "The review contains content that violates the selected noon guideline."
        )


    messages = {

        "2.4":
            (
                "تشير المراجعة إلى تلف المنتج أو وجود عنصر أو "
                "جزء مفقود، وهو أمر غير مسموح به وفقًا للقسم 2، "
                "النقطة 4."
            ),

        "3.1":
            (
                "تقارن المراجعة سعر المنتج بسعر أقل في مكان آخر "
                "أو بسعر بائع أو متجر أو موقع أو منافس آخر، "
                "وهو أمر غير مسموح به وفقًا للقسم 3، النقطة 1."
            ),

        "3.2":
            (
                "تتعلق المراجعة بتوفر المنتج أو حالة المخزون أو "
                "عدم توفر المنتج، وهو أمر غير مسموح به وفقًا "
                "للقسم 3، النقطة 2."
            ),

        "2.3":
            (
                "تتعلق المراجعة بالشحن أو التوصيل أو سرعة التوصيل "
                "أو شركة التوصيل أو التغليف، وهو أمر غير مسموح به "
                "وفقًا للقسم 2، النقطة 3."
            )
    }

    return messages.get(
        rule_id,
        "تتضمن المراجعة محتوى يخالف إرشادات نون المحددة."
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

    priority = {

        "1.3": 100,
        "1.2": 90,
        "1.4": 80,
        "1.1": 70,

        "4.2": 60,
        "4.1": 50,

        "3.1": 40,
        "3.2": 35,

        "2.1": 30,
        "2.2": 25,
        "2.3": 20,
        "2.4": 10
    }


    selected = max(
        hard_rules,
        key=lambda x: priority.get(
            x["rule_id"],
            0
        )
    )


    rule_id = selected["rule_id"]
    rule = RULES[rule_id]


    ai_result["decision"] = "NOT_ALLOWED"

    ai_result["rule_id"] = rule_id

    ai_result["section_number"] = (
        rule["section_number"]
    )

    ai_result["section_title"] = (
        rule["section_title"]
    )

    ai_result["point_number"] = (
        rule["point_number"]
    )

    ai_result["point_text"] = (
        rule["point_text"]
    )


    # =====================================================
    # IMPORTANT:
    # Replace BOTH reason and comment.
    # This prevents contradictory AI output.
    # =====================================================

    final_text = hard_rule_text(
        rule_id
    )

    ai_result["reason"] = final_text
    ai_result["comment"] = final_text


    return ai_result


# =========================================================
# PRODUCT OPINION SAFETY
# =========================================================

def protect_product_opinion(
    result,
    review,
    hard_rules
):

    # If a confirmed hard violation exists,
    # never override it.
    if hard_rules:
        return result


    # If it clearly looks like product feedback,
    # prevent the model from turning it into
    # Community Guideline violation.
    if looks_like_product_opinion(review):

        result["decision"] = "ALLOWED"

        # Use closest valid rule.
        result["rule_id"] = get_closest_rule(
            review
        )

        rule = RULES[
            result["rule_id"]
        ]

        result["section_number"] = (
            rule["section_number"]
        )

        result["section_title"] = (
            rule["section_title"]
        )

        result["point_number"] = (
            rule["point_number"]
        )

        result["point_text"] = (
            rule["point_text"]
        )


        if lang_option == "English":

            result["reason"] = (
                "The review expresses an opinion about the "
                "product itself, such as its quality, usefulness, "
                "performance, battery, or charging. It does not "
                "contain a confirmed violation of the selected "
                "guideline, so the review is allowed."
            )

            result["comment"] = (
                "This is product-focused feedback and does not "
                "violate the noon Product Review Guidelines. "
                "The selected guideline is shown only as the "
                "closest relevant category."
            )

        else:

            result["reason"] = (
                "تعبر المراجعة عن رأي يتعلق بالمنتج نفسه، مثل "
                "الجودة أو الفائدة أو الأداء أو البطارية أو الشحن، "
                "ولا تتضمن مخالفة مؤكدة للإرشاد المحدد، ولذلك "
                "فالمراجعة مسموحة."
            )

            result["comment"] = (
                "تتعلق هذه المراجعة بالمنتج نفسه ولا تخالف "
                "إرشادات نون لمراجعات المنتجات. تم اختيار "
                "الإرشاد المعروض فقط باعتباره الأقرب من حيث التصنيف."
            )


    return result


# =========================================================
# FINAL SAFETY CHECK
# =========================================================

def final_safety_check(result):

    if result.get("decision") not in [
        "ALLOWED",
        "NOT_ALLOWED"
    ]:
        raise ValueError(
            "Invalid final decision."
        )


    rule_id = result.get(
        "rule_id"
    )

    if rule_id not in RULES:

        raise ValueError(
            "Final result has no valid Rule ID."
        )


    # Always synchronize from canonical database.
    rule = RULES[rule_id]

    result["section_number"] = (
        rule["section_number"]
    )

    result["section_title"] = (
        rule["section_title"]
    )

    result["point_number"] = (
        rule["point_number"]
    )

    result["point_text"] = (
        rule["point_text"]
    )


    # No empty reason/comment
    if not str(
        result.get("reason", "")
    ).strip():

        raise ValueError(
            "Final reason is empty."
        )


    if not str(
        result.get("comment", "")
    ).strip():

        raise ValueError(
            "Final comment is empty."
        )


    return result


# =========================================================
# CLEAN COMMENT
# =========================================================

def clean_comment(comment):

    comment = str(
        comment
    ).strip()


    comment = re.sub(
        r"^(dear seller[,:\s]*|hi[,:\s]*|hello[,:\s]*|dear[,:\s]*)",
        "",
        comment,
        flags=re.IGNORECASE
    )


    comment = re.sub(
        r"^(عزيزي البائع[,:\s]*|عزيزي[,:\s]*|مرحبا[,:\s]*|مرحباً[,:\s]*)",
        "",
        comment,
        flags=re.IGNORECASE
    )


    return comment.strip()


# =========================================================
# FORMAT RESULT
# =========================================================

def format_result(result):

    decision = result["decision"]

    rule_id = result["rule_id"]

    section_number = result["section_number"]

    section_title = result["section_title"]

    point_number = result["point_number"]

    point_text = result["point_text"]

    reason = clean_comment(
        result["reason"]
    )

    comment = clean_comment(
        result["comment"]
    )


    # =====================================================
    # ENGLISH
    # =====================================================

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

**Rule ID:** {rule_id}

**Main Guideline Section:** {section_number}. {section_title}

**Specific Sub-rule:** Point {point_number}: {point_text}

**Reason:** {reason}

**Comment:** {comment}
"""


    # =====================================================
    # ARABIC
    # =====================================================

    section_translation = {

        1:
            "مخالفات إرشادات المجتمع",

        2:
            "ملاحظات البائع أو الطلب أو الشحن",

        3:
            "التعليقات المتعلقة بالسعر أو التوفر",

        4:
            "تعارض المصالح والتلاعب"
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
            "كتابة المراجعة من البائع أو المنافس أو الموظف أو شخص ذي صلة",

        (4, 2):
            "نشر المراجعة مقابل تعويض أو حافز مالي"
    }


    translated_section = section_translation[
        section_number
    ]

    translated_point = point_translation[
        (
            section_number,
            point_number
        )
    ]


    if decision == "ALLOWED":

        decision_text = (
            "✅ مسموح — لا ينبغي إزالته"
        )

    else:

        decision_text = (
            "❌ غير مسموح — ينبغي إزالة المراجعة"
        )


    return f"""
**القرار:** {decision_text}

**معرّف القاعدة:** {rule_id}

**القسم الرئيسي للإرشادات:** {section_number}. {translated_section}

**القاعدة الفرعية:** النقطة {point_number}: {translated_point}

**السبب:** {reason}

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

                # =========================================
                # STEP 1
                # Hard rules
                # =========================================

                hard_rules = detect_hard_rules(
                    review_text
                )


                # =========================================
                # STEP 2
                # AI
                # =========================================

                prompt = build_prompt(
                    review_text,
                    hard_rules
                )


                ai_result, used_model = (
                    evaluate_with_reliability(
                        prompt
                    )
                )


                # =========================================
                # STEP 3
                # Validate
                # =========================================

                validate_result(
                    ai_result
                )


                # =========================================
                # STEP 4
                # Canonical Rule
                # =========================================

                ai_result = enforce_rule_consistency(
                    ai_result
                )


                # =========================================
                # STEP 5
                # Hard Rules Override
                # =========================================

                ai_result = apply_hard_rules(
                    ai_result,
                    hard_rules
                )


                # =========================================
                # STEP 6
                # Product Opinion Protection
                # =========================================

                ai_result = protect_product_opinion(
                    ai_result,
                    review_text,
                    hard_rules
                )


                # =========================================
                # STEP 7
                # Final Rule Sync
                # =========================================

                ai_result = enforce_rule_consistency(
                    ai_result
                )


                # =========================================
                # STEP 8
                # Final Safety
                # =========================================

                final_result = final_safety_check(
                    ai_result
                )


                # =========================================
                # STEP 9
                # Format
                # =========================================

                formatted_result = format_result(
                    final_result
                )


                # =========================================
                # STEP 10
                # Save
                # =========================================

                st.session_state.result = (
                    formatted_result
                )

                st.session_state.comment_text = (
                    extract_comment(
                        formatted_result
                    )
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

    st.markdown(
        "### Result:"
    )

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

                alert(
                    "Comment copied to clipboard!"
                );

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
    # GUIDELINES
    # =====================================================

    st.markdown("---")

    st.markdown(
        "**Guidelines Reference:**"
    )

    st.markdown(
        "https://help.noon.com/portal/en/kb/articles/product-review-guidelines"
    )
