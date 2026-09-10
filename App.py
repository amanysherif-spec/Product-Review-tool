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


# =========================================================
# MODELS
# =========================================================

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
#
# IMPORTANT:
# Every result MUST use one of these rules.
# There is NO "NONE" or "NO VIOLATION" rule.
#
# For ALLOWED reviews, the system selects the closest
# relevant existing guideline rule.
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
RULE ENGINE INFORMATION
============================================================

The application has independently checked the review.

Rule engine result:

{json.dumps(rule_engine_result, ensure_ascii=False)}

IMPORTANT:

If the rule engine identifies a confirmed violation,
you MUST classify the review as NOT_ALLOWED.

You MUST NOT override a confirmed rule-engine violation.

If the rule engine identifies no confirmed violation,
perform a complete contextual evaluation yourself.

============================================================
CRITICAL RULE FOR PRICE COMMENTS
============================================================

Section 3 - Point 1 applies when the review says or clearly means:

"Found it cheaper elsewhere"

"Found this product cheaper somewhere else"

"It is cheaper on another website"

"I found a lower price elsewhere"

"The same product is cheaper at another store"

or any equivalent statement comparing the product price
with another store, website, seller, marketplace, or competitor.

These reviews are:

NOT_ALLOWED

Section 3
Point 1

Finding the product cheaper elsewhere or competitor pricing

IMPORTANT:

A normal opinion about price is NOT automatically a violation.

Examples:

"The price is high."
→ ALLOWED

"Too expensive."
→ ALLOWED

"I think it is overpriced."
→ ALLOWED

"Not worth the price."
→ ALLOWED

"Great quality for the price."
→ ALLOWED

Only classify under Section 3 Point 1 as NOT_ALLOWED when the
customer is actually comparing the price with another place,
seller, website, store, or competitor, or clearly says they
found it cheaper elsewhere.

============================================================
IMPORTANT CLASSIFICATION RULES
============================================================

1. PRODUCT OPINIONS

Normal opinions about the product itself are ALLOWED unless they
violate one of the official guidelines.

Examples:

"I don't like it."
"The product is not good."
"It doesn't work."
"The battery is weak."
"The quality is poor."
"I expected better."
"The color is not nice."

Do NOT classify a normal product complaint as seller feedback.

Do NOT invent a violation.

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
- متهالك

classify it as:

NOT_ALLOWED

Rule ID: 2.4

------------------------------------------------------------

3. MISSING ITEM

If the customer clearly says that an item, component,
accessory, or part was missing from the order, classify it as:

NOT_ALLOWED

Rule ID: 2.4

------------------------------------------------------------

4. SELLER FEEDBACK

If the review specifically discusses:

- seller behavior
- seller performance
- seller reputation
- seller service

classify it as:

NOT_ALLOWED

Rule ID: 2.1

------------------------------------------------------------

5. ORDER / RETURN EXPERIENCE

If the review specifically discusses:

- placing an order
- cancelling an order
- returning an order
- refund/order experience

classify it as:

NOT_ALLOWED

Rule ID: 2.2

------------------------------------------------------------

6. SHIPPING / DELIVERY / PACKAGING

If the review specifically complains about:

- shipping
- delivery
- delivery speed
- packaging
- courier/delivery experience

classify it as:

NOT_ALLOWED

Rule ID: 2.3

------------------------------------------------------------

7. PRICE

Use Rule ID 3.1 when:

- the customer found the same product cheaper elsewhere
- the customer compares the price with another seller
- the customer compares the price with another store
- the customer compares the price with another website
- the customer mentions a competitor's lower price

This is NOT_ALLOWED.

However, general product value opinions are ALLOWED.

Examples:

"Good value for money."
→ ALLOWED

"Expensive."
→ ALLOWED

"Too expensive for the quality."
→ ALLOWED

"Found the same item cheaper elsewhere."
→ NOT_ALLOWED

------------------------------------------------------------

8. AVAILABILITY

If the review is about:

- out of stock
- unavailable
- store availability
- product availability
- stock status

classify it as:

NOT_ALLOWED

Rule ID: 3.2

However:

"I hope it comes in more colors."

is ALLOWED because it expresses a general wish and does not
state the current stock status.

------------------------------------------------------------

9. PROMOTIONAL CONTENT

If the review contains advertising, promotional or marketing
content, classify it as:

NOT_ALLOWED

Rule ID: 1.1

------------------------------------------------------------

10. OFFENSIVE LANGUAGE

If the review contains clearly vulgar, abusive, offensive,
inappropriate, or distasteful language, classify it as:

NOT_ALLOWED

Rule ID: 1.2

Do not mark ordinary negative opinions as offensive.

------------------------------------------------------------

11. HATE SPEECH

If the review contains hate speech or discriminatory remarks,
classify it as:

