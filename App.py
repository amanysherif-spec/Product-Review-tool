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
        "GROQ_API_KEY is missing. "
        "Please add GROQ_API_KEY to Streamlit Secrets."
    )
    st.stop()


client = Groq(api_key=GROQ_API_KEY)


# ============================================================
# ORIGINAL UI STYLE
# ============================================================

st.markdown(
    """
    <style>

    /* ========================================================
       MAIN CONTAINER
       ======================================================== */

    .block-container {
        max-width: 1056px !important;
        padding-top: 1rem !important;
        padding-bottom: 3rem !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        margin: 0 auto !important;
    }


    /* ========================================================
       REMOVE EXTRA TOP SPACE
       ======================================================== */

    header {
        visibility: hidden;
        height: 0px;
    }


    /* ========================================================
       TEXTAREA
       ======================================================== */

    textarea {
        font-size: 16px !important;
        line-height: 1.5 !important;
        background-color: #f0f2f6 !important;
        border-radius: 10px !important;
    }


    /* ========================================================
       BUTTONS
       ======================================================== */

    div.stButton > button {
        min-height: 48px !important;
        border-radius: 10px !important;
        font-size: 16px !important;
    }


    /* ========================================================
       PRIMARY BUTTON
       ======================================================== */

    div.stButton > button[kind="primary"] {
        background-color: #ff4b4b !important;
        border-color: #ff4b4b !important;
        color: white !important;
        font-weight: 600 !important;
    }


    /* ========================================================
       RESULT TEXT
       ======================================================== */

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

GUIDELINES = {

    "1": {
        "title": "Community Guideline Violations",
        "points": {
            "1": "Promotional / advertising content",
            "2": "Offensive, abusive, inappropriate, vulgar, or distasteful language",
            "3": "Hate speech or discriminatory content",
            "4": "Personal or sensitive information"
        }
    },

    "2": {
        "title": "Seller, Order, or Shipping Feedback",
        "points": {
            "1": "Seller performance or seller reputation",
            "2": "Ordering or return experiences",
            "3": "Shipping, packaging, or delivery speed",
            "4": "Product damage or missing items"
        }
    },

    "3": {
        "title": "Comments About Pricing or Availability",
        "points": {
            "1": "Finding product cheaper elsewhere / competitor pricing",
            "2": "Stock status / out-of-stock / availability"
        }
    },

    "4": {
        "title": "Conflicts of Interest & Anti-Manipulation",
        "points": {
            "1": "Written by seller, competitor, employee, friend, family member, or business partner",
            "2": "Posted for compensation or financial incentive"
        }
    }
}


# ============================================================
# CANONICAL RULES
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
        "point_text": "Offensive, abusive, inappropriate, vulgar, or distasteful language"
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
        "point_text": "Finding product cheaper elsewhere / competitor pricing"
    },

    "3.2": {
        "section_number": "3",
        "section_title": "Comments About Pricing or Availability",
        "point_number": "2",
        "point_text": "Stock status / out-of-stock / availability"
    },

    "4.1": {
        "section_number": "4",
        "section_title": "Conflicts of Interest & Anti-Manipulation",
        "point_number": "1",
        "point_text": "Written by seller, competitor, employee, friend, family member, or business partner"
    },

    "4.2": {
        "section_number": "4",
        "section_title": "Conflicts of Interest & Anti-Manipulation",
        "point_number": "2",
        "point_text": "Posted for compensation or financial incentive"
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

    "1.2": "لغة مسيئة أو غير لائقة أو مبتذلة أو جارحة",

    "1.3": "خطاب كراهية أو محتوى تمييزي",

    "1.4": "معلومات شخصية أو حساسة",

    "2.1": "أداء البائع أو سمعة البائع",

    "2.2": "تجربة الطلب أو الإرجاع",

    "2.3": "الشحن أو التغليف أو سرعة التوصيل",

    "2.4": "تلف المنتج أو فقدان أجزاء أو منتجات",

    "3.1": "العثور على المنتج بسعر أرخص في مكان آخر / أسعار المنافسين",

    "3.2": "حالة المخزون أو عدم توفر المنتج",

    "4.1": "التقييم من البائع أو المنافس أو الموظف أو أحد المعارف أو أفراد العائلة أو شريك تجاري",

    "4.2": "التقييم مقابل تعويض أو حافز مالي"
}


# ============================================================
# LANGUAGE INSTRUCTION
# ============================================================

def get_language_instruction(language):

    if language == "Arabic":

        return """
OUTPUT LANGUAGE:
- Write the reason in Arabic.
- Write the generated comment in Arabic.
- Do not add greetings.
- Do not add unnecessary explanations.
"""

    return """
OUTPUT LANGUAGE:
- Write the reason in English.
- Write the generated comment in English.
- Do not add greetings.
- Do not add unnecessary explanations.
"""


# ============================================================
# NORMALIZE TEXT
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
# GET CLOSEST RULE
# ============================================================

def get_closest_rule(review):

    text = normalize_text(review)


    # PRICE
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
        "نفس المنتج بسعر ارخص",
        "نفسه ارخص"
    ]

    if any(
        normalize_text(x) in text
        for x in price_phrases
    ):
        return "3.1"


    # AVAILABILITY
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
        "خلص من المخزون",
        "نفد المخزون",
        "مفيش مخزون",
        "لا يوجد مخزون",
        "متى سيتوفر",
        "متى يتوفر",
        "متى يرجع للمخزون"
    ]

    if any(
        normalize_text(x) in text
        for x in availability_phrases
    ):
        return "3.2"


    # SELLER
    seller_phrases = [

        "seller",
        "seller service",
        "seller support",
        "seller attitude",
        "seller behavior",
        "seller performance",

        "البائع",
        "البايع",
        "تعامل البائع",
        "خدمة البائع",
        "تصرف البائع",
        "اداء البائع"
    ]

    if any(
        normalize_text(x) in text
        for x in seller_phrases
    ):
        return "2.1"


    # ORDER / RETURN
    order_phrases = [

        "order",
        "ordered",
        "cancelled my order",
        "cancel my order",
        "returned",
        "return",
        "refund",

        "الطلب",
        "طلبت",
        "الغاء الطلب",
        "إلغاء الطلب",
        "ارجاع",
        "إرجاع",
        "استرجاع",
        "استرداد"
    ]

    if any(
        normalize_text(x) in text
        for x in order_phrases
    ):
        return "2.2"


    # SHIPPING
    shipping_phrases = [

        "shipping",
        "delivery",
        "delivered late",
        "late delivery",
        "delivery took",
        "packaging",
        "package",
        "courier",
        "delivery driver",

        "الشحن",
        "التوصيل",
        "وصل متاخر",
        "وصل متأخر",
        "التغليف",
        "الكرتونه",
        "الكرتونة",
        "المندوب"
    ]

    if any(
        normalize_text(x) in text
        for x in shipping_phrases
    ):
        return "2.3"


    # DAMAGE / MISSING
    damage_missing_phrases = [

        "broken",
        "damaged",
        "cracked",
        "crushed",
        "destroyed",
        "physically damaged",

        "missing item",
        "missing items",
        "missing part",
        "missing parts",
        "missing accessory",
        "missing accessories",

        "مكسور",
        "مكسوره",
        "مكسورة",
        "تالف",
        "تالفة",
        "تالفه",
        "متضرر",
        "متضررة",
        "جزء ناقص",
        "اجزاء ناقصه",
        "جزء مفقود",
        "اكسسوار ناقص",
        "اكسسوارات ناقصه"
    ]

    if any(
        normalize_text(x) in text
        for x in damage_missing_phrases
    ):
        return "2.4"


    # PROMOTIONAL
    promotional_phrases = [

        "buy from me",
        "contact me",
        "contact us",
        "visit my store",
        "visit our store",
        "whatsapp me",
        "whatsapp us",
        "call me",
        "call us",
        "discount code",
        "promo code",

        "اشتروا مني",
        "تواصل معي",
        "تواصل معنا",
        "زوروا متجري",
        "واتساب",
        "كود خصم"
    ]

    if any(
        normalize_text(x) in text
        for x in promotional_phrases
    ):
        return "1.1"


    # PERSONAL INFORMATION
    personal_info_phrases = [

        "phone number",
        "mobile number",
        "email address",
        "credit card",
        "card number",
        "bank account",
        "password",
        "otp",

        "رقم الهاتف",
        "رقم الموبايل",
        "البريد الالكتروني",
        "الايميل",
        "رقم البطاقة",
        "رقم الحساب",
        "كلمة المرور",
        "رمز التحقق"
    ]

    if any(
        normalize_text(x) in text
        for x in personal_info_phrases
    ):
        return "1.4"


    # CONFLICT OF INTEREST
    conflict_phrases = [

        "i am the seller",
        "i work for the seller",
        "my company",
        "my store",
        "competitor",
        "employee",
        "family member",
        "friend of the seller",
        "business partner",

        "انا البائع",
        "انا من الشركة",
        "انا موظف",
        "منافس",
        "صديقي",
        "قريبي",
        "شريكي"
    ]

    if any(
        normalize_text(x) in text
        for x in conflict_phrases
    ):
        return "4.1"


    # COMPENSATION
    compensation_phrases = [

        "paid to review",
        "paid for review",
        "received money",
        "received compensation",
        "free product for review",
        "in exchange for a review",
        "gifted for review",

        "دفعت لي",
        "تم الدفع لي",
        "مقابل التقييم",
        "مقابل المراجعة",
        "حصلت على منتج مجاني"
    ]

    if any(
        normalize_text(x) in text
        for x in compensation_phrases
    ):
        return "4.2"


    # DEFAULT FOR NORMAL PRODUCT FEEDBACK
    return "2.4"


# ============================================================
# HARD RULE DETECTOR
# ============================================================

def detect_hard_rules(review):

    text = normalize_text(review)


    result = {
        "rule_id": None,
        "reason": None
    }


    # PRICE
    price_patterns = [

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
        "نفس المنتج بسعر ارخص",
        "نفسه ارخص"
    ]

    if any(
        normalize_text(x) in text
        for x in price_patterns
    ):

        result["rule_id"] = "3.1"

        result["reason"] = (
            "The review explicitly compares the product "
            "price with a cheaper price elsewhere."
        )

        return result


    # AVAILABILITY
    availability_patterns = [

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
        "خلص من المخزون",
        "نفد المخزون",
        "لا يوجد مخزون",
        "مفيش مخزون",
        "متى سيتوفر",
        "متى يتوفر",
        "متى يرجع للمخزون"
    ]

    if any(
        normalize_text(x) in text
        for x in availability_patterns
    ):

        result["rule_id"] = "3.2"

        result["reason"] = (
            "The review explicitly discusses product "
            "availability or stock status."
        )

        return result


    # DAMAGE
    damage_patterns = [

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
        normalize_text(x) in text
        for x in damage_patterns
    ):

        result["rule_id"] = "2.4"

        result["reason"] = (
            "The review explicitly reports that the product "
            "arrived damaged or physically broken."
        )

        return result


    # MISSING
    missing_patterns = [

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
        normalize_text(x) in text
        for x in missing_patterns
    ):

        result["rule_id"] = "2.4"

        result["reason"] = (
            "The review explicitly reports a missing product, "
            "part, or accessory."
        )

        return result


    return result


# ============================================================
# AI PROMPT
# ============================================================

def build_prompt(
    review,
    language,
    hard_rule_result
):

    closest_rule = get_closest_rule(review)


    if hard_rule_result.get("rule_id"):

        hard_rule_text = (
            f"{hard_rule_result['rule_id']} - "
            f"{RULES[hard_rule_result['rule_id']]['point_text']}"
        )

    else:

        hard_rule_text = "NONE"


    closest_rule_text = (
        f"{closest_rule} - "
        f"{RULES[closest_rule]['point_text']}"
    )


    return f"""
You are a highly accurate Noon product-review moderation classifier.

Evaluate ONE customer review according to the rules below.

============================================================
MOST IMPORTANT PRINCIPLE
============================================================

A customer is allowed to express negative opinions about
the PRODUCT.

Normal product criticism must NOT be removed automatically.

Examples of ALLOWED product criticism:

"The product is bad."
"The product is disappointing."
"I don't like it."
"The battery is terrible."
"The battery drains quickly."
"It is not useful."
"The quality is poor."
"The color is ugly."
"I regret buying it."

Arabic:

"المنتج سيء"
"المنتج وحش"
"مش عاجبني"
"البطارية ضعيفة"
"البطارية بتخلص بسرعة"
"المنتج غير مفيد"

These are normal product opinions.

============================================================
OFFENSIVE LANGUAGE
============================================================

You MUST identify genuinely offensive, abusive, vulgar,
obscene, inappropriate, insulting, or distasteful language.

Examples:

"This product is disgusting."
"This is fucking garbage."
"The seller is an idiot."
"The seller is disgusting."

Arabic:

"المنتج مقرف"
"المنتج زبالة"
"البائع غبي ومقرف"

These should be NOT_ALLOWED under rule 1.2.

IMPORTANT:

Do not classify every negative word as offensive.

"The product is bad."
"The battery is terrible."
"I hate this product."

are normally ALLOWED when they are simply product opinions.

Use the FULL CONTEXT.

============================================================
SECTION 1
============================================================

1.1 Promotional / advertising content

1.2 Offensive, abusive, inappropriate, vulgar,
or distasteful language

1.3 Hate speech or discriminatory content

1.4 Personal or sensitive information

============================================================
SECTION 2
============================================================

2.1 Seller performance or seller reputation

2.2 Ordering or return experiences

2.3 Shipping, packaging, or delivery speed

2.4 Product damage or missing items

IMPORTANT:

"Battery drains quickly"

is NOT shipping feedback.

It is normal product feedback and should be ALLOWED.

============================================================
SECTION 3
============================================================

3.1 Finding product cheaper elsewhere.

Examples:

"Found it cheaper elsewhere"
"Found the same product cheaper"
"وجدته بسعر ارخص"
"لقيته ارخص"
"نفس المنتج ارخص"

These are NOT_ALLOWED.

3.2 Stock / availability.

Examples:

"Out of stock"
"When will this be available?"
"It is unavailable."

These are NOT_ALLOWED.

But:

"Hope it comes in more colors"

is ALLOWED.

============================================================
SECTION 4
============================================================

4.1 Conflict of interest.

4.2 Compensation or financial incentive.

============================================================
IMPORTANT
============================================================

- Never invent a violation.
- Negative product feedback can be ALLOWED.
- Offensive language must be NOT_ALLOWED.
- Seller complaints are NOT_ALLOWED.
- Shipping complaints are NOT_ALLOWED.
- Damage/missing items are NOT_ALLOWED.
- Competitor price comparison is NOT_ALLOWED.
- Stock-status complaints are NOT_ALLOWED.
- General wishes about product availability can be ALLOWED.
- Do not confuse product performance with shipping.
- Do not classify "battery", "quality", "color", "size",
  "performance", or "effectiveness" as shipping automatically.

For ALLOWED reviews, select the closest valid rule ID.

Never use:

NONE
N/A
No
Unknown

Closest rule:
{closest_rule_text}

High-confidence detector:
{hard_rule_text}

============================================================
CUSTOMER REVIEW
============================================================

{review}

{get_language_instruction(language)}

Return ONLY valid JSON.
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

        "section_number": {
            "type": "string"
        },

        "section_title": {
            "type": "string"
        },

        "point_number": {
            "type": "string"
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
    ]
}


