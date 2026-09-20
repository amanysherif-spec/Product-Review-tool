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
    layout="wide"
)


# ============================================================
# MODELS
# ============================================================

PRIMARY_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "openai/gpt-oss-20b"


# ============================================================
# GROQ CLIENT
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    st.error("GROQ_API_KEY is not configured.")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)


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
            "2": "Ordering or return experience",
            "3": "Shipping, packaging, or delivery speed",
            "4": "Product damage or missing items"
        }
    },

    "3": {
        "title": "Comments About Pricing or Availability",
        "points": {
            "1": "Finding the product cheaper elsewhere / competitor pricing",
            "2": "Stock status / out-of-stock / availability"
        }
    },

    "4": {
        "title": "Conflicts of Interest & Anti-Manipulation",
        "points": {
            "1": "Review written by seller, competitor, employee, friend, family member, or business partner",
            "2": "Review posted for compensation or financial incentive"
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
        "point_text": "Ordering or return experience"
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
        "point_text": "Finding the product cheaper elsewhere / competitor pricing"
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
        "point_text": "Review written by seller, competitor, employee, friend, family member, or business partner"
    },

    "4.2": {
        "section_number": "4",
        "section_title": "Conflicts of Interest & Anti-Manipulation",
        "point_number": "2",
        "point_text": "Review posted for compensation or financial incentive"
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
    "2.4": "تلف المنتج أو فقدان أجزاء / منتجات",

    "3.1": "العثور على المنتج بسعر أرخص في مكان آخر / أسعار المنافسين",
    "3.2": "حالة المخزون أو عدم توفر المنتج",

    "4.1": "التقييم من البائع أو المنافس أو الموظف أو أحد المعارف أو أفراد العائلة أو شريك تجاري",
    "4.2": "التقييم مقابل تعويض أو حافز مالي"
}


# ============================================================
# LANGUAGE
# ============================================================

def get_language_instruction(language):

    if language == "Arabic":
        return """
OUTPUT LANGUAGE:
- Return reason and comment in Arabic.
- Keep section and point names exactly according to the provided Arabic mapping.
- Do not add greetings.
- Do not add unnecessary explanation.
"""

    return """
OUTPUT LANGUAGE:
- Return reason and comment in English.
- Do not add greetings.
- Do not add unnecessary explanation.
"""


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = str(text).lower().strip()

    # Remove Arabic diacritics and tatweel
    text = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", text)

    # Normalize Arabic letters
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

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text


# ============================================================
# HELPER
# ============================================================

def contains_any(text, phrases):

    normalized = normalize_text(text)

    for phrase in phrases:
        if normalize_text(phrase) in normalized:
            return True

    return False


# ============================================================
# CLOSEST RULE
# ============================================================

def get_closest_rule(review):

    text = normalize_text(review)

    # --------------------------------------------------------
    # PRICE
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

    if any(normalize_text(x) in text for x in price_phrases):
        return "3.1"

    # --------------------------------------------------------
    # AVAILABILITY
    # --------------------------------------------------------

    availability_phrases = [
        "out of stock",
        "out-of-stock",
        "unavailable",
        "not available",
        "no stock",
        "no longer available",
        "when will it be available",

        "غير متوفر",
        "غير متاح",
        "خلص من المخزون",
        "نفد المخزون",
        "مفيش مخزون",
        "لا يوجد مخزون",
        "متى سيتوفر",
        "متى يتوفر"
    ]

    if any(normalize_text(x) in text for x in availability_phrases):
        return "3.2"

    # --------------------------------------------------------
    # SELLER
    # --------------------------------------------------------

    seller_phrases = [
        "seller",
        "seller was",
        "seller is",
        "seller service",
        "seller support",
        "seller attitude",
        "seller behavior",

        "البائع",
        "البايع",
        "تعامل البائع",
        "خدمة البائع",
        "تصرف البائع"
    ]

    if any(normalize_text(x) in text for x in seller_phrases):
        return "2.1"

    # --------------------------------------------------------
    # ORDER / RETURN
    # --------------------------------------------------------

    order_phrases = [
        "order",
        "ordered",
        "cancelled my order",
        "returned",
        "return",
        "refund",
        "refund experience",

        "الطلب",
        "طلبت",
        "الغاء الطلب",
        "إلغاء الطلب",
        "ارجاع",
        "إرجاع",
        "استرجاع",
        "استرداد"
    ]

    if any(normalize_text(x) in text for x in order_phrases):
        return "2.2"

    # --------------------------------------------------------
    # SHIPPING / DELIVERY
    # --------------------------------------------------------

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
        "التغليف",
        "الكرتونه",
        "الكرتونة",
        "المندوب"
    ]

    if any(normalize_text(x) in text for x in shipping_phrases):
        return "2.3"

    # --------------------------------------------------------
    # DAMAGE / MISSING
    # --------------------------------------------------------

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
        "مكسور عند الوصول",
        "جزء ناقص",
        "اجزاء ناقصه",
        "جزء مفقود",
        "اكسسوار ناقص",
        "اكسسوارات ناقصه"
    ]

    if any(normalize_text(x) in text for x in damage_missing_phrases):
        return "2.4"

    # --------------------------------------------------------
    # PROMOTIONAL
    # --------------------------------------------------------

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
        "best seller",
        "discount code",
        "promo code",

        "اشتروا مني",
        "تواصل معي",
        "تواصل معنا",
        "زوروا متجري",
        "واتساب",
        "كود خصم",
        "خصم"
    ]

    if any(normalize_text(x) in text for x in promotional_phrases):
        return "1.1"

    # --------------------------------------------------------
    # PERSONAL INFORMATION
    # --------------------------------------------------------

    personal_info_phrases = [
        "phone number",
        "mobile number",
        "email address",
        "email",
        "address",
        "credit card",
        "card number",
        "bank account",
        "password",
        "otp",

        "رقم الهاتف",
        "رقم الموبايل",
        "البريد الالكتروني",
        "الايميل",
        "العنوان",
        "رقم البطاقة",
        "رقم الحساب",
        "كلمة المرور",
        "رمز التحقق"
    ]

    if any(normalize_text(x) in text for x in personal_info_phrases):
        return "1.4"

    # --------------------------------------------------------
    # CONFLICT / COMPENSATION
    # --------------------------------------------------------

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

    if any(normalize_text(x) in text for x in conflict_phrases):
        return "4.1"

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

    if any(normalize_text(x) in text for x in compensation_phrases):
        return "4.2"

    # --------------------------------------------------------
    # DEFAULT
    # --------------------------------------------------------
    #
    # Important:
    # Generic product complaints such as:
    # "bad product"
    # "battery drains quickly"
    # "not useful"
    # "I don't like it"
    #
    # are closest to product-related feedback.
    #
    # This does NOT mean the review is a violation.
    # It is simply the closest available guideline.
    # --------------------------------------------------------

    return "2.4"