NOT_ALLOWED

Rule ID: 1.3

------------------------------------------------------------

12. PERSONAL INFORMATION

If the review exposes personal or sensitive information,
classify it as:

NOT_ALLOWED

Rule ID: 1.4

------------------------------------------------------------

13. CONFLICT OF INTEREST

Classify under Section 4 only when there is actual evidence
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

Use:

4.1 = relationship/conflict of interest

4.2 = compensation or financial incentive

------------------------------------------------------------

14. ALLOWED REVIEWS

If the review does not violate any official guideline:

decision = ALLOWED

IMPORTANT:

You MUST STILL select the MOST RELEVANT EXISTING guideline
Section and Point.

NEVER use:

- NONE
- NO VIOLATION
- No guideline violation
- No applicable violation
- N/A
- 0
- empty section
- empty point

Every result MUST contain one of the valid Rule IDs:

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

The selected Section and Point do NOT mean that the review
violates that rule when the decision is ALLOWED.

They only represent the closest relevant guideline category.

The reason and comment MUST clearly explain that the review
is ALLOWED and does not violate the selected guideline.

------------------------------------------------------------

15. RULE CONSISTENCY

The Rule ID determines the correct Section and Point.

The following mappings are mandatory:

1.1 → Section 1, Point 1
1.2 → Section 1, Point 2
1.3 → Section 1, Point 3
1.4 → Section 1, Point 4

2.1 → Section 2, Point 1
2.2 → Section 2, Point 2
2.3 → Section 2, Point 3
2.4 → Section 2, Point 4

3.1 → Section 3, Point 1
3.2 → Section 3, Point 2

4.1 → Section 4, Point 1
4.2 → Section 4, Point 2

Do not create a different mapping.

------------------------------------------------------------

16. DO NOT INVENT RULES

You MUST NOT create a new guideline.

You MUST select the Section and Point from the official
noon guidelines only.

------------------------------------------------------------

17. COMMENT

The comment must:

- directly explain the decision
- be professional
- be concise
- be specific to the review
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
# NORMALIZE TEXT
# =========================================================

def normalize_text(text):

    text = text.lower().strip()

    # Normalize Arabic characters
    text = text.replace("أ", "ا")
    text = text.replace("إ", "ا")
    text = text.replace("آ", "ا")
    text = text.replace("ى", "ي")
    text = text.replace("ة", "ه")

    # Normalize punctuation
    text = re.sub(r"[،,؛;]", " ", text)

    # Normalize spaces
    text = re.sub(r"\s+", " ", text)

    return text


# =========================================================
# HARD RULE ENGINE
# =========================================================

def detect_hard_rules(review):

    text = normalize_text(review)

    violations = []


    # =====================================================
    # PRODUCT DAMAGE
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
            "rule_id": "2.4",
            **RULES["2.4"]
        })


    # =====================================================
    # MISSING ITEM
    # =====================================================

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
            "rule_id": "2.4",
            **RULES["2.4"]
        })


    # =====================================================
    # PRICE / COMPETITOR
    # =====================================================
    #
    # IMPORTANT:
    # Only clear price comparisons are hard violations.
    # General "expensive" comments remain ALLOWED.
    # =====================================================

    price_patterns = [

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

        r"\blower price elsewhere\b",
        r"\blower price somewhere else\b",
        r"\blower price at another\b",
        r"\blower price on another\b",

        r"\bmore expensive here than\b",
        r"\bmore expensive than\b",
        r"\bcheaper than noon\b",

        r"\bارخص في مكان اخر\b",
        r"\bارخص في مكان اخر\b",
        r"\bارخص برا\b",
        r"\bسعره ارخص في مكان اخر\b",
        r"\bلقيته ارخص في مكان اخر\b",
        r"\bلقيته ارخص برا\b",
        r"\bنفس المنتج ارخص\b"
    ]

    if any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in price_patterns
    ):

        violations.append({
            "type": "PRICE_COMPARISON",
            "decision": "NOT_ALLOWED",
            "rule_id": "3.1",
            **RULES["3.1"]
        })


    # =====================================================
    # AVAILABILITY
    # =====================================================

    availability_patterns = [

        r"\bout of stock\b",
        r"\bout-of-stock\b",
        r"\bunavailable\b",
        r"\bnot available\b",
        r"\bcurrently unavailable\b",
        r"\bno stock\b",
        r"\bno longer available\b",

        r"\bغير متوفر\b",
        r"\bغير متاح\b",
        r"\bنفذ من المخزون\b",
        r"\bخلص من المخزون\b"
    ]

    if any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in availability_patterns
    ):

        violations.append({
            "type": "AVAILABILITY",
            "decision": "NOT_ALLOWED",
            "rule_id": "3.2",
            **RULES["3.2"]
        })


    return violations


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
                    "You are a strict and highly accurate product "
                    "review moderation classifier. "
                    "Follow the supplied noon guidelines exactly. "
                    "Never invent rules. "
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
# RETRY + FALLBACK SYSTEM
# =========================================================

