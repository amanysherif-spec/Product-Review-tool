import streamlit as st
import os
import streamlit.components.v1 as components
import json
import re
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
# GROQ MODELS
# ============================================================

PRIMARY_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "openai/gpt-oss-20b"


# ============================================================
# GROQ API KEY
# ============================================================

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")


if not GROQ_API_KEY:
    st.error(
        "GROQ_API_KEY is missing. Please add GROQ_API_KEY "
        "to Streamlit Secrets."
    )
    st.stop()


client = Groq(api_key=GROQ_API_KEY)


# ============================================================
# ORIGINAL UI
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1056px !important;
        padding-top: 1rem !important;
        padding-bottom: 3rem !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        margin: 0 auto !important;
    }

    header {
        visibility: hidden;
        height: 0px;
    }

    textarea {
        font-size: 16px !important;
        line-height: 1.5 !important;
        background-color: #f0f2f6 !important;
        border-radius: 10px !important;
    }

    div.stButton > button {
        min-height: 48px !important;
        border-radius: 10px !important;
        font-size: 16px !important;
    }

    div.stButton > button[kind="primary"] {
        background-color: #ff4b4b !important;
        border-color: #ff4b4b !important;
        color: white !important;
        font-weight: 600 !important;
    }

    .result-line {
        font-size: 20px;
        line-height: 1.7;
        margin-bottom: 22px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# GUIDELINES
# ============================================================

RULES = {

    "1.1": {
        "section_number": "1",
        "section_title": "Community Guideline Violations",
        "point_number": "1",
        "point_text": "Promotional / advertising content"
    },

    "1.2": {
        "section_number": "1",
        "section_title": "Community Guideline Violations",
        "point_number": "2",
        "point_text": (
            "Offensive, abusive, inappropriate, vulgar, "
            "or distasteful language"
        )
    },

    "1.3": {
        "section_number": "1",
        "section_title": "Community Guideline Violations",
        "point_number": "3",
        "point_text": "Hate speech or discriminatory content"
    },

    "1.4": {
        "section_number": "1",
        "section_title": "Community Guideline Violations",
        "point_number": "4",
        "point_text": "Personal or sensitive information"
    },

    "2.1": {
        "section_number": "2",
        "section_title": "Seller, Order, or Shipping Feedback",
        "point_number": "1",
        "point_text": "Seller performance or seller reputation"
    },

    "2.2": {
        "section_number": "2",
        "section_title": "Seller, Order, or Shipping Feedback",
        "point_number": "2",
        "point_text": "Ordering or return experiences"
    },

    "2.3": {
        "section_number": "2",
        "section_title": "Seller, Order, or Shipping Feedback",
        "point_number": "3",
        "point_text": "Shipping, packaging, or delivery speed"
    },

    "2.4": {
        "section_number": "2",
        "section_title": "Seller, Order, or Shipping Feedback",
        "point_number": "4",
        "point_text": "Product damage or missing items"
    },

    "3.1": {
        "section_number": "3",
        "section_title": "Comments About Pricing or Availability",
        "point_number": "1",
        "point_text": (
            "Finding product cheaper elsewhere / "
            "competitor pricing"
        )
    },

    "3.2": {
        "section_number": "3",
        "section_title": "Comments About Pricing or Availability",
        "point_number": "2",
        "point_text": (
            "Stock status / out-of-stock / availability"
        )
    },

    "4.1": {
        "section_number": "4",
        "section_title": (
            "Conflicts of Interest & Anti-Manipulation"
        ),
        "point_number": "1",
        "point_text": (
            "Written by seller, competitor, employee, "
            "friend, family member, or business partner"
        )
    },

    "4.2": {
        "section_number": "4",
        "section_title": (
            "Conflicts of Interest & Anti-Manipulation"
        ),
        "point_number": "2",
        "point_text": (
            "Posted for compensation or financial incentive"
        )
    }
}


VALID_RULE_IDS = list(RULES.keys())


# ============================================================
# ARABIC TRANSLATIONS
# ============================================================

ARABIC_SECTIONS = {

    "1": "مخالفات إرشادات المجتمع",

    "2": "تعليقات البائع أو الطلب أو الشحن",

    "3": "التعليقات المتعلقة بالسعر أو التوفر",

    "4": "تعارض المصالح والتلاعب"
}


ARABIC_POINTS = {

    "1.1": "محتوى ترويجي أو إعلاني",

    "1.2": (
        "لغة مسيئة أو غير لائقة أو مبتذلة "
        "أو جارحة"
    ),

    "1.3": "خطاب كراهية أو محتوى تمييزي",

    "1.4": "معلومات شخصية أو حساسة",

    "2.1": "أداء البائع أو سمعة البائع",

    "2.2": "تجربة الطلب أو الإرجاع",

    "2.3": "الشحن أو التغليف أو سرعة التوصيل",

    "2.4": "تلف المنتج أو فقدان أجزاء أو منتجات",

    "3.1": (
        "العثور على المنتج بسعر أرخص في مكان آخر "
        "/ أسعار المنافسين"
    ),

    "3.2": "حالة المخزون أو عدم توفر المنتج",

    "4.1": (
        "التقييم من البائع أو المنافس أو الموظف "
        "أو أحد المعارف أو أفراد العائلة أو شريك تجاري"
    ),

    "4.2": (
        "التقييم مقابل تعويض أو حافز مالي"
    )
}


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = str(text).lower().strip()

    # Remove Arabic diacritics and Tatweel
    text = re.sub(
        r"[\u064B-\u065F\u0670\u0640]",
        "",
        text
    )

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

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


# ============================================================
# PHRASE MATCH
# ============================================================

def contains_phrase(text, phrase):

    text = normalize_text(text)
    phrase = normalize_text(phrase)

    if not phrase:
        return False

    return phrase in text


# ============================================================
# HIGH CONFIDENCE HARD RULES
# ============================================================

def detect_hard_rules(review):

    text = normalize_text(review)


    # --------------------------------------------------------
    # 3.1 PRICE
    # --------------------------------------------------------

    price_phrases = [

        "found it cheaper elsewhere",
        "found it cheaper",
        "cheaper elsewhere",
        "cheaper in another store",
        "cheaper at another store",
        "lower price elsewhere",
        "lower price in another store",
        "more expensive than",
        "more expensive here",
        "same product cheaper",
        "same item cheaper",

        "وجدته بسعر ارخص",
        "وجدته ارخص",
        "لقيته بسعر ارخص",
        "لقيته ارخص",
        "ارخص في مكان اخر",
        "ارخص في مكان ثاني",
        "ارخص برا",
        "سعره ارخص",
        "نفس المنتج ارخص",
        "نفس المنتج بسعر ارخص"
    ]


    if any(
        contains_phrase(text, phrase)
        for phrase in price_phrases
    ):

        return "3.1"


    # --------------------------------------------------------
    # 3.2 AVAILABILITY
    # --------------------------------------------------------

    availability_phrases = [

        "out of stock",
        "out-of-stock",
        "unavailable",
        "not available",
        "no stock",
        "no longer available",
        "when will it be available",
        "when will it be back in stock",

        "غير متوفر",
        "غير متاح",
        "نفد المخزون",
        "خلص من المخزون",
        "لا يوجد مخزون",
        "مفيش مخزون",
        "متى سيتوفر",
        "متى يتوفر",
        "متى يرجع للمخزون"
    ]


    if any(
        contains_phrase(text, phrase)
        for phrase in availability_phrases
    ):

        return "3.2"


    # --------------------------------------------------------
    # 2.4 DAMAGE
    # --------------------------------------------------------

    damage_phrases = [

        "broken",
        "damaged",
        "cracked",
        "crushed",
        "destroyed",
        "physically damaged",
        "arrived broken",
        "arrived damaged",

        "مكسور",
        "مكسوره",
        "مكسورة",
        "تالف",
        "تالفة",
        "تالفه",
        "متضرر",
        "متضررة",
        "وصل مكسور",
        "وصل تالف"
    ]


    if any(
        contains_phrase(text, phrase)
        for phrase in damage_phrases
    ):

        return "2.4"


    # --------------------------------------------------------
    # 2.4 MISSING
    # --------------------------------------------------------

    missing_phrases = [

        "missing item",
        "missing items",
        "missing part",
        "missing parts",
        "missing accessory",
        "missing accessories",
        "part is missing",
        "parts are missing",
        "item is missing",

        "جزء ناقص",
        "اجزاء ناقصه",
        "جزء مفقود",
        "اجزاء مفقوده",
        "اكسسوار ناقص",
        "اكسسوارات ناقصه",
        "حاجه ناقصه",
        "شيء ناقص",
        "شي ناقص"
    ]


    if any(
        contains_phrase(text, phrase)
        for phrase in missing_phrases
    ):

        return "2.4"


    return None


# ============================================================
# CLOSEST RULE FOR ALLOWED REVIEWS
# ============================================================

def get_closest_rule(review):

    text = normalize_text(review)


    # Availability preference
    availability_preference = [

        "hope it comes in more colors",
        "hope it comes in other colors",
        "wish it came in more colors",

        "اتمنى ينزل بالوان تانيه",
        "اتمنى يتوفر بالوان تانيه",
        "اتمنى يكون فيه الوان تانيه"
    ]


    if any(
        contains_phrase(text, phrase)
        for phrase in availability_preference
    ):

        return "3.2"


    # Seller
    seller_words = [
        "seller",
        "seller performance",
        "seller reputation",
        "البائع",
        "البايع"
    ]


    if any(
        contains_phrase(text, word)
        for word in seller_words
    ):

        return "2.1"


    # Order / return
    order_words = [

        "order",
        "ordered",
        "return",
        "returned",
        "refund",

        "الطلب",
        "طلبت",
        "ارجاع",
        "إرجاع",
        "استرجاع",
        "استرداد"
    ]


    if any(
        contains_phrase(text, word)
        for word in order_words
    ):

        return "2.2"


    # Shipping
    shipping_words = [

        "shipping",
        "delivery",
        "delivered late",
        "late delivery",
        "packaging",
        "package",
        "courier",

        "الشحن",
        "التوصيل",
        "التغليف",
        "المندوب"
    ]


    if any(
        contains_phrase(text, word)
        for word in shipping_words
    ):

        return "2.3"


    # Damage / missing
    if detect_hard_rules(review) == "2.4":

        return "2.4"


    # Default for ordinary product feedback
    return "2.4"


# ============================================================
# LANGUAGE INSTRUCTION
# ============================================================

def get_language_instruction(language):

    if language == "Arabic":

        return """
Write ONLY the Comment in Arabic.

Do not translate the guideline names into the comment.
Do not add greetings.
Do not add extra explanations.
"""

    return """
Write ONLY the Comment in English.

Do not add greetings.
Do not add extra explanations.
"""


# ============================================================
# AI PROMPT
# ============================================================

def build_prompt(
    review,
    language,
    hard_rule_id
):

    closest_rule = get_closest_rule(review)


    rules_text = """

1.1 Promotional / advertising content
1.2 Offensive, abusive, inappropriate, vulgar,
    or distasteful language
1.3 Hate speech or discriminatory content
1.4 Personal or sensitive information

2.1 Seller performance or seller reputation
2.2 Ordering or return experiences
2.3 Shipping, packaging, or delivery speed
2.4 Product damage or missing items

3.1 Finding product cheaper elsewhere /
    competitor pricing
3.2 Stock status / out-of-stock / availability

4.1 Conflict of interest
4.2 Compensation or financial incentive
"""


    return f"""
You are Noon Product Review Moderation AI.

Your ONLY job is to classify the customer review according
to the Noon Customer Review Article.

Do NOT invent rules.

Do NOT create new categories.

Do NOT change the meaning of the article.

============================================================
OFFICIAL RULES
============================================================

{rules_text}

============================================================
VERY IMPORTANT: OFFENSIVE LANGUAGE
============================================================

The article specifically prohibits:

- Offensive language
- Abusive language
- Inappropriate language
- Vulgar language
- Distasteful language

If the review contains genuinely offensive, abusive,
vulgar, inappropriate, or distasteful wording, classify it:

NOT_ALLOWED
Rule 1.2

Examples:

"The product is disgusting"
-> NOT_ALLOWED / 1.2

"This product is fucking garbage"
-> NOT_ALLOWED / 1.2

"The seller is an idiot"
-> NOT_ALLOWED / 1.2

"المنتج مقرف"
-> NOT_ALLOWED / 1.2

"المنتج زبالة"
-> NOT_ALLOWED / 1.2

"البائع غبي ومقرف"
-> NOT_ALLOWED / 1.2

Arabic offensive words must be understood according to
their actual meaning and context.

Do NOT ignore offensive Arabic wording just because
the review is written in Arabic.

============================================================
IMPORTANT DIFFERENCE
============================================================

Normal negative product feedback is NOT automatically
offensive.

Examples:

"The product is bad"
-> ALLOWED

"The quality is poor"
-> ALLOWED

"The battery drains quickly"
-> ALLOWED

"I don't like the product"
-> ALLOWED

"The product is useless"
-> ALLOWED when it is normal product criticism.

"المنتج سيء"
-> ALLOWED

"المنتج وحش"
-> ALLOWED

"البطارية ضعيفة"
-> ALLOWED

"البطارية بتخلص بسرعة"
-> ALLOWED

"مش عاجبني"
-> ALLOWED

Do NOT classify normal product criticism as 1.2.

The distinction must be based on whether the wording itself
is offensive / abusive / vulgar / inappropriate /
distasteful, not simply whether the customer is unhappy.

============================================================
PRICE
============================================================

"Found it cheaper elsewhere"
-> NOT_ALLOWED / 3.1

"Found the same product cheaper"
-> NOT_ALLOWED / 3.1

"وجدته بسعر ارخص"
-> NOT_ALLOWED / 3.1

"لقيته ارخص"
-> NOT_ALLOWED / 3.1

============================================================
AVAILABILITY
============================================================

"Out of stock"
-> NOT_ALLOWED / 3.2

"It is unavailable"
-> NOT_ALLOWED / 3.2

"Hope it comes in more colors"
-> ALLOWED

============================================================
DAMAGE / MISSING
============================================================

"Product arrived broken"
-> NOT_ALLOWED / 2.4

"The product is damaged"
-> NOT_ALLOWED / 2.4

"An accessory is missing"
-> NOT_ALLOWED / 2.4

============================================================
PRODUCT PERFORMANCE
============================================================

"Battery drains quickly"
-> ALLOWED

"The battery is weak"
-> ALLOWED

"The product is not effective"
-> ALLOWED

"The product does not work as expected"
-> ALLOWED

These are product opinions unless the customer explicitly
reports physical damage or a missing item.

============================================================
MOST IMPORTANT
============================================================

1. Follow the Article.
2. Offensive wording = NOT_ALLOWED / 1.2.
3. Do not confuse negative product opinions with offensive language.
4. Arabic offensive wording must be understood correctly.
5. Price comparison with cheaper elsewhere = 3.1.
6. Actual stock problem = 3.2.
7. Damage or missing = 2.4.
8. Never use NONE.
9. Never use N/A.
10. Never invent a guideline.
11. For ALLOWED reviews, choose the closest valid rule.
12. The closest rule does NOT mean the review violates that rule.

============================================================
CUSTOMER REVIEW
============================================================

{review}

============================================================
CLOSEST RULE IF ALLOWED
============================================================

{closest_rule}

============================================================
LANGUAGE
============================================================

{get_language_instruction(language)}

Return ONLY JSON.
"""


# ============================================================
# JSON SCHEMA
# ============================================================

REVIEW_SCHEMA = {

    "type": "object",

    "additionalProperties": False,

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

        "comment": {
            "type": "string"
        }
    },

    "required": [
        "decision",
        "rule_id",
        "comment"
    ]
}