# ============================================================
# HARD RULE DETECTION
# ============================================================

def detect_hard_rules(review):

    text = normalize_text(review)

    result = {
        "rule_id": None,
        "reason": None
    }

    # --------------------------------------------------------
    # PRICE COMPARISON
    # --------------------------------------------------------

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

    if any(normalize_text(p) in text for p in price_patterns):

        result["rule_id"] = "3.1"
        result["reason"] = (
            "The review explicitly compares the product price with a cheaper price elsewhere."
        )

        return result

    # --------------------------------------------------------
    # AVAILABILITY
    # --------------------------------------------------------

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

    if any(normalize_text(p) in text for p in availability_patterns):

        result["rule_id"] = "3.2"
        result["reason"] = (
            "The review explicitly discusses product availability or stock status."
        )

        return result

    # --------------------------------------------------------
    # DAMAGE
    # --------------------------------------------------------

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

    if any(normalize_text(p) in text for p in damage_patterns):

        result["rule_id"] = "2.4"
        result["reason"] = (
            "The review explicitly reports that the product arrived damaged or physically broken."
        )

        return result

    # --------------------------------------------------------
    # MISSING ITEMS / PARTS
    # --------------------------------------------------------

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

    if any(normalize_text(p) in text for p in missing_patterns):

        result["rule_id"] = "2.4"
        result["reason"] = (
            "The review explicitly reports a missing product, part, or accessory."
        )

        return result

    return result


# ============================================================
# PROMPT
# ============================================================