def evaluate_with_reliability(prompt):

    models = [
        PRIMARY_MODEL,
        FALLBACK_MODEL
    ]

    last_error = None


    for model in models:

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


                # =================================================
                # MODEL DECOMMISSIONED / NOT FOUND
                # =================================================

                if (
                    "decommissioned" in error_text
                    or "model_not_found" in error_text
                    or "model not found" in error_text
                    or "does not exist" in error_text
                ):

                    break


                # =================================================
                # RATE LIMIT / TEMPORARY ERROR
                # =================================================

                if (
                    "429" in error_text
                    or "rate limit" in error_text
                    or "timeout" in error_text
                    or "temporarily unavailable" in error_text
                    or "503" in error_text
                    or "502" in error_text
                    or "500" in error_text
                ):

                    if attempt < 1:

                        time.sleep(
                            2 ** attempt
                        )

                        continue

                    break


                # =================================================
                # OTHER ERROR
                # =================================================

                if attempt == 1:

                    break


    if last_error:

        raise last_error

    raise RuntimeError(
        "Unable to evaluate the review."
    )


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


    # ---------------------------------------------------------
    # REQUIRED FIELDS
    # ---------------------------------------------------------

    for field in required_fields:

        if field not in result:

            raise ValueError(
                f"Missing field from AI response: {field}"
            )


    # ---------------------------------------------------------
    # DECISION
    # ---------------------------------------------------------

    if result["decision"] not in [
        "ALLOWED",
        "NOT_ALLOWED"
    ]:

        raise ValueError(
            "Invalid decision returned by AI."
        )


    # ---------------------------------------------------------
    # RULE ID
    # ---------------------------------------------------------

    if result["rule_id"] not in RULES:

        raise ValueError(
            "Every result must contain a valid guideline Rule ID."
        )


    # ---------------------------------------------------------
    # RULE CONSISTENCY
    # ---------------------------------------------------------

    expected_rule = RULES[
        result["rule_id"]
    ]


    if (
        result["section_number"]
        != expected_rule["section_number"]
    ):

        raise ValueError(
            "Section number does not match the Rule ID."
        )


    if (
        result["point_number"]
        != expected_rule["point_number"]
    ):

        raise ValueError(
            "Point number does not match the Rule ID."
        )


    # ---------------------------------------------------------
    # COMMENT
    # ---------------------------------------------------------

    if not result["comment"].strip():

        raise ValueError(
            "Empty comment returned by AI."
        )


    # ---------------------------------------------------------
    # REASON
    # ---------------------------------------------------------

    if not result["reason"].strip():

        raise ValueError(
            "Empty reason returned by AI."
        )


    return True


# =========================================================
# ENFORCE RULE CONSISTENCY
# =========================================================

def enforce_rule_consistency(result):

    rule_id = result["rule_id"]

    if rule_id not in RULES:

        raise ValueError(
            "The result must contain a valid guideline Rule ID."
        )

    rule = RULES[rule_id]


    # The canonical RULES database is the source of truth.
    # The AI cannot change the Section/Point text.

    result["section_number"] = rule[
        "section_number"
    ]

    result["section_title"] = rule[
        "section_title"
    ]

    result["point_number"] = rule[
        "point_number"
    ]

    result["point_text"] = rule[
        "point_text"
    ]


    return result


# =========================================================
# APPLY HARD RULES
# =========================================================