# ============================================================
# CALL MODEL
# ============================================================

def call_model(
    model,
    review,
    language,
    hard_rule_result,
    reasoning_effort="medium"
):

    prompt = build_prompt(
        review,
        language,
        hard_rule_result
    )


    response = client.chat.completions.create(

        model=model,

        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict and highly accurate "
                    "product review moderation engine."
                )
            },

            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0,

        max_tokens=1200,

        reasoning_effort=reasoning_effort,

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
            "Empty response from Groq."
        )


    return json.loads(content)


# ============================================================
# RELIABLE AI EVALUATION
# ============================================================

def evaluate_with_reliability(
    review,
    language,
    hard_rule_result
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
                    hard_rule_result=hard_rule_result,
                    reasoning_effort="medium"
                )

                return result, model


            except Exception as e:

                last_error = e

                error_text = str(e).lower()


                if (
                    "decommissioned" in error_text
                    or "model_not_found" in error_text
                    or "model not found" in error_text
                    or "does not exist" in error_text
                ):

                    break


                if attempt == 0:
                    time.sleep(1)


    raise RuntimeError(
        f"All AI attempts failed: {last_error}"
    )


# ============================================================
# SECOND AI QUALITY CHECK
# ============================================================

def call_ai_adjudicator(
    model,
    review,
    language,
    first_result
):

    prompt = f"""
You are the FINAL QUALITY CONTROL reviewer for Noon
product review moderation.

Review the original customer review and the first AI result.

Correct the result if necessary.

Pay special attention to:

1. Offensive / abusive / vulgar language
2. Arabic offensive language
3. Difference between product criticism and offensive language
4. Seller complaints
5. Shipping complaints
6. Product damage
7. Missing items
8. Competitor price comparison
9. Availability

============================================================
IMPORTANT EXAMPLES
============================================================

"The product is bad."
-> ALLOWED

"The battery is terrible."
-> ALLOWED

"I don't like this product."
-> ALLOWED

"The product is disgusting."
-> NOT_ALLOWED 1.2

"المنتج مقرف"
-> NOT_ALLOWED 1.2

"المنتج زبالة"
-> NOT_ALLOWED 1.2

"Found it cheaper elsewhere"
-> NOT_ALLOWED 3.1

"وجدته بسعر ارخص"
-> NOT_ALLOWED 3.1

"Out of stock"
-> NOT_ALLOWED 3.2

"Hope it comes in more colors"
-> ALLOWED

"Product arrived broken"
-> NOT_ALLOWED 2.4

"Battery drains quickly"
-> ALLOWED

"Received wrong item"
-> NOT_ALLOWED 2.1

============================================================
IMPORTANT
============================================================

Do not over-block normal product criticism.

The fact that a review is negative does not automatically
make it a guideline violation.

For ALLOWED reviews, use the closest valid rule.

Never use NONE or N/A.

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

============================================================
ORIGINAL REVIEW
============================================================

{review}

============================================================
FIRST AI RESULT
============================================================

{json.dumps(first_result, ensure_ascii=False, indent=2)}

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

{get_language_instruction(language)}
"""


    response = client.chat.completions.create(

        model=model,

        messages=[
            {
                "role": "system",
                "content": (
                    "You are the final quality-control "
                    "reviewer."
                )
            },

            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0,

        max_tokens=1200,

        reasoning_effort="high",

        response_format={
            "type": "json_schema",

            "json_schema": {
                "name": "product_review_adjudication",
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
# VALIDATE RESULT
# ============================================================

def validate_result(result):

    if not isinstance(result, dict):

        raise ValueError(
            "Invalid AI result."
        )


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
                f"Missing field: {field}"
            )


    if result["decision"] not in [
        "ALLOWED",
        "NOT_ALLOWED"
    ]:

        raise ValueError(
            "Invalid decision."
        )


    if result["rule_id"] not in RULES:

        raise ValueError(
            f"Invalid rule ID: {result['rule_id']}"
        )


    if not str(
        result["reason"]
    ).strip():

        raise ValueError(
            "Empty reason."
        )


    if not str(
        result["comment"]
    ).strip():

        raise ValueError(
            "Empty comment."
        )


    return True


# ============================================================
# ENFORCE RULE CONSISTENCY
# ============================================================

def enforce_rule_consistency(result):

    rule_id = result["rule_id"]

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


    return result


# ============================================================
# APPLY ARABIC LABELS
# ============================================================

def apply_arabic_labels(result):

    rule_id = result["rule_id"]


    result["section_title"] = (
        ARABIC_SECTIONS[
            RULES[rule_id]["section_number"]
        ]
    )


    result["point_text"] = (
        ARABIC_POINTS[rule_id]
    )


    return result


# ============================================================
# HARD RULE OVERRIDE
# ============================================================

def apply_hard_rules(
    result,
    hard_rule_result,
    language
):

    hard_rule_id = hard_rule_result.get(
        "rule_id"
    )


    if not hard_rule_id:

        return result


    result["decision"] = "NOT_ALLOWED"

    result["rule_id"] = hard_rule_id


    result = enforce_rule_consistency(
        result
    )


    if language == "English":

        if hard_rule_id == "3.1":

            result["reason"] = (
                "The review explicitly states that "
                "the product was found cheaper elsewhere."
            )

            result["comment"] = (
                "Not allowed: the review compares the product "
                "with a cheaper price elsewhere."
            )


        elif hard_rule_id == "3.2":

            result["reason"] = (
                "The review discusses product availability "
                "or stock status."
            )

            result["comment"] = (
                "Not allowed: the review refers to product "
                "availability or stock status."
            )


        elif hard_rule_id == "2.4":

            result["reason"] = (
                "The review reports product damage or "
                "a missing product, part, or accessory."
            )

            result["comment"] = (
                "Not allowed: the review reports product damage "
                "or a missing item, part, or accessory."
            )


    else:

        if hard_rule_id == "3.1":

            result["reason"] = (
                "التعليق يوضح أن المنتج تم العثور عليه "
                "بسعر أرخص في مكان آخر."
            )

            result["comment"] = (
                "غير مسموح: التعليق يقارن سعر المنتج "
                "بسعر أرخص في مكان آخر."
            )


        elif hard_rule_id == "3.2":

            result["reason"] = (
                "التعليق يتحدث عن توفر المنتج "
                "أو حالة المخزون."
            )

            result["comment"] = (
                "غير مسموح: التعليق يشير إلى توفر المنتج "
                "أو حالة المخزون."
            )


        elif hard_rule_id == "2.4":

            result["reason"] = (
                "التعليق يوضح وجود تلف في المنتج "
                "أو فقدان منتج أو جزء أو ملحق."
            )

            result["comment"] = (
                "غير مسموح: التعليق يوضح وجود تلف في المنتج "
                "أو فقدان منتج أو جزء أو ملحق."
            )


    return result


# ============================================================
# ALLOWED CLOSEST RULE
# ============================================================

def enforce_allowed_closest_rule(
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


    result = enforce_rule_consistency(
        result
    )


    if language == "English":

        if closest_rule == "2.4":

            result["reason"] = (
                "This is normal product feedback or criticism "
                "and does not report product damage or missing items."
            )

            result["comment"] = (
                "Allowed: this is a normal opinion about the product "
                "and does not contain a guideline violation."
            )


        elif closest_rule == "3.2":

            result["reason"] = (
                "The review expresses a general availability "
                "preference rather than reporting an actual stock issue."
            )

            result["comment"] = (
                "Allowed: this is a general product availability "
                "preference, not a stock-status complaint."
            )


        elif closest_rule == "3.1":

            result["reason"] = (
                "The review discusses product value without explicitly "
                "stating that the product was found cheaper elsewhere."
            )

            result["comment"] = (
                "Allowed: the review does not contain a prohibited "
                "competitor-price comparison."
            )


        else:

            result["reason"] = (
                "The review does not contain a guideline violation."
            )

            result["comment"] = (
                "Allowed: no guideline violation was identified."
            )


    else:

        if closest_rule == "2.4":

            result["reason"] = (
                "هذا تعليق أو انتقاد عادي للمنتج ولا يشير إلى "
                "وجود تلف في المنتج أو فقدان أجزاء أو منتجات."
            )

            result["comment"] = (
                "مسموح: التعليق يعبر عن رأي عادي في المنتج "
                "ولا يحتوي على مخالفة."
            )


        elif closest_rule == "3.2":

            result["reason"] = (
                "التعليق يعبر عن رغبة عامة تتعلق بتوفر المنتج "
                "ولا يشير إلى مشكلة فعلية في المخزون."
            )

            result["comment"] = (
                "مسموح: التعليق يعبر عن رغبة عامة تتعلق بتوفر المنتج."
            )


        elif closest_rule == "3.1":

            result["reason"] = (
                "التعليق يتحدث عن قيمة المنتج دون الإشارة إلى "
                "العثور عليه بسعر أرخص في مكان آخر."
            )

            result["comment"] = (
                "مسموح: التعليق لا يحتوي على مقارنة محظورة "
                "مع سعر منافس."
            )


        else:

            result["reason"] = (
                "التعليق لا يحتوي على مخالفة لإرشادات التقييم."
            )

            result["comment"] = (
                "مسموح: لم يتم تحديد أي مخالفة."
            )


    return result


# ============================================================
# FINAL SAFETY CHECK
# ============================================================

def final_safety_check(
    result,
    review,
    language
):

    result = enforce_rule_consistency(
        result
    )


    if result["rule_id"] not in RULES:

        result["rule_id"] = (
            get_closest_rule(review)
        )

        result = enforce_rule_consistency(
            result
        )


    if language == "Arabic":

        result = apply_arabic_labels(
            result
        )


    return result


# ============================================================
# CLEAN COMMENT
# ============================================================

def clean_comment(comment):

    if not comment:

        return ""


    comment = str(
        comment
    ).strip()


    greetings = [

        "hello seller",
        "hi seller",
        "dear seller",
        "greetings",
        "شريكنا العزيز",
        "تحية طيبة"
    ]


    for greeting in greetings:

        comment = re.sub(
            re.escape(greeting),
            "",
            comment,
            flags=re.IGNORECASE
        )


    comment = re.sub(
        r"\s+",
        " ",
        comment
    ).strip()


    return comment


# ============================================================
# MAIN EVALUATION
# ============================================================

def evaluate_review(
    review,
    language
):

    review = review.strip()


    if not review:

        raise ValueError(
            "Please enter a review."
        )


    # 1. Hard rules
    hard_rule_result = detect_hard_rules(
        review
    )


    # 2. First AI
    ai_result, used_model = (
        evaluate_with_reliability(
            review=review,
            language=language,
            hard_rule_result=hard_rule_result
        )
    )


    validate_result(
        ai_result
    )


    ai_result = enforce_rule_consistency(
        ai_result
    )


    # 3. Second AI quality check
    try:

        second_result = call_ai_adjudicator(
            model=used_model,
            review=review,
            language=language,
            first_result=ai_result
        )


        validate_result(
            second_result
        )


        ai_result = enforce_rule_consistency(
            second_result
        )


    except Exception:

        pass


    # 4. Hard rules always override AI
    ai_result = apply_hard_rules(
        result=ai_result,
        hard_rule_result=hard_rule_result,
        language=language
    )


    # 5. Allowed reviews get closest rule
    ai_result = enforce_allowed_closest_rule(
        result=ai_result,
        review=review,
        language=language
    )


    # 6. Final safety
    ai_result = final_safety_check(
        result=ai_result,
        review=review,
        language=language
    )


    # 7. Final validation
    validate_result(
        ai_result
    )


    ai_result["reason"] = clean_comment(
        ai_result["reason"]
    )

    ai_result["comment"] = clean_comment(
        ai_result["comment"]
    )


    return ai_result, used_model


# ============================================================
# ============================================================
# UI
# ============================================================
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

button_col1, button_col2, button_col3 = st.columns(
    [1.2, 0.8, 7]
)


with button_col1:

    evaluate_button = st.button(
        "Evaluate Review",
        type="primary",
        use_container_width=True
    )


with button_col2:

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

        st.markdown(
            """
            <div class="result-line">
                <strong>Decision:</strong>
                <span style="color:#21a366;">
                    ✓ Allowed
                </span>
                — the review can remain
            </div>
            """,
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            """
            <div class="result-line">
                <strong>Decision:</strong>
                <span style="color:#ff4b5c;">
                    ❌ Not allowed
                </span>
                — the review should be removed
            </div>
            """,
            unsafe_allow_html=True
        )


    # ========================================================
    # RULE ID
    # ========================================================

    st.markdown(
        f"""
        <div class="result-line">
            <strong>Rule ID:</strong>
            {result["rule_id"]}
        </div>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # MAIN GUIDELINE SECTION
    # ========================================================

    st.markdown(
        f"""
        <div class="result-line">
            <strong>Main Guideline Section:</strong>
            {result["section_number"]}.
            {result["section_title"]}
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
            Point {result["point_number"]}:
            {result["point_text"]}
        </div>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # REASON
    # ========================================================

    st.markdown(
        f"""
        <div class="result-line">
            <strong>Reason:</strong>
            {result["reason"]}
        </div>
        """,
        unsafe_allow_html=True
    )


    # ========================================================
    # COMMENT
    # ========================================================

    st.markdown(
        "### Comment:"
    )


    comment = clean_comment(
        result["comment"]
    )


    st.markdown(
        "**Generated Comment**"
    )


    st.text_area(
        "",
        value=comment,
        height=100,
        key="generated_comment",
        label_visibility="collapsed"
    )


    # ========================================================
    # COPY COMMENT
    # ========================================================

    escaped_comment = (
        comment
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
# GUIDELINES REFERENCE
# ============================================================

st.markdown("---")

st.markdown(
    "### Guidelines Reference"
)

st.markdown(
    "[Noon Customer Reviews Guidelines]"
    "(https://help.noon.com/portal/en/kb/articles/customer-reviews)"
)