def build_prompt(review, language, hard_rule_result):

    closest_rule = get_closest_rule(review)

    hard_rule_text = "NONE"

    if hard_rule_result.get("rule_id"):
        hard_rule_text = (
            f"HIGH-CONFIDENCE RULE DETECTED: "
            f"{hard_rule_result['rule_id']} - "
            f"{RULES[hard_rule_result['rule_id']]['point_text']}"
        )

    closest_rule_text = (
        f"{closest_rule} - {RULES[closest_rule]['point_text']}"
    )

    return f"""
You are a strict and highly accurate Noon product-review moderation classifier.

Your job is to classify ONE customer product review according to the provided Noon moderation guidelines.

IMPORTANT:
You must evaluate the meaning and context of the ENTIRE review.
Do NOT classify based on one isolated negative word.

============================================================
CORE PRINCIPLE
============================================================

A customer is allowed to express a negative opinion about the PRODUCT itself.

Examples that should normally remain ALLOWED:

- "The product is bad."
- "I don't like the product."
- "The quality is disappointing."
- "The battery drains quickly."
- "The battery is weak."
- "It is not useful."
- "The color is ugly."
- "The product does not work as expected."
- "I regret buying it."
- "The product is expensive."
- "I wish it came in more colors."

These are normal product opinions unless they contain a separate policy violation.

Do NOT classify ordinary product criticism as:
- offensive language
- seller feedback
- shipping feedback
- damage
- missing item

simply because the review is negative.

============================================================
OFFENSIVE / ABUSIVE / INAPPROPRIATE LANGUAGE
============================================================

You MUST carefully detect language that is genuinely offensive, abusive,
vulgar, insulting, obscene, or clearly inappropriate.

This includes both English and Arabic.

Examples that should be classified as NOT_ALLOWED under rule 1.2:

- "This product is disgusting."
- "The product is fucking useless."
- "This is fucking garbage."
- "The seller is an idiot."
- "The seller is disgusting."
- "المنتج مقرف"
- "المنتج زبالة"
- "البائع غبي ومقرف"

However, do NOT over-classify ordinary negative adjectives.

For example:

- "The product is bad." -> ALLOWED
- "The product is disappointing." -> ALLOWED
- "The battery is terrible." -> ALLOWED
- "The product is useless for me." -> ALLOWED unless the wording becomes clearly abusive/vulgar
- "I hate this product." -> normally ALLOWED as a product opinion

The important distinction is:
PRODUCT CRITICISM != OFFENSIVE LANGUAGE

But clearly vulgar, obscene, abusive, insulting, or distasteful wording
must be classified as rule 1.2.

Consider Arabic slang, spelling variations, repeated letters,
missing spaces, and informal writing.

============================================================
RULE 1 - COMMUNITY GUIDELINES
============================================================

1.1 Promotional / advertising:
Remove content that promotes a seller, business, product/service,
contact details, promotional code, or advertising activity.

1.2 Offensive / abusive / inappropriate:
Remove genuinely offensive, abusive, vulgar, obscene, insulting,
or clearly inappropriate/distasteful language.

1.3 Hate / discrimination:
Remove hate speech or discriminatory content targeting protected groups.

1.4 Personal / sensitive information:
Remove personal or sensitive information such as phone numbers,
email addresses, passwords, financial information, etc.

============================================================
RULE 2 - SELLER / ORDER / SHIPPING
============================================================

2.1 Seller performance/reputation:
Examples:
- seller was rude
- seller was dishonest
- seller service was bad

2.2 Ordering / return:
Examples:
- order was cancelled
- return was difficult
- refund problem

2.3 Shipping / packaging / delivery:
Examples:
- delivery was late
- courier was bad
- packaging was poor
- arrived after 10 days

2.4 Product damage / missing:
Examples:
- product arrived broken
- product was damaged
- missing accessory
- missing part

IMPORTANT:
Do NOT classify normal PRODUCT PERFORMANCE complaints as 2.3.

For example:
"The battery drains quickly"
is NOT shipping/delivery feedback.

It is normal product feedback and should be ALLOWED.

============================================================
RULE 3 - PRICE / AVAILABILITY
============================================================

3.1 Price comparison:
"Found it cheaper elsewhere"
must be NOT_ALLOWED.

Arabic examples:
- وجدته بسعر ارخص
- وجدته أرخص
- لقيته بسعر ارخص
- ارخص في مكان اخر
- نفس المنتج ارخص

3.2 Availability:
Comments specifically discussing stock availability are NOT_ALLOWED.

Examples:
- "It is out of stock again."
- "When will this be available?"
- "It is unavailable."

BUT:

"Hope it comes in more colors"
is NOT a stock-status violation and should remain ALLOWED.

============================================================
RULE 4 - CONFLICT OF INTEREST
============================================================

4.1:
Review created by seller, competitor, employee, friend,
family member, or business partner.

4.2:
Review posted in exchange for money, compensation,
free product, financial incentive, or another benefit.

============================================================
VERY IMPORTANT DECISION RULES
============================================================

1. If the review contains an obvious high-confidence policy violation,
classify NOT_ALLOWED.

2. If the review is simply a negative opinion about the product,
classify ALLOWED.

3. Do not confuse "bad product" with "offensive language".

4. Do not confuse "battery is bad" with shipping.

5. Do not confuse "expensive" with competitor price comparison.

6. "Found it cheaper elsewhere" is NOT_ALLOWED under 3.1.

7. "Hope it comes in more colors" is ALLOWED.

8. Damage and missing-item statements are NOT_ALLOWED under 2.4.

9. Seller-related complaints are NOT_ALLOWED under 2.1.

10. Shipping/delivery complaints are NOT_ALLOWED under 2.3.

11. Product quality/performance complaints without another violation
are ALLOWED.

12. Never invent a violation.

============================================================
ALLOWED REVIEWS - RULE ID
============================================================

For an ALLOWED review, you MUST still provide one of the existing rule IDs.

Do NOT use:
- NONE
- N/A
- No
- Unknown

The rule ID for an ALLOWED review should represent the CLOSEST
relevant guideline category, not a violation.

A generic product complaint can use 2.4 as the closest available category,
but explicitly explain that the review does NOT report damage or missing items.

Closest-rule reference:
{closest_rule_text}

============================================================
HIGH-CONFIDENCE DETECTOR
============================================================

{hard_rule_text}

If a high-confidence detector is provided above, follow it unless
the actual review clearly proves the detector is not applicable.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON according to the provided schema.

Do not add markdown.
Do not add comments outside JSON.
Do not add greetings.

Review:
{review}

{get_language_instruction(language)}
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
# MODEL CALL
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
                    "You are a highly accurate policy classification "
                    "engine. Follow the supplied policy exactly."
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
        raise ValueError("Empty model response.")

    return json.loads(content)


# ============================================================
# AI RELIABILITY
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

                # Do not keep retrying a model that does not exist.
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
# AI SECOND REVIEW / ADJUDICATOR
# ============================================================

def call_ai_adjudicator(
    model,
    review,
    language,
    first_result
):

    adjudication_prompt = f"""