def apply_hard_rules(ai_result, hard_rules):

    if not hard_rules:

        return ai_result


    # ---------------------------------------------------------
    # Confirmed deterministic violation
    # ---------------------------------------------------------

    rule = hard_rules[0]

    rule_id = rule["rule_id"]

    ai_result["decision"] = "NOT_ALLOWED"

    ai_result["rule_id"] = rule_id

    ai_result["section_number"] = rule[
        "section_number"
    ]

    ai_result["section_title"] = rule[
        "section_title"
    ]

    ai_result["point_number"] = rule[
        "point_number"
    ]

    ai_result["point_text"] = rule[
        "point_text"
    ]


    # ---------------------------------------------------------
    # Make sure the comment reflects the hard rule
    # ---------------------------------------------------------

    if rule_id == "3.1":

        if lang_option == "English":

            ai_result["comment"] = (
                "The review states that the product was found "
                "cheaper elsewhere or compares its price with "
                "another seller, store, website, or competitor. "
                "This is not allowed under Section 3, Point 1."
            )

        else:

            ai_result["comment"] = (
                "توضح المراجعة أن المنتج تم العثور عليه بسعر "
                "أقل في مكان آخر أو تقارن سعره بسعر بائع أو متجر "
                "أو موقع أو منافس آخر، ولذلك فهي غير مسموحة وفقًا "
                "للقسم 3، النقطة 1."
            )


    elif rule_id == "3.2":

        if lang_option == "English":

            ai_result["comment"] = (
                "The review comments on product or store "
                "availability or stock status, which is not "
                "allowed under Section 3, Point 2."
            )

        else:

            ai_result["comment"] = (
                "تتعلق المراجعة بتوفر المنتج أو حالة المخزون، "
                "وهو أمر غير مسموح به وفقًا للقسم 3، النقطة 2."
            )


    elif rule_id == "2.4":

        if lang_option == "English":

            ai_result["comment"] = (
                "The review reports product damage or a missing "
                "item/component, which is not allowed under "
                "Section 2, Point 4."
            )

        else:

            ai_result["comment"] = (
                "تشير المراجعة إلى تلف المنتج أو وجود عنصر أو "
                "جزء مفقود، وهو أمر غير مسموح به وفقًا للقسم 2، "
                "النقطة 4."
            )


    return ai_result


# =========================================================
# FINAL SAFETY CHECK
# =========================================================

def final_safety_check(result):

    # ---------------------------------------------------------
    # NEVER allow fake / empty guideline values
    # ---------------------------------------------------------

    forbidden_values = [

        "none",
        "no violation",
        "no guideline violation",
        "no applicable violation",
        "n/a",
        "not applicable",
        ""

    ]


    section_title = str(
        result.get("section_title", "")
    ).strip().lower()

    point_text = str(
        result.get("point_text", "")
    ).strip().lower()


    if section_title in forbidden_values:

        raise ValueError(
            "Invalid guideline section returned."
        )


    if point_text in forbidden_values:

        raise ValueError(
            "Invalid guideline point returned."
        )


    # ---------------------------------------------------------
    # Rule ID must always exist
    # ---------------------------------------------------------

    if result.get("rule_id") not in RULES:

        raise ValueError(
            "Invalid or missing Rule ID."
        )


    # ---------------------------------------------------------
    # Force canonical rule values one final time
    # ---------------------------------------------------------

    rule = RULES[
        result["rule_id"]
    ]


    result["section_number"] = rule[
        "section_number"
    ]

    result["section_title"] = rule[
        "section_title"
    ]

    result["point_number"] = rule[
        "point_number"
    ]

    result["point_text"] = rule[
        "point_text"
    ]


    return result


# =========================================================
# REMOVE GREETINGS
# =========================================================

def clean_comment(comment):

    comment = comment.strip()


    # English greetings

    comment = re.sub(
        r"^(dear seller[,:\s]*|hi[,:\s]*|hello[,:\s]*|dear[,:\s]*)",
        "",
        comment,
        flags=re.IGNORECASE
    )


    # Arabic greetings

    comment = re.sub(
        r"^(عزيزي البائع[,:\s]*|عزيزي[,:\s]*|مرحبا[,:\s]*|مرحباً[,:\s]*)",
        "",
        comment,
        flags=re.IGNORECASE
    )


    return comment.strip()


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

                # =============================================
                # STEP 1
                # Deterministic rule engine
                # =============================================

                hard_rules = detect_hard_rules(
                    review_text
                )


                rule_engine_result = {

                    "confirmed_violations":
                        hard_rules

                }


                # =============================================
                # STEP 2
                # AI evaluation
                # =============================================

                prompt = build_prompt(
                    review_text,
                    rule_engine_result
                )


                ai_result, used_model = (
                    evaluate_with_reliability(
                        prompt
                    )
                )


                # =============================================
                # STEP 3
                # Validate AI result
                # =============================================

                validate_result(
                    ai_result
                )


                # =============================================
                # STEP 4
                # Enforce canonical Rule mapping
                # =============================================

                ai_result = enforce_rule_consistency(
                    ai_result
                )


                # =============================================
                # STEP 5
                # Apply confirmed hard rules
                # =============================================

                final_result = apply_hard_rules(
                    ai_result,
                    hard_rules
                )


                # =============================================
                # STEP 6
                # Final safety validation
                # =============================================

                final_result = final_safety_check(
                    final_result
                )


                # =============================================
                # STEP 7
                # Format result
                # =============================================

                formatted_result = format_result(
                    final_result
                )


                # =============================================
                # STEP 8
                # Save result
                # =============================================

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
    # GUIDELINES REFERENCE
    # =====================================================

    st.markdown("---")

    st.markdown(
        "**Guidelines Reference:**"
    )

    st.markdown(
        "https://help.noon.com/portal/en/kb/articles/product-review-guidelines"
    )