# ============================================================
# CALL AI
# ============================================================

def call_model(
    model,
    review,
    language,
    hard_rule_id,
    reasoning_effort="medium"
):

    prompt = build_prompt(
        review=review,
        language=language,
        hard_rule_id=hard_rule_id
    )


    response = client.chat.completions.create(

        model=model,

        messages=[

            {
                "role": "system",
                "content": (
                    "You are a strict Noon product review "
                    "moderation classifier. Follow the provided "
                    "article exactly."
                )
            },

            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0,

        max_tokens=900,

        reasoning_effort=reasoning_effort,

        response_format={
            "type": "json_schema",

            "json_schema": {
                "name": "noon_review_moderation",
                "strict": True,
                "schema": REVIEW_SCHEMA
            }
        }
    )


    content = response.choices[0].message.content


    if not content:
        raise ValueError(
            "Empty AI response."
        )


    return json.loads(content)


# ============================================================
# RELIABLE AI CALL
# ============================================================

def evaluate_with_reliability(
    review,
    language,
    hard_rule_id
):

    models = [
        PRIMARY_MODEL,
        FALLBACK_MODEL
    ]


    last_error = None


    for model in models:

        for attempt in range(2):

            try:

                result = call_model(
                    model=model,
                    review=review,
                    language=language,
                    hard_rule_id=hard_rule_id,
                    reasoning_effort="medium"
                )

                return result, model


            except Exception as e:

                last_error = e

                error_text = str(e).lower()


                if (
                    "decommissioned" in error_text
                    or "model not found" in error_text
                    or "model_not_found" in error_text
                    or "does not exist" in error_text
                ):

                    break


                if attempt == 0:

                    time.sleep(1)


    raise RuntimeError(
        f"AI evaluation failed: {last_error}"
    )


# ============================================================
# ADJUDICATOR
# ============================================================

def call_adjudicator(
    model,
    review,
    language,
    first_result
):

    prompt = f"""
You are the final Noon Product Review Policy checker.

Check whether the first AI classification follows the
Noon Customer Review Article.

Correct it if necessary.

IMPORTANT:

Offensive / abusive / inappropriate / vulgar /
distasteful language = NOT_ALLOWED / 1.2.

Examples:

"The product is disgusting"
= NOT_ALLOWED / 1.2

"المنتج مقرف"
= NOT_ALLOWED / 1.2

"المنتج زبالة"
= NOT_ALLOWED / 1.2

Normal negative product criticism remains ALLOWED:

"The product is bad"
= ALLOWED

"The quality is poor"
= ALLOWED

"The battery drains quickly"
= ALLOWED

"البطارية ضعيفة"
= ALLOWED

"مش عاجبني"
= ALLOWED

Price comparison:

"Found it cheaper elsewhere"
= NOT_ALLOWED / 3.1

"وجدته بسعر ارخص"
= NOT_ALLOWED / 3.1

Availability:

"Out of stock"
= NOT_ALLOWED / 3.2

"Hope it comes in more colors"
= ALLOWED

Damage:

"Product arrived broken"
= NOT_ALLOWED / 2.4

Missing:

"Missing accessory"
= NOT_ALLOWED / 2.4

Do not invent any rule.

Do not over-block normal product criticism.

============================================================
CUSTOMER REVIEW
============================================================

{review}

============================================================
FIRST RESULT
============================================================

{json.dumps(
    first_result,
    ensure_ascii=False,
    indent=2
)}

============================================================

Return ONLY JSON.

The JSON must contain:

decision
rule_id
comment

Valid rule IDs:

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

{get_language_instruction(language)}
"""


    response = client.chat.completions.create(

        model=model,

        messages=[

            {
                "role": "system",
                "content": (
                    "You are the final policy quality "
                    "control reviewer."
                )
            },

            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0,

        max_tokens=900,

        reasoning_effort="high",

        response_format={
            "type": "json_schema",

            "json_schema": {
                "name": "noon_review_adjudication",
                "strict": True,
                "schema": REVIEW_SCHEMA
            }
        }
    )


    content = response.choices[0].message.content


    if not content:
        raise ValueError(
            "Empty adjudicator response."
        )


    return json.loads(content)


# ============================================================
# VALIDATE
# ============================================================

def validate_result(result):

    if not isinstance(result, dict):
        raise ValueError(
            "Invalid result."
        )


    if result.get("decision") not in [
        "ALLOWED",
        "NOT_ALLOWED"
    ]:

        raise ValueError(
            "Invalid decision."
        )


    if result.get("rule_id") not in RULES:

        raise ValueError(
            "Invalid rule ID."
        )


    if not str(
        result.get("comment", "")
    ).strip():

        raise ValueError(
            "Empty comment."
        )


# ============================================================
# HARD RULE OUTPUT
# ============================================================

def apply_hard_rule(
    result,
    hard_rule_id,
    language
):

    if not hard_rule_id:

        return result


    result["decision"] = "NOT_ALLOWED"
    result["rule_id"] = hard_rule_id


    if language == "English":

        if hard_rule_id == "3.1":

            result["comment"] = (
                "Review mentions finding the product cheaper "
                "elsewhere and is not allowed."
            )


        elif hard_rule_id == "3.2":

            result["comment"] = (
                "Review refers to product availability or "
                "stock status and is not allowed."
            )


        elif hard_rule_id == "2.4":

            result["comment"] = (
                "Review reports product damage or missing "
                "items and is not allowed."
            )


    else:

        if hard_rule_id == "3.1":

            result["comment"] = (
                "التعليق يذكر العثور على المنتج بسعر أرخص "
                "في مكان آخر ولذلك فهو غير مسموح."
            )


        elif hard_rule_id == "3.2":

            result["comment"] = (
                "التعليق يتحدث عن توفر المنتج أو حالة المخزون "
                "ولذلك فهو غير مسموح."
            )


        elif hard_rule_id == "2.4":

            result["comment"] = (
                "التعليق يوضح وجود تلف في المنتج أو فقدان "
                "أجزاء أو منتجات ولذلك فهو غير مسموح."
            )


    return result


# ============================================================
# ALLOWED RULE
# ============================================================

def apply_allowed_rule(
    result,
    review,
    language
):

    if result["decision"] != "ALLOWED":

        return result


    closest_rule = get_closest_rule(
        review
    )


    result["rule_id"] = closest_rule


    if language == "English":

        result["comment"] = (
            "Allowed: the review does not contain a "
            "violation of the Noon Customer Review guidelines."
        )

    else:

        result["comment"] = (
            "مسموح: التعليق لا يحتوي على مخالفة "
            "لإرشادات تقييمات العملاء في نون."
        )


    return result


# ============================================================
# OFFENSIVE LANGUAGE SAFETY CHECK
# ============================================================

def detect_clear_offensive_language(review):

    text = normalize_text(review)


    # These are deliberately HIGH-CONFIDENCE expressions.
    # We do not use generic negative words such as:
    # bad, poor, useless, hate, سيء, وحش, etc.
    #
    # This prevents normal product criticism from being
    # incorrectly removed.

    offensive_phrases = [

        # English
        "fucking garbage",
        "fucking shit",
        "piece of shit",
        "shit product",
        "shit item",
        "what a disgusting product",
        "this product is disgusting",
        "disgusting product",

        # Arabic
        "المنتج مقرف",
        "المنتج زباله",
        "المنتج زبالة",
        "منتج مقرف",
        "منتج زباله",
        "منتج زبالة",
        "البائع مقرف",
        "البائع غبي ومقرف"
    ]


    for phrase in offensive_phrases:

        if contains_phrase(
            text,
            phrase
        ):

            return True


    return False


# ============================================================
# FINAL EVALUATION
# ============================================================

def evaluate_review(
    review,
    language
):

    review = review.strip()


    if not review:

        raise ValueError(
            "Please enter a customer review."
        )


    # --------------------------------------------------------
    # 1. Deterministic hard rules
    # --------------------------------------------------------

    hard_rule_id = detect_hard_rules(
        review
    )


    # --------------------------------------------------------
    # 2. AI classification
    # --------------------------------------------------------

    result, used_model = (
        evaluate_with_reliability(
            review=review,
            language=language,
            hard_rule_id=hard_rule_id
        )
    )


    validate_result(
        result
    )


    # --------------------------------------------------------
    # 3. AI quality check
    # --------------------------------------------------------

    try:

        checked_result = call_adjudicator(
            model=used_model,
            review=review,
            language=language,
            first_result=result
        )


        validate_result(
            checked_result
        )


        result = checked_result


    except Exception:

        pass


    # --------------------------------------------------------
    # 4. Explicit high-confidence offensive language
    # --------------------------------------------------------

    if detect_clear_offensive_language(
        review
    ):

        result["decision"] = "NOT_ALLOWED"
        result["rule_id"] = "1.2"


        if language == "English":

            result["comment"] = (
                "Review contains offensive, abusive, "
                "inappropriate, vulgar, or distasteful "
                "language and is not allowed."
            )

        else:

            result["comment"] = (
                "التعليق يحتوي على ألفاظ مسيئة أو غير لائقة "
                "أو مبتذلة ولذلك فهو غير مسموح."
            )


    # --------------------------------------------------------
    # 5. Hard article rules override AI
    # --------------------------------------------------------

    result = apply_hard_rule(
        result=result,
        hard_rule_id=hard_rule_id,
        language=language
    )


    # --------------------------------------------------------
    # 6. If ALLOWED, use closest valid rule
    # --------------------------------------------------------

    result = apply_allowed_rule(
        result=result,
        review=review,
        language=language
    )


    # --------------------------------------------------------
    # 7. Final cleanup
    # --------------------------------------------------------

    if result["rule_id"] not in RULES:

        result["rule_id"] = "2.4"


    return result, used_model


# ============================================================
# UI
# ============================================================

st.title(
    "Product Review Moderation Tool"
)


# ============================================================
# LANGUAGE
# ============================================================

language = st.radio(
    "Select Output Language / اختر لغة الرد:",
    [
        "English",
        "Arabic"
    ],
    horizontal=True
)


# ============================================================
# CUSTOMER REVIEW
# ============================================================

review_text = st.text_area(
    "Enter Customer Review:",
    height=180,
    placeholder="Enter the customer review here..."
)


# ============================================================
# BUTTONS
# ============================================================

col1, col2, col3 = st.columns(
    [1.2, 0.8, 7]
)


with col1:

    evaluate_button = st.button(
        "Evaluate Review",
        type="primary",
        use_container_width=True
    )


with col2:

    reset_button = st.button(
        "Reset",
        use_container_width=True
    )


# ============================================================
# RESET
# ============================================================

if reset_button:

    st.session_state.pop(
        "moderation_result",
        None
    )

    st.session_state.pop(
        "used_model",
        None
    )

    st.rerun()


# ============================================================
# EVALUATE
# ============================================================

if evaluate_button:

    if not review_text.strip():

        st.warning(
            "Please enter a customer review."
            if language == "English"
            else
            "يرجى إدخال تعليق العميل."
        )

    else:

        try:

            with st.spinner(
                "Analyzing review..."
                if language == "English"
                else
                "جاري تحليل التعليق..."
            ):

                result, used_model = evaluate_review(
                    review=review_text,
                    language=language
                )


                st.session_state[
                    "moderation_result"
                ] = result


                st.session_state[
                    "used_model"
                ] = used_model


        except Exception as e:

            st.error(
                "The application could not complete the evaluation."
            )

            st.exception(e)


# ============================================================
# RESULT
# ============================================================

if "moderation_result" in st.session_state:

    result = st.session_state[
        "moderation_result"
    ]


    st.markdown(
        "## Result:"
    )


    # ========================================================
    # DECISION
    # ========================================================

    if result["decision"] == "ALLOWED":

        decision_text = (
            "✓ Allowed — the review can remain"
        )

        decision_color = "#21a366"

    else:

        decision_text = (
            "❌ Not allowed — the review should be removed"
        )

        decision_color = "#ff4b5c"


    st.markdown(
        f"""
        <div class="result-line">
            <strong>Decision:</strong>
            <span style="color:{decision_color};">
                {decision_text}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # MAIN GUIDELINE SECTION
    # ========================================================

    rule_id = result["rule_id"]

    rule = RULES[rule_id]


    if language == "Arabic":

        section_title = ARABIC_SECTIONS[
            rule["section_number"]
        ]

        point_text = ARABIC_POINTS[
            rule_id
        ]

    else:

        section_title = rule[
            "section_title"
        ]

        point_text = rule[
            "point_text"
        ]


    st.markdown(
        f"""
        <div class="result-line">
            <strong>Main Guideline Section:</strong>
            {rule["section_number"]}.
            {section_title}
        </div>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # SPECIFIC SUB-RULE
    # ========================================================

    st.markdown(
        f"""
        <div class="result-line">
            <strong>Specific Sub-rule:</strong>
            Point {rule["point_number"]}:
            {point_text}
        </div>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # COMMENT
    # ========================================================

    st.markdown(
        f"""
        <div class="result-line">
            <strong>Comment:</strong>
            {result["comment"]}
        </div>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # COPY COMMENT
    # ========================================================

    escaped_comment = (
        result["comment"]
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("$", "\\$")
    )


    components.html(
        f"""
        <button
            onclick="
                navigator.clipboard.writeText(`{escaped_comment}`);
                this.innerText='✓ Copied';
            "
            style="
                padding:8px 16px;
                border:1px solid #dddddd;
                border-radius:6px;
                background:#f7f7f7;
                cursor:pointer;
                font-size:14px;
            "
        >
            📋 Copy Comment
        </button>
        """,
        height=45
    )


# ============================================================
# GUIDELINES LINK
# ============================================================

st.markdown("---")

st.markdown(
    "[Noon Customer Reviews Guidelines]"
    "(https://help.noon.com/portal/en/kb/articles/customer-reviews)"
)