You are the FINAL QUALITY-CONTROL reviewer for a product review
moderation decision.

Review the original customer review and the first AI classification.

Your task is to correct the first classification if necessary.

Pay special attention to:

1. Offensive / abusive / vulgar / inappropriate language.
2. Arabic offensive language and slang.
3. The difference between ordinary product criticism and offensive language.
4. Seller complaints.
5. Shipping complaints.
6. Damage or missing items.
7. "Found it cheaper elsewhere" -> 3.1 NOT_ALLOWED.
8. Stock/availability complaints -> 3.2 NOT_ALLOWED.
9. "Hope it comes in more colors" -> ALLOWED.
10. Product performance complaints such as battery problems -> normally ALLOWED.
11. Generic negative product opinions -> normally ALLOWED.
12. Never invent a violation.

IMPORTANT OFFENSIVE-LANGUAGE DISTINCTION:

"The product is bad." -> ALLOWED
"The product is disappointing." -> ALLOWED
"The battery is terrible." -> ALLOWED
"I don't like it." -> ALLOWED

"The product is disgusting." -> NOT_ALLOWED 1.2
"المنتج مقرف" -> NOT_ALLOWED 1.2
"المنتج زبالة" -> NOT_ALLOWED 1.2
"البائع غبي ومقرف" -> NOT_ALLOWED 1.2

Do not remove a review merely because it is strongly negative.
Remove it when the actual wording falls under the policy.

============================================================
ORIGINAL REVIEW
============================================================

{review}

============================================================
FIRST AI RESULT
============================================================

{json.dumps(first_result, ensure_ascii=False, indent=2)}

============================================================
TASK
============================================================

Return the corrected final result as JSON only.

The rule_id MUST be one of:

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

For ALLOWED reviews, use the closest existing rule.
Never use NONE or N/A.

{get_language_instruction(language)}
"""

    response = client.chat.completions.create(

        model=model,

        messages=[
            {
                "role": "system",
                "content": (
                    "You are the final independent quality-control "
                    "reviewer for policy classification."
                )
            },
            {
                "role": "user",
                "content": adjudication_prompt
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
        raise ValueError("Empty adjudicator response.")

    return json.loads(content)


# ============================================================
# VALIDATION
# ============================================================

def validate_result(result):

    if not isinstance(result, dict):
        raise ValueError("AI result is not a dictionary.")

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
        raise ValueError("Invalid decision.")

    if result["rule_id"] not in RULES:
        raise ValueError(
            f"Invalid rule_id: {result['rule_id']}"
        )

    if not str(result["reason"]).strip():
        raise ValueError("Empty reason.")

    if not str(result["comment"]).strip():
        raise ValueError("Empty comment.")

    # Prevent NONE/N/A values
    forbidden_values = [
        "",
        "none",
        "n/a",
        "na",
        "no",
        "unknown"
    ]

    for field in [
        "section_number",
        "section_title",
        "point_number",
        "point_text"
    ]:

        value = str(result[field]).strip().lower()

        if value in forbidden_values:
            raise ValueError(
                f"Invalid empty guideline value in {field}"
            )

    return True


# ============================================================
# ENFORCE CANONICAL RULE
# ============================================================

def enforce_rule_consistency(result):

    rule_id = result["rule_id"]

    rule = RULES[rule_id]

    result["section_number"] = rule["section_number"]
    result["section_title"] = rule["section_title"]
    result["point_number"] = rule["point_number"]
    result["point_text"] = rule["point_text"]

    return result


# ============================================================
# ARABIC RULE DISPLAY
# ============================================================

def apply_arabic_labels(result):

    rule_id = result["rule_id"]

    if rule_id in ARABIC_POINTS:

        result["section_title"] = ARABIC_SECTIONS[
            RULES[rule_id]["section_number"]
        ]

        result["point_text"] = ARABIC_POINTS[rule_id]

    return result


# ============================================================
# HARD RULE OVERRIDE
# ============================================================

def apply_hard_rules(
    result,
    hard_rule_result,
    language
):

    hard_rule_id = hard_rule_result.get("rule_id")

    if not hard_rule_id:
        return result

    result["decision"] = "NOT_ALLOWED"
    result["rule_id"] = hard_rule_id

    result = enforce_rule_consistency(result)

    # --------------------------------------------------------
    # ENGLISH
    # --------------------------------------------------------

    if language == "English":

        if hard_rule_id == "3.1":

            result["reason"] = (
                "The review states that the product was found at a "
                "cheaper price elsewhere, which is not allowed under "
                "the pricing guideline."
            )

            result["comment"] = (
                "Not allowed: the review compares the product price "
                "with a cheaper price elsewhere."
            )

        elif hard_rule_id == "3.2":

            result["reason"] = (
                "The review discusses product stock or availability, "
                "which is not allowed under the availability guideline."
            )

            result["comment"] = (
                "Not allowed: the review refers to product availability "
                "or stock status."
            )

        elif hard_rule_id == "2.4":

            result["reason"] = (
                "The review reports product damage or a missing item, "
                "part, or accessory."
            )

            result["comment"] = (
                "Not allowed: the review reports product damage "
                "or a missing item, part, or accessory."
            )

    # --------------------------------------------------------
    # ARABIC
    # --------------------------------------------------------

    else:

        if hard_rule_id == "3.1":

            result["reason"] = (
                "التعليق يوضح أن المنتج تم العثور عليه بسعر أرخص في "
                "مكان آخر، وهو محتوى غير مسموح به وفقًا لإرشادات الأسعار."
            )

            result["comment"] = (
                "غير مسموح: التعليق يقارن سعر المنتج بسعر أرخص في مكان آخر."
            )

        elif hard_rule_id == "3.2":

            result["reason"] = (
                "التعليق يتحدث عن توفر المنتج أو حالة المخزون، "
                "وهو محتوى غير مسموح به وفقًا لإرشادات التوفر."
            )

            result["comment"] = (
                "غير مسموح: التعليق يشير إلى توفر المنتج أو حالة المخزون."
            )

        elif hard_rule_id == "2.4":

            result["reason"] = (
                "التعليق يوضح وجود تلف في المنتج أو فقدان منتج أو جزء "
                "أو ملحق."
            )

            result["comment"] = (
                "غير مسموح: التعليق يوضح وجود تلف في المنتج أو فقدان "
                "منتج أو جزء أو ملحق."
            )

    return result


# ============================================================
# ALLOWED RULE NORMALIZATION
# ============================================================

def enforce_allowed_closest_rule(
    result,
    review,
    language
):

    if result["decision"] != "ALLOWED":
        return result

    closest_rule = get_closest_rule(review)

    result["rule_id"] = closest_rule

    result = enforce_rule_consistency(result)

    # --------------------------------------------------------
    # ENGLISH
    # --------------------------------------------------------

    if language == "English":

        if closest_rule == "2.4":

            result["reason"] = (
                "This is normal product feedback or criticism and does "
                "not report product damage or missing items. Therefore, "
                "the review remains allowed."
            )

            result["comment"] = (
                "Allowed: this is a normal opinion about the product "
                "and does not contain a guideline violation."
            )

        elif closest_rule == "3.2":

            result["reason"] = (
                "The review expresses a general availability preference "
                "rather than reporting an actual stock-status issue."
            )

            result["comment"] = (
                "Allowed: this is a general product availability preference, "
                "not a stock-status complaint."
            )

        elif closest_rule == "3.1":

            result["reason"] = (
                "The review discusses product value without explicitly "
                "stating that the same product was found cheaper elsewhere."
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

    # --------------------------------------------------------
    # ARABIC
    # --------------------------------------------------------

    else:

        if closest_rule == "2.4":

            result["reason"] = (
                "هذا تعليق أو انتقاد عادي للمنتج ولا يشير إلى وجود تلف "
                "في المنتج أو فقدان أجزاء أو منتجات، لذلك يظل التعليق مسموحًا."
            )

            result["comment"] = (
                "مسموح: التعليق يعبر عن رأي عادي في المنتج ولا يحتوي "
                "على مخالفة لإرشادات التقييم."
            )

        elif closest_rule == "3.2":

            result["reason"] = (
                "التعليق يعبر عن رغبة عامة تتعلق بتوفر المنتج ولا يشير "
                "إلى مشكلة فعلية في حالة المخزون."
            )

            result["comment"] = (
                "مسموح: التعليق يعبر عن رغبة عامة تتعلق بتوفر المنتج "
                "ولا يمثل شكوى بشأن حالة المخزون."
            )

        elif closest_rule == "3.1":

            result["reason"] = (
                "التعليق يتحدث عن قيمة المنتج دون الإشارة بشكل واضح "
                "إلى العثور على نفس المنتج بسعر أرخص في مكان آخر."
            )

            result["comment"] = (
                "مسموح: التعليق لا يحتوي على مقارنة محظورة مع سعر منافس."
            )

        else:

            result["reason"] = (
                "التعليق لا يحتوي على مخالفة لإرشادات التقييم."
            )

            result["comment"] = (
                "مسموح: لم يتم تحديد أي مخالفة لإرشادات التقييم."
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

    # --------------------------------------------------------
    # Ensure canonical fields
    # --------------------------------------------------------

    result = enforce_rule_consistency(result)

    # --------------------------------------------------------
    # Prevent invalid rule values
    # --------------------------------------------------------

    if result["rule_id"] not in RULES:

        result["rule_id"] = get_closest_rule(review)

        result = enforce_rule_consistency(result)

    # --------------------------------------------------------
    # Ensure non-empty fields
    # --------------------------------------------------------

    for field in [
        "reason",
        "comment"
    ]:

        if not str(result.get(field, "")).strip():

            if language == "English":

                result[field] = (
                    "The review was evaluated according to the "
                    "provided moderation guidelines."
                )

            else:

                result[field] = (
                    "تم تقييم التعليق وفقًا لإرشادات التقييم المحددة."
                )

    # --------------------------------------------------------
    # Remove accidental forbidden output
    # --------------------------------------------------------

    forbidden = [
        "none",
        "n/a",
        "not applicable",
        "no violation",
        "لا يوجد",
        "غير محدد"
    ]

    for field in [
        "section_title",
        "point_text",
        "reason",
        "comment"
    ]:

        value = str(result[field]).strip().lower()

        if value in forbidden:

            if result["decision"] == "ALLOWED":

                result = enforce_allowed_closest_rule(
                    result,
                    review,
                    language
                )

            else:

                if language == "English":
                    result[field] = (
                        "The review was identified as violating the "
                        "specified guideline."
                    )
                else:
                    result[field] = (
                        "تم تحديد أن التعليق يخالف الإرشادات المحددة."
                    )

    # --------------------------------------------------------
    # Arabic labels
    # --------------------------------------------------------

    if language == "Arabic":

        result = apply_arabic_labels(result)

    return result


# ============================================================
# SEMANTIC CONSISTENCY CHECK
# ============================================================

def semantic_cleanup(
    result,
    review,
    language
):

    decision = result["decision"]

    reason = str(result["reason"]).lower()
    comment = str(result["comment"]).lower()

    # --------------------------------------------------------
    # ALLOWED should not contain contradictory violation language
    # --------------------------------------------------------

    if decision == "ALLOWED":

        contradiction_terms = [
            "not allowed",
            "remove this review",
            "violation",
            "must be removed",
            "غير مسموح",
            "يجب حذف",
            "مخالفة",
            "يحذف"
        ]

        if any(term in reason or term in comment for term in contradiction_terms):

            result = enforce_allowed_closest_rule(
                result,
                review,
                language
            )

    return result


# ============================================================
# COMPLETE EVALUATION
# ============================================================

def evaluate_review(
    review,
    language
):

    review = review.strip()

    if not review:
        raise ValueError("Please enter a review.")

    # --------------------------------------------------------
    # STEP 1
    # Deterministic high-confidence checks
    # --------------------------------------------------------

    hard_rule_result = detect_hard_rules(review)

    # --------------------------------------------------------
    # STEP 2
    # First AI classification
    # --------------------------------------------------------

    ai_result, used_model = evaluate_with_reliability(
        review=review,
        language=language,
        hard_rule_result=hard_rule_result
    )

    validate_result(ai_result)

    ai_result = enforce_rule_consistency(ai_result)

    # --------------------------------------------------------
    # STEP 3
    # Second AI quality-control pass
    # --------------------------------------------------------

    try:

        adjudicated_result = call_ai_adjudicator(
            model=used_model,
            review=review,
            language=language,
            first_result=ai_result
        )

        validate_result(adjudicated_result)

        adjudicated_result = enforce_rule_consistency(
            adjudicated_result
        )

        ai_result = adjudicated_result

    except Exception:

        # If second AI review fails, keep the first valid result.
        pass

    # --------------------------------------------------------
    # STEP 4
    # Hard rules ALWAYS override AI when unambiguous
    # --------------------------------------------------------

    ai_result = apply_hard_rules(
        result=ai_result,
        hard_rule_result=hard_rule_result,
        language=language
    )

    # --------------------------------------------------------
    # STEP 5
    # For allowed reviews, use closest valid guideline
    # --------------------------------------------------------

    ai_result = enforce_allowed_closest_rule(
        result=ai_result,
        review=review,
        language=language
    )

    # --------------------------------------------------------
    # STEP 6
    # Semantic cleanup
    # --------------------------------------------------------

    ai_result = semantic_cleanup(
        result=ai_result,
        review=review,
        language=language
    )

    # --------------------------------------------------------
    # STEP 7
    # Final safety
    # --------------------------------------------------------

    ai_result = final_safety_check(
        result=ai_result,
        review=review,
        language=language
    )

    # --------------------------------------------------------
    # STEP 8
    # Final validation
    # --------------------------------------------------------

    validate_result(ai_result)

    return ai_result, used_model


# ============================================================
# COMMENT CLEANUP
# ============================================================

def clean_comment(comment):

    if not comment:
        return ""

    comment = str(comment).strip()

    # Remove accidental greetings
    greetings = [
        "hello seller",
        "hi seller",
        "dear seller",
        "greetings",
        "شريكنا العزيز",
        "تحية طيبة"
    ]

    for greeting in greetings:

        pattern = re.compile(
            re.escape(greeting),
            re.IGNORECASE
        )

        comment = pattern.sub("", comment)

    comment = re.sub(
        r"\s+",
        " ",
        comment
    ).strip()

    return comment


# ============================================================
# FORMAT RESULT
# ============================================================

def format_result(result):

    result["reason"] = clean_comment(
        result["reason"]
    )

    result["comment"] = clean_comment(
        result["comment"]
    )

    return result


# ============================================================
# EXTRACT COMMENT
# ============================================================

def extract_comment(result):

    return clean_comment(
        result.get("comment", "")
    )


# ============================================================
# UI CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 34px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .sub-title {
        color: #666;
        font-size: 16px;
        margin-bottom: 25px;
    }

    .result-box {
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #ddd;
        margin-top: 15px;
    }

    .allowed {
        color: #1a7f37;
        font-weight: 700;
        font-size: 22px;
    }

    .not-allowed {
        color: #d1242f;
        font-weight: 700;
        font-size: 22px;
    }

    .copy-box {
        background: #f7f7f7;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #ddd;
        margin-top: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🛡️ Product Review Moderation Tool</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">'
    'AI-powered Noon product review moderation'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# LANGUAGE
# ============================================================

language = st.radio(
    "Output Language",
    [
        "English",
        "Arabic"
    ],
    horizontal=True
)


# ============================================================
# REVIEW INPUT
# ============================================================

review_text = st.text_area(
    "Customer Review",
    height=180,
    placeholder=(
        "Enter the customer review here..."
        if language == "English"
        else
        "أدخل تعليق العميل هنا..."
    )
)


# ============================================================
# BUTTONS
# ============================================================

col1, col2 = st.columns(2)

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

    st.rerun()


# ============================================================
# EVALUATE
# ============================================================

if evaluate_button:

    if not review_text.strip():

        if language == "English":

            st.warning(
                "Please enter a customer review."
            )

        else:

            st.warning(
                "يرجى إدخال تعليق العميل."
            )

    else:

        with st.spinner(
            "Analyzing review..." if language == "English"
            else
            "جاري تحليل التعليق..."
        ):

            try:

                result, used_model = evaluate_review(
                    review=review_text,
                    language=language
                )

                result = format_result(result)

                st.session_state["moderation_result"] = result
                st.session_state["used_model"] = used_model

            except Exception as e:

                st.error(
                    f"Evaluation failed: {str(e)}"
                )


# ============================================================
# DISPLAY RESULT
# ============================================================

if "moderation_result" in st.session_state:

    result = st.session_state["moderation_result"]
    used_model = st.session_state.get(
        "used_model",
        PRIMARY_MODEL
    )

    st.markdown("---")

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    if result["decision"] == "ALLOWED":

        st.markdown(
            '<div class="allowed">✓ ALLOWED</div>',
            unsafe_allow_html=True
        )

    else:

        st.markdown(
            '<div class="not-allowed">✕ NOT ALLOWED</div>',
            unsafe_allow_html=True
        )

    # --------------------------------------------------------
    # GUIDELINE DETAILS
    # --------------------------------------------------------

    st.markdown("### Guideline")

    col1, col2 = st.columns(2)

    with col1:

        st.write(
            f"**Section:** "
            f"{result['section_number']} - "
            f"{result['section_title']}"
        )

    with col2:

        st.write(
            f"**Point:** "
            f"{result['point_number']} - "
            f"{result['point_text']}"
        )

    # --------------------------------------------------------
    # REASON
    # --------------------------------------------------------

    st.markdown("### Reason")

    st.info(
        result["reason"]
    )

    # --------------------------------------------------------
    # COMMENT
    # --------------------------------------------------------

    st.markdown("### Comment")

    comment = extract_comment(result)

    st.text_area(
        "Generated Comment",
        value=comment,
        height=130,
        key="generated_comment"
    )

    # --------------------------------------------------------
    # COPY BUTTON
    # --------------------------------------------------------

    escaped_comment = (
        comment
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("$", "\\$")
    )

    components.html(
        f"""
        <button
            onclick="navigator.clipboard.writeText(`{escaped_comment}`)"
            style="
                padding:10px 18px;
                border:none;
                border-radius:8px;
                cursor:pointer;
                font-size:14px;
            "
        >
            📋 Copy Comment
        </button>
        """,
        height=50
    )

    # --------------------------------------------------------
    # MODEL
    # --------------------------------------------------------

    with st.expander("Technical Details"):

        st.write(
            f"Model used: `{used_model}`"
        )

        st.write(
            f"Rule ID: `{result['rule_id']}`"
        )

        st.write(
            f"Decision: `{result['decision']}`"
        )


# ============================================================
# GUIDELINES LINK
# ============================================================

st.markdown("---")

st.markdown(
    """
    **Noon Review Guidelines**

    Please always refer to the official Noon guidelines when needed.
    """
)

st.markdown(
    "[Open Noon Guidelines](https://help.noon.com/portal/en/kb/articles/"
    "customer-reviews)"
)
