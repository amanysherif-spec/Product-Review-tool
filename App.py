import streamlit as st
import os
import streamlit.components.v1 as components
import json
import re
import time
import requests
from html.parser import HTMLParser
from openai import OpenAI


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Product Review Moderation Tool",
    page_icon="🛡️",
    layout="centered"
)


# ============================================================
# MODELS
# ============================================================

PRIMARY_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "google/gemini-3.8-flash"

ARTICLE_URL = "https://help.noon.com/portal/en/kb/articles/product-review-guidelines"


# ============================================================
# NOON CUSTOMER REVIEW GUIDELINES
# ============================================================

# The full policy text is NOT hard-coded here. The tool fetches the
# official Noon article below and uses it as the policy source of truth.
# This small map is kept only for the result display / JSON validation.
RULES = {
    "1.1": {"section": "Community Guideline Violations", "rule": "Promotional or advertising content"},
    "1.2": {"section": "Community Guideline Violations", "rule": "Offensive, abusive, or illegal language"},
    "1.3": {"section": "Community Guideline Violations", "rule": "Hate speech or discriminatory remarks"},
    "1.4": {"section": "Community Guideline Violations", "rule": "Personal or sensitive information"},
    "2.1": {"section": "Seller, Order, or Shipping Feedback", "rule": "Seller performance or reputation"},
    "2.2": {"section": "Seller, Order, or Shipping Feedback", "rule": "Ordering or return experiences"},
    "2.3": {"section": "Seller, Order, or Shipping Feedback", "rule": "Shipping, packaging, or delivery speed"},
    "2.4": {"section": "Seller, Order, or Shipping Feedback", "rule": "Product damage or missing items"},
    "3.1": {"section": "Comments About Pricing or Availability", "rule": "Finding the product cheaper elsewhere"},
    "3.2": {"section": "Comments About Pricing or Availability", "rule": "Stock status or availability"},
    "4.1": {"section": "Conflicts of Interest & Anti-Manipulation", "rule": "Conflict of interest"},
    "4.2": {"section": "Conflicts of Interest & Anti-Manipulation", "rule": "Compensation or financial incentive"},
}


# ============================================================
# LIVE NOON ARTICLE LOADER
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_noon_guidelines():
    """
    Load the official Noon Product Review Guidelines.

    Direct access is tried first. Some hosting environments may receive a
    protected/empty HTML response from the Noon help center, so a text-reader
    fallback is used only when direct access cannot be parsed. The policy
    itself still comes from the official Noon article URL.
    """

    urls = [
        ARTICLE_URL,
        f"https://r.jina.ai/{ARTICLE_URL}",
    ]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/154.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    errors = []

    for url in urls:
        try:
            response = requests.get(
                url,
                timeout=15,
                headers=headers,
                allow_redirects=True,
            )
            response.raise_for_status()

            raw = response.text or ""

            # Jina returns clean text. For the direct Noon HTML response,
            # strip tags without depending on BeautifulSoup.
            if "r.jina.ai/" in url:
                text = raw
            else:
                raw = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
                raw = re.sub(r"<style[^>]*>.*?</style>", " ", raw, flags=re.I | re.S)
                raw = re.sub(r"<noscript[^>]*>.*?</noscript>", " ", raw, flags=re.I | re.S)
                raw = re.sub(r"<[^>]+>", " ", raw)
                text = raw

            # Decode common HTML entities and normalize whitespace.
            import html as _html
            text = _html.unescape(text)
            text = re.sub(r"\s+", " ", text).strip()

            required_markers = [
                "Product Review Guidelines",
                "Seller, Order, or Shipping Feedback",
                "Comments About Pricing or Availability",
                "Conflicts of Interest",
            ]

            if len(text) >= 1000 and all(marker.lower() in text.lower() for marker in required_markers):
                return text[:50000]

            errors.append(f"Invalid policy content from {url}")

        except Exception as exc:
            errors.append(f"{url}: {exc}")

    raise RuntimeError(
        "The Noon Product Review Guidelines could not be loaded. "
        "Please try again. The tool will not classify a review without "
        "a valid copy of the official policy."
    )


# ============================================================
# ARABIC TRANSLATIONS
# ============================================================

ARABIC_SECTIONS = {
    "Community Guideline Violations":
        "مخالفات إرشادات المجتمع",

    "Seller, Order, or Shipping Feedback":
        "التعليقات المتعلقة بالبائع أو الطلب أو الشحن",

    "Comments About Pricing or Availability":
        "التعليقات المتعلقة بالسعر أو التوفر",

    "Conflicts of Interest & Anti-Manipulation":
        "تعارض المصالح والتلاعب بالتقييمات",
}


ARABIC_RULES = {
    "1.1":
        "المحتوى الترويجي أو الإعلاني",

    "1.2":
        "الألفاظ المسيئة أو غير اللائقة أو المبتذلة أو غير المناسبة",

    "1.3":
        "خطاب الكراهية أو المحتوى التمييزي",

    "1.4":
        "المعلومات الشخصية أو الحساسة",

    "2.1":
        "أداء البائع أو سمعته",

    "2.2":
        "تجربة الطلب أو الإرجاع",

    "2.3":
        "الشحن أو التغليف أو التوصيل",

    "2.4":
        "تلف المنتج أو وجود أجزاء مفقودة",

    "3.1":
        "العثور على المنتج بسعر أرخص في مكان آخر",

    "3.2":
        "حالة المخزون أو توفر المنتج",

    "4.1":
        "تعارض المصالح",

    "4.2":
        "الحصول على مقابل أو حافز مالي",
}


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):
    if not text:
        return ""

    text = str(text).strip().lower()

    # Remove Arabic diacritics and Tatweel
    text = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", text)

    # Normalize Arabic characters
    text = text.translate(
        str.maketrans({
            "أ": "ا",
            "إ": "ا",
            "آ": "ا",
            "ٱ": "ا",
            "ى": "ي",
            "ة": "ه",
        })
    )

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text


def contains_phrase(text, phrases):
    normalized = normalize_text(text)

    for phrase in phrases:
        phrase_normalized = normalize_text(phrase)

        if phrase_normalized and phrase_normalized in normalized:
            return True

    return False


# ============================================================
# HARD RULE DETECTION
# ============================================================

def detect_hard_rules(review):
    """
    Deterministic rules for violations that must never be
    overridden by the AI.
    """

    text = normalize_text(review)

    # --------------------------------------------------------
    # 3.1 PRICE / CHEAPER ELSEWHERE
    # --------------------------------------------------------

    price_phrases = [
        "found it cheaper elsewhere",
        "found it cheaper",
        "cheaper elsewhere",
        "cheaper in another store",
        "cheaper at another store",
        "lower price elsewhere",
        "lower price in another store",
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
    ]

    if contains_phrase(text, price_phrases):
        return "3.1"


    # --------------------------------------------------------
    # 3.2 AVAILABILITY / STOCK
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
        "متى يرجع للمخزون",
    ]

    if contains_phrase(text, availability_phrases):
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
        "وصل تالف",
    ]

    if contains_phrase(text, damage_phrases):
        return "2.4"


    # --------------------------------------------------------
    # 2.4 MISSING ITEM / PART
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
        "شي ناقص",
    ]

    if contains_phrase(text, missing_phrases):
        return "2.4"


    return None


# ============================================================
# HIGH CONFIDENCE OFFENSIVE LANGUAGE DETECTION
# ============================================================

def detect_clear_offensive_language(review):
    """
    Deterministic safety layer for Rule 1.2.

    The Article says offensive, abusive, inappropriate, vulgar, or
    distasteful language is not allowed.  This layer intentionally
    catches clear offensive terms even when the AI might otherwise
    interpret them as ordinary product criticism.

    Normal criticism such as "bad", "poor quality", "not useful",
    "I don't like it", "سيء", and "جودته ضعيفة" is NOT included.
    """

    text = normalize_text(review)

    offensive_phrases = [

        # ----------------------------------------------------
        # ENGLISH - HIGH CONFIDENCE
        # ----------------------------------------------------

        # Explicitly prohibited / distasteful terms requested for
        # Article compliance, including single-word usage.
        "disgusting",
        "disgusted",
        "gross",
        "vulgar",
        "fuck",
        "fucking",
        "shit",
        "bullshit",
        "asshole",
        "bastard",
        "idiot",
        "stupid",
        "moron",
        "damn",

        "fucking garbage",
        "fucking shit",
        "piece of shit",
        "shit product",
        "shit item",
        "bullshit",
        "fuck this",
        "fuck you",
        "fucked up",

        "damn this product",

        "disgusting product",
        "this product is disgusting",
        "the product is disgusting",
        "what a disgusting product",
        "disgusting item",

        # ----------------------------------------------------
        # ARABIC - HIGH CONFIDENCE
        # ----------------------------------------------------

        # Clear vulgar / insulting / distasteful terms.
        "مقرف",
        "قرف",
        "زباله",
        "زفت",
        "وسخ",
        "خرا",
        "غبي",
        "احمق",
        "اهبل",
        "تافه",
        "حقير",
        "قذر",
        "سخيف",

        "المنتج مقرف",
        "منتج مقرف",
        "مقرف جدا",
        "مقرف اوي",

        "المنتج زباله",
        "المنتج زبالة",
        "منتج زباله",
        "منتج زبالة",

        "يا غبي",
        "غبي جدا",
        "البائع غبي",

        "خرا",
        "زفت",
        "وسخ",
        "وسخه",
        "وسخة",
    ]

    for phrase in offensive_phrases:
        normalized_phrase = normalize_text(phrase)
        if not normalized_phrase:
            continue

        # Single terms are matched as words so a term cannot be found
        # accidentally inside an unrelated longer word.
        if " " not in normalized_phrase:
            if re.search(r"(?<![\w])" + re.escape(normalized_phrase) + r"(?![\w])", text):
                return True
        elif normalized_phrase in text:
            return True

    return False


# ============================================================
# HIGH-CONFIDENCE ARTICLE RULE DETECTION
# ============================================================

def detect_high_confidence_article_rule(review):
    """
    Deterministic checks for additional high-confidence Article violations.

    These checks intentionally use strong contextual phrases instead of
    single generic words, because ordinary product reviews can mention
    words such as "order", "price", or "seller" without necessarily
    describing a prohibited experience.
    """

    text = normalize_text(review)

    # --------------------------------------------------------
    # 1.1 PROMOTIONAL / ADVERTISING CONTENT
    # --------------------------------------------------------
    promotional_phrases = [
        "use my promo code",
        "use my promo code",
        "use my discount code",
        "use this discount code",
        "use this promo code",
        "promo code",
        "discount code",
        "coupon code",
        "coupon link",
        "buy from my store",
        "buy from our store",
        "visit my store",
        "visit our store",
        "contact me for a discount",
        "contact me to buy",
        "dm me to buy",
        "message me to buy",
        "whatsapp me to buy",
        "اتواصل معي للشراء",
        "تواصل معي للشراء",
        "استخدم كود الخصم",
        "كود خصم",
        "كود تخفيض",
        "اشتروا من متجري",
        "اشتري من متجري",
        "تواصل معي للشراء",
    ]

    if contains_phrase(text, promotional_phrases):
        return "1.1"

    # Explicit external promotional/social links or handles.
    if re.search(r"https?://|www\.|@[a-z0-9_.-]{3,}", text):
        return "1.1"

    # --------------------------------------------------------
    # 1.4 PERSONAL / SENSITIVE INFORMATION
    # --------------------------------------------------------
    # High-confidence email address.
    if re.search(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", text):
        return "1.4"

    personal_info_phrases = [
        "my phone number is",
        "my mobile number is",
        "my email is",
        "my address is",
        "call me at",
        "contact me at",
        "رقم موبايلي",
        "رقم تليفوني",
        "رقم هاتفي",
        "ايميلي هو",
        "بريدي الالكتروني",
        "عنواني هو",
        "كلمني على الرقم",
        "تواصل معي على الرقم",
    ]

    if contains_phrase(text, personal_info_phrases):
        return "1.4"

    # --------------------------------------------------------
    # 4.2 COMPENSATION / FINANCIAL INCENTIVE
    # --------------------------------------------------------
    incentive_phrases = [
        "paid to review",
        "paid for this review",
        "paid for my review",
        "got paid to review",
        "received money for this review",
        "received money to review",
        "given money to review",
        "given a free product for review",
        "received a free product for review",
        "free product in exchange for a review",
        "free item in exchange for a review",
        "compensated for this review",
        "compensated to review",
        "in exchange for a positive review",
        "in exchange for a good review",
        "تم الدفع لي مقابل التقييم",
        "اخذت فلوس مقابل التقييم",
        "اخذت مال مقابل التقييم",
        "حصلت على منتج مجاني مقابل التقييم",
        "منتج مجاني مقابل التقييم",
        "مقابل تقييم ايجابي",
        "مقابل تقييم جيد",
    ]

    if contains_phrase(text, incentive_phrases):
        return "4.2"

    # --------------------------------------------------------
    # 4.1 CONFLICT OF INTEREST / MANIPULATION
    # --------------------------------------------------------
    conflict_phrases = [
        "i am the seller",
        "i'm the seller",
        "i work for the seller",
        "i work for noon",
        "i am a noon employee",
        "i'm a noon employee",
        "i am the manufacturer",
        "i'm the manufacturer",
        "i am the brand owner",
        "i'm the brand owner",
        "i am the competitor",
        "i work for a competitor",
        "my friend is the seller",
        "my family member is the seller",
        "my relative is the seller",
        "انا البائع",
        "انا موظف في نون",
        "انا من شركة نون",
        "انا صاحب البراند",
        "انا صاحب العلامة التجارية",
        "انا من المنافسين",
        "البائع صديقي",
        "البائع قريبي",
    ]

    if contains_phrase(text, conflict_phrases):
        return "4.1"

    # --------------------------------------------------------
    # 2.1 SELLER PERFORMANCE / REPUTATION
    # --------------------------------------------------------
    seller_feedback_phrases = [
        "seller was",
        "seller is",
        "seller sent",
        "seller refused",
        "seller did not",
        "seller didn't",
        "seller never",
        "seller lied",
        "seller was rude",
        "seller was helpful",
        "seller was unhelpful",
        "bad seller",
        "good seller",
        "البائع كان",
        "البائع هو",
        "البائع ارسل",
        "البائع رفض",
        "البائع لم",
        "البائع كذب",
        "البائع وحش",
        "البائع كويس",
        "البائع سيء",
        "البايع كان",
        "البايع رفض",
        "البايع وحش",
        "البايع كويس",
    ]

    if contains_phrase(text, seller_feedback_phrases):
        return "2.1"

    # --------------------------------------------------------
    # 2.2 ORDER / RETURN EXPERIENCE
    # --------------------------------------------------------
    order_experience_phrases = [
        "my order was cancelled",
        "my order was canceled",
        "order was cancelled",
        "order was canceled",
        "my order was wrong",
        "wrong order",
        "wrong item in my order",
        "i returned the product",
        "i returned it",
        "return was rejected",
        "return was refused",
        "refund was rejected",
        "refund was refused",
        "refund not received",
        "did not receive my refund",
        "لم يصلني الاسترداد",
        "الاسترداد لم يصل",
        "الطلب اتلغى",
        "الطلب الغي",
        "الطلب غلط",
        "رجعت المنتج",
        "رفضوا الارجاع",
        "رفض الاسترجاع",
    ]

    if contains_phrase(text, order_experience_phrases):
        return "2.2"

    # --------------------------------------------------------
    # 2.3 SHIPPING / PACKAGING / DELIVERY
    # --------------------------------------------------------
    shipping_experience_phrases = [
        "delivery was late",
        "late delivery",
        "delivery was delayed",
        "delivery took too long",
        "shipping was late",
        "shipping was delayed",
        "package arrived late",
        "packaging was poor",
        "bad packaging",
        "poor packaging",
        "package was damaged",
        "التوصيل اتاخر",
        "التوصيل تأخر",
        "التوصيل كان متاخر",
        "التوصيل كان متأخر",
        "الشحن اتاخر",
        "الشحن تأخر",
        "التغليف سيء",
        "التغليف وحش",
        "تغليف سيء",
        "وصل متاخر",
        "وصل متأخر",
    ]

    if contains_phrase(text, shipping_experience_phrases):
        return "2.3"

    return None


# ============================================================
# CLOSEST VALID RULE FOR ALLOWED REVIEWS
# ============================================================

def get_closest_rule(review):
    """
    For allowed reviews, we still need to display a valid
    Article guideline section/sub-rule.

    This does NOT mean that the review violated the rule.
    It only identifies the closest relevant Article category.
    """

    text = normalize_text(review)

    # Availability-related review
    availability_words = [
        "hope it comes in more colors",
        "hope it will be available",
        "wish it was available",
        "wish it came in",
        "ممكن يتوفر",
        "اتمني يتوفر",
        "اتمنى يتوفر",
        "اتمنى يكون متوفر",
        "نفسي يكون متوفر",
    ]

    if contains_phrase(text, availability_words):
        return "3.2"

    # Seller-related feedback
    seller_words = [
        "seller",
        "seller was",
        "seller is",
        "البائع",
        "البايع",
    ]

    if contains_phrase(text, seller_words):
        return "2.1"

    # Order / return
    order_words = [
        "order",
        "ordered",
        "return",
        "returned",
        "refund",
        "طلب",
        "طلبت",
        "ارجاع",
        "إرجاع",
        "استرجاع",
        "استرداد",
    ]

    if contains_phrase(text, order_words):
        return "2.2"

    # Shipping / delivery
    shipping_words = [
        "delivery",
        "delivered",
        "shipping",
        "shipment",
        "package",
        "packaging",
        "شحن",
        "توصيل",
        "وصل",
        "التوصيل",
        "الشحن",
        "التغليف",
        "الباكدج",
    ]

    if contains_phrase(text, shipping_words):
        return "2.3"

    # Damage / missing
    damage_missing_words = [
        "broken",
        "damaged",
        "missing",
        "مكسور",
        "تالف",
        "ناقص",
        "مفقود",
    ]

    if contains_phrase(text, damage_missing_words):
        return "2.4"

    # Generic product feedback: 2.4 is the closest product-related
    # category available in the required output taxonomy. This does NOT
    # mean the review violates 2.4.
    return "2.4"


# ============================================================
# LANGUAGE INSTRUCTIONS
# ============================================================

def get_language_instruction(language):

    if language == "Arabic":
        return """
Respond in Arabic.

The review may contain Egyptian Arabic, Modern Standard Arabic,
English words, Arabic written with different spelling, or a mixture.

Understand the meaning and context of the review.
"""

    return """
Respond in English.

The review may contain English, Arabic, mixed Arabic/English,
or Arabic transliteration.

Understand the meaning and context of the review.
"""


# ============================================================
# AI PROMPT
# ============================================================

def build_prompt(review, language):
    language_instruction = get_language_instruction(language)
    article = get_noon_guidelines()

    return f"""
You are a highly accurate Noon Customer Review moderation classifier.

Your task is to read the ENTIRE customer review carefully, understand its
meaning and context, and classify it according to the OFFICIAL Noon Product
Review Guidelines supplied below. Do not classify based on isolated keywords.
Understand what the customer is actually saying.

{language_instruction}

============================================================
OFFICIAL NOON POLICY — LIVE SOURCE OF TRUTH
============================================================

The following text was fetched directly from the official Noon article:
{article}

============================================================
OUR CLASSIFICATION LOGIC
============================================================

1. The review should focus on the customer's personal experience with the
   PRODUCT itself.

2. Normal negative product feedback is ALLOWED when it is genuinely about
   the product. Examples: bad product, poor quality, ineffective, does not
   work well, I don't like it, disappointed with the product, weak battery,
   poor performance, or equivalent Arabic expressions.

3. Do NOT mark a review NOT_ALLOWED just because it is negative, short,
   emotional, mentions buying the product, mentions a seller, mentions a
   price, or uses words such as "order" or "delivery". Determine the actual
   subject of the statement.

4. Seller performance/reputation, ordering/return experience, shipping/
   packaging/delivery, and damage/missing-item complaints are NOT_ALLOWED
   when those are the subject of the review rather than the product itself.

5. "Found it cheaper elsewhere", cheaper at another store, competitor
   pricing, or similar price-comparison feedback is ALWAYS NOT_ALLOWED under
   3.1. Do not confuse this with an allowed value-for-money opinion such as
   "great quality for the price".

6. Stock or store-level availability statements are NOT_ALLOWED under 3.2.
   A general product wish such as "hope it comes in more colors" is allowed.

7. Promotional/advertising content, hate speech/discrimination, personal or
   sensitive information, conflicts of interest, and compensation/incentives
   are NOT_ALLOWED under the applicable official rule.

8. Offensive/abusive/illegal language is NOT_ALLOWED under 1.2. Use context:
   ordinary criticism such as "bad" or "poor quality" is NOT offensive, while
   genuinely abusive, vulgar, insulting, or illegal language is.

9. If a review contains multiple ideas, classify based on the clearest
   applicable violation. Choose the MOST DIRECT rule.

10. Never invent a violation. If the review is about the product and does
    not clearly violate an official rule, choose ALLOWED.

============================================================
ACCURACY CHECK BEFORE ANSWERING
============================================================

Before returning JSON, silently verify:
- What is the review actually talking about?
- Is the complaint about the PRODUCT or about the seller/order/delivery?
- Is there a cheaper-elsewhere comparison?
- Is there stock/availability feedback?
- Is the wording genuinely offensive or merely negative product feedback?
- Is there any promotion, personal information, discrimination, conflict of
  interest, or compensation?
- If none applies, keep it ALLOWED.

Return ONLY valid JSON with decision, rule_id, and comment.
No markdown. No additional fields.

Customer review:
{review}
"""


# ============================================================
# JSON SCHEMA
# ============================================================

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["ALLOWED", "NOT_ALLOWED"]
        },
        "rule_id": {
            "type": "string",
            "enum": list(RULES.keys())
        },
        "comment": {
            "type": "string"
        }
    },
    "required": [
        "decision",
        "rule_id",
        "comment"
    ],
    "additionalProperties": False
}


# ============================================================
# OPENROUTER CLIENT
# ============================================================

@st.cache_resource(show_spinner=False)
def get_openrouter_client():
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        try:
            api_key = st.secrets["OPENROUTER_API_KEY"]
        except Exception:
            api_key = None

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not configured."
        )

    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": ARTICLE_URL,
            "X-Title": "Noon Product Review Moderation Tool",
        },
    )


# ============================================================
# API ERROR HELPERS
# ============================================================

def is_access_denied_error(error):
    text = str(error).lower()
    return (
        "403" in text
        or "access denied" in text
        or "please check your network settings" in text
    )


def is_retryable_error(error):
    text = str(error).lower()
    return any(token in text for token in [
        "429", "rate limit", "timeout", "timed out",
        "temporarily unavailable", "503", "502", "500",
        "connection reset", "connection error"
    ])


def friendly_api_error(error):
    if is_access_denied_error(error):
        return (
            "OpenRouter API access was denied (HTTP 403). This is a "
            "network/service access issue, not a review-classification issue. "
            "The tool will not guess an ALLOWED result when the AI is unavailable. "
            "Please check the OPENROUTER_API_KEY and Streamlit Cloud/network "
            "access to openrouter.ai, then try again."
        )

    return str(error)


# ============================================================
# MODEL CALL
# ============================================================

def call_model(
    review,
    language,
    model,
    reasoning_effort=None
):
    client = get_openrouter_client()

    prompt = build_prompt(review, language)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict Noon Customer Review moderation classifier. "
                    "The supplied Noon Article rules are the only authority. "
                    "Do not invent rules. Return the required JSON only."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "review_moderation",
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
# VALIDATE RESULT
# ============================================================

def validate_result(result):

    if not isinstance(result, dict):
        raise ValueError("Model result is not a dictionary.")

    decision = result.get("decision")
    rule_id = result.get("rule_id")
    comment = result.get("comment")

    if decision not in ["ALLOWED", "NOT_ALLOWED"]:
        raise ValueError("Invalid decision.")

    if rule_id not in RULES:
        raise ValueError("Invalid rule_id.")

    if not isinstance(comment, str):
        raise ValueError("Invalid comment.")

    return {
        "decision": decision,
        "rule_id": rule_id,
        "comment": comment.strip()
    }


# ============================================================
# HARD RULE OVERRIDE
# ============================================================

def apply_hard_rule(result, rule_id, language):
    """
    Create a seller-facing explanation that can be sent directly
    without additional editing. The wording is tied to the relevant
    Noon Customer Review guideline and explains why the review cannot remain.
    """

    result = dict(result)
    result["decision"] = "NOT_ALLOWED"
    result["rule_id"] = rule_id

    if language == "Arabic":
        comments = {
            "1.1":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتضمن محتوى ترويجيًا أو إعلانيًا، مثل الترويج لمنتج أو متجر، مشاركة كود خصم، أو توجيه العملاء إلى وسيلة شراء أو تواصل. "
                "وفقًا للبند 1.1 من إرشادات تقييمات العملاء في نون، يجب أن يركز التقييم على تجربة العميل مع المنتج نفسه، ولذلك لا يمكن الإبقاء على هذا التقييم بصيغته الحالية.",

            "1.2":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتضمن ألفاظًا أو تعبيرات مسيئة أو مبتذلة أو غير لائقة أو غير مناسبة. "
                "وفقًا للبند 1.2 من إرشادات تقييمات العملاء في نون، هذا النوع من المحتوى يخالف قواعد المحتوى المسيء أو غير المناسب، ولذلك لا يمكن الإبقاء على التقييم.",

            "1.3":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتضمن خطاب كراهية أو محتوى تمييزيًا تجاه شخص أو فئة. "
                "وفقًا للبند 1.3 من إرشادات تقييمات العملاء في نون، لا يُسمح بالمحتوى الذي يتضمن كراهية أو تمييزًا، ولذلك لا يمكن الإبقاء على هذا التقييم.",

            "1.4":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتضمن معلومات شخصية أو حساسة، مثل رقم الهاتف أو البريد الإلكتروني أو عنوان أو بيانات يمكن استخدامها للتعرف على شخص. "
                "وفقًا للبند 1.4 من إرشادات تقييمات العملاء في نون، لا يُسمح بمشاركة هذا النوع من المعلومات داخل تقييم المنتج، ولذلك لا يمكن الإبقاء على التقييم.",

            "2.1":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يقدم ملاحظات عن البائع أو أدائه أو سمعته بدلًا من التركيز على تجربة العميل مع المنتج نفسه. "
                "وفقًا للبند 2.1 من إرشادات تقييمات العملاء في نون، تعليقات أداء البائع أو سمعته لا تُعد محتوى مناسبًا لتقييم المنتج، ولذلك لا يمكن الإبقاء على التقييم.",

            "2.2":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتناول تجربة الطلب أو الإرجاع، مثل إلغاء الطلب أو رفض الإرجاع أو مشكلة في استرداد المبلغ. "
                "وفقًا للبند 2.2 من إرشادات تقييمات العملاء في نون، يجب أن يركز التقييم على تجربة المنتج وليس على إجراءات الطلب أو الإرجاع، ولذلك لا يمكن الإبقاء على هذا التقييم.",

            "2.3":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتناول الشحن أو التغليف أو سرعة التوصيل أو تأخر وصول الطلب. "
                "وفقًا للبند 2.3 من إرشادات تقييمات العملاء في نون، هذه الملاحظات تتعلق بعملية التوصيل وليس بتجربة استخدام المنتج، ولذلك لا يمكن الإبقاء على التقييم.",

            "2.4":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يذكر أن المنتج وصل تالفًا أو مكسورًا أو أن جزءًا أو عنصرًا من المنتج مفقود. "
                "وفقًا للبند 2.4 من إرشادات تقييمات العملاء في نون، تعليقات التلف أو العناصر المفقودة تتعلق بحالة أو اكتمال الطلب عند الاستلام وليست بتجربة استخدام المنتج، ولذلك لا يمكن الإبقاء على التقييم.",

            "3.1":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يذكر أن العميل وجد نفس المنتج بسعر أرخص في مكان آخر أو يقارن سعر المنتج بسعر جهة أخرى. "
                "وفقًا للبند 3.1 من إرشادات تقييمات العملاء في نون، التعليقات التي تشير إلى العثور على المنتج بسعر أرخص في مكان آخر غير مسموح بها، ولذلك لا يمكن الإبقاء على التقييم.",

            "3.2":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتناول توفر المنتج أو حالة المخزون، مثل الإشارة إلى أن المنتج غير متوفر أو السؤال عن موعد توفره مرة أخرى. "
                "وفقًا للبند 3.2 من إرشادات تقييمات العملاء في نون، يجب ألا يتناول تقييم المنتج حالة المخزون أو توفره، ولذلك لا يمكن الإبقاء على التقييم.",

            "4.1":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتضمن تعارضًا في المصالح أو يشير إلى علاقة بين كاتب التقييم والبائع أو الموظف أو المنافس أو جهة مرتبطة بالمنتج. "
                "وفقًا للبند 4.1 من إرشادات تقييمات العملاء في نون، يجب أن يكون التقييم تجربة عميل مستقلة، ولذلك لا يمكن الإبقاء على هذا التقييم.",

            "4.2":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يشير إلى كتابة التقييم مقابل مقابل مادي أو منتج مجاني أو حافز مالي أو منفعة أخرى. "
                "وفقًا للبند 4.2 من إرشادات تقييمات العملاء في نون، التقييمات المنشورة مقابل تعويض أو حافز غير مسموح بها، ولذلك لا يمكن الإبقاء على التقييم.",
        }
    else:
        comments = {
            "1.1":
                "Regarding the submitted review, please note that it is not allowed because it contains promotional or advertising content, such as promoting a product or store, sharing a discount code, or directing customers to a purchasing or contact method. "
                "Under Section 1.1 of the Noon Customer Review guidelines, reviews should focus on the customer's experience with the product itself, so this review cannot remain in its current form.",

            "1.2":
                "Regarding the submitted review, please note that it is not allowed because it contains offensive, abusive, vulgar, inappropriate, or distasteful language. "
                "Under Section 1.2 of the Noon Customer Review guidelines, this type of content violates the rule covering offensive or inappropriate language, so the review cannot remain.",

            "1.3":
                "Regarding the submitted review, please note that it is not allowed because it contains hate speech or discriminatory content directed at a person or group. "
                "Under Section 1.3 of the Noon Customer Review guidelines, hate speech and discriminatory content are not allowed, so the review cannot remain.",

            "1.4":
                "Regarding the submitted review, please note that it is not allowed because it contains personal or sensitive information, such as a phone number, email address, physical address, or information that can directly identify a person. "
                "Under Section 1.4 of the Noon Customer Review guidelines, this type of information should not be included in a product review, so the review cannot remain.",

            "2.1":
                "Regarding the submitted review, please note that it is not allowed because it provides feedback about the seller's performance or reputation instead of focusing on the customer's experience with the product itself. "
                "Under Section 2.1 of the Noon Customer Review guidelines, seller performance or reputation feedback is not permitted in a product review, so the review cannot remain.",

            "2.2":
                "Regarding the submitted review, please note that it is not allowed because it discusses the ordering or return experience, such as an order cancellation, rejected return, or refund issue. "
                "Under Section 2.2 of the Noon Customer Review guidelines, reviews should focus on the product experience rather than the order or return process, so the review cannot remain.",

            "2.3":
                "Regarding the submitted review, please note that it is not allowed because it discusses shipping, packaging, delivery speed, or a delayed delivery. "
                "Under Section 2.3 of the Noon Customer Review guidelines, these comments concern the delivery process rather than the product experience, so the review cannot remain.",

            "2.4":
                "Regarding the submitted review, please note that it is not allowed because it reports that the product arrived damaged or broken, or that an item, part, or accessory was missing. "
                "Under Section 2.4 of the Noon Customer Review guidelines, damage and missing-item comments concern the condition or completeness of the delivered order rather than the normal product experience, so the review cannot remain.",

            "3.1":
                "Regarding the submitted review, please note that it is not allowed because it states that the customer found the same product cheaper elsewhere or compares the product's price with another seller or source. "
                "Under Section 3.1 of the Noon Customer Review guidelines, comments about finding the product cheaper elsewhere are not allowed, so the review cannot remain.",

            "3.2":
                "Regarding the submitted review, please note that it is not allowed because it discusses the product's stock status or availability, such as saying that the item is unavailable or asking when it will be available again. "
                "Under Section 3.2 of the Noon Customer Review guidelines, stock and availability comments are not allowed in a product review, so the review cannot remain.",

            "4.1":
                "Regarding the submitted review, please note that it is not allowed because it indicates a conflict of interest or a relationship between the reviewer and the seller, employee, competitor, or another party connected to the product. "
                "Under Section 4.1 of the Noon Customer Review guidelines, reviews must represent an independent customer experience, so this review cannot remain.",

            "4.2":
                "Regarding the submitted review, please note that it is not allowed because it indicates that the review was submitted in exchange for compensation, a free product, a financial incentive, or another benefit. "
                "Under Section 4.2 of the Noon Customer Review guidelines, reviews submitted in exchange for compensation or incentives are not allowed, so the review cannot remain.",
        }

    result["comment"] = comments.get(rule_id, result.get("comment", ""))
    return result


# ============================================================
# OFFENSIVE LANGUAGE OVERRIDE
# ============================================================

def apply_offensive_rule(result, language):

    result = dict(result)
    result["decision"] = "NOT_ALLOWED"
    result["rule_id"] = "1.2"

    if language == "Arabic":
        result["comment"] = (
            "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتضمن ألفاظًا أو تعبيرات مسيئة أو مبتذلة أو غير لائقة أو غير مناسبة. "
            "وفقًا للبند 1.2 من إرشادات تقييمات العملاء في نون، يجب ألا تتضمن تقييمات المنتجات هذا النوع من المحتوى، ولذلك لا يمكن الإبقاء على التقييم."
        )
    else:
        result["comment"] = (
            "Regarding the submitted review, please note that it is not allowed because it contains offensive, abusive, vulgar, inappropriate, or distasteful language. "
            "Under Section 1.2 of the Noon Customer Review guidelines, this type of content is not permitted in product reviews, so the review cannot remain."
        )

    return result


# ============================================================
# ALLOWED RULE
# ============================================================

def apply_allowed_rule(result, review, language):

    result = dict(result)
    result["decision"] = "ALLOWED"
    closest_rule = get_closest_rule(review)
    result["rule_id"] = closest_rule

    if language == "Arabic":
        result["comment"] = (
            "بخصوص التقييم المذكور، يرجى العلم بأنه مسموح ويمكن الإبقاء عليه لأنه يركز على تجربة العميل الشخصية مع المنتج، مثل الجودة أو الأداء أو الفعالية أو الاستخدام أو مدى رضا العميل عن المنتج. "
            "ولا يتضمن التقييم، وفقًا لإرشادات تقييمات العملاء في نون، محتوى ترويجيًا أو ألفاظًا مسيئة أو معلومات شخصية أو ملاحظات عن أداء البائع أو تجربة الطلب والإرجاع أو الشحن والتوصيل أو العثور على المنتج بسعر أرخص في مكان آخر أو حالة المخزون أو تعارض المصالح أو الحصول على مقابل. "
            "وبالتالي لا توجد مخالفة واضحة لبنود الإزالة في Article الخاص بتقييمات العملاء، ويمكن الإبقاء على التقييم كما هو."
        )
    else:
        result["comment"] = (
            "Regarding the submitted review, please note that it is allowed and can remain because it focuses on the customer's personal experience with the product, such as its quality, performance, effectiveness, usefulness, or overall satisfaction. "
            "Under the Noon Customer Review guidelines, the review does not contain promotional content, offensive language, personal information, seller-performance feedback, order or return feedback, shipping or delivery feedback, a cheaper-elsewhere price comparison, stock-availability feedback, a conflict of interest, or compensation-related content. "
            "Therefore, there is no clear violation of the removal rules in the Customer Reviews Article, and the review can remain as submitted."
        )

    return result


# ============================================================
# SECOND AI ADJUDICATOR
# ============================================================

def call_adjudicator(review, language, first_result):
    article = get_noon_guidelines()

    adjudicator_prompt = f"""
You are the final quality-control reviewer for Noon Customer Reviews.

Read the review carefully and independently verify the first classifier
result against the official Noon policy below. Focus on meaning and context,
not keyword matching.

OFFICIAL NOON POLICY:
{article}

CLASSIFICATION LOGIC:
- Product-focused personal experience, including normal negative criticism,
  is ALLOWED unless another rule clearly applies.
- Seller performance/reputation = 2.1 NOT_ALLOWED.
- Ordering/return experience = 2.2 NOT_ALLOWED.
- Shipping/packaging/delivery = 2.3 NOT_ALLOWED.
- Damage/missing items = 2.4 NOT_ALLOWED.
- Cheaper elsewhere / competitor price comparison = 3.1 NOT_ALLOWED.
- Stock/store availability = 3.2 NOT_ALLOWED.
- Promotional content, offensive/abusive/illegal language, hate/discrimination,
  personal/sensitive information = applicable 1.x NOT_ALLOWED.
- Conflict of interest = 4.1 NOT_ALLOWED.
- Compensation/incentive = 4.2 NOT_ALLOWED.
- Do not invent violations from isolated words.

First classifier result:
{json.dumps(first_result, ensure_ascii=False)}

Customer review:
{review}

If the first result is wrong, correct it. If there is no clear violation,
choose ALLOWED. Choose the most direct rule for a violation.

Return ONLY valid JSON with decision, rule_id, and comment.
No markdown. No additional fields.
"""

    client = get_openrouter_client()

    response = client.chat.completions.create(
        model=PRIMARY_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a final quality-control reviewer. "
                    "Follow the supplied official Noon policy exactly. "
                    "Understand the full review before deciding. Return JSON only."
                )
            },
            {"role": "user", "content": adjudicator_prompt}
        ],
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "review_adjudication",
                "strict": True,
                "schema": REVIEW_SCHEMA
            }
        }
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("Empty adjudicator response.")

    return validate_result(json.loads(content))


# ============================================================
# SECOND REVIEW DECISION
# ============================================================

def should_run_second_review(review, first_result):
    """
    Run a second AI pass only when the first AI says NOT_ALLOWED.

    Clear violations are already handled deterministically before the AI.
    For semantic cases, a second pass is valuable mainly to verify a removal
    decision and reduce false positives, while ALLOWED product reviews stay
    on the faster one-call path.
    """
    return first_result.get("decision") == "NOT_ALLOWED"


# ============================================================
# RELIABLE EVALUATION
# ============================================================

def evaluate_with_reliability(review, language):
    """
    Article-first hybrid moderation.

    1) High-confidence Article rules are checked locally.
    2) If no deterministic violation exists, the AI evaluates the review
       against the structured Article.
    3) A second AI adjudication is used only for ambiguous/potentially
       policy-related cases.
    4) If OpenRouter is unavailable, NEVER invent an ALLOWED result.
    """

    hard_rule = detect_hard_rules(review)
    if not hard_rule:
        hard_rule = detect_high_confidence_article_rule(review)

    clear_offensive = detect_clear_offensive_language(review)

    # Deterministic Article violations are final and fast.
    deterministic_rule = hard_rule
    if clear_offensive and not deterministic_rule:
        deterministic_rule = "1.2"

    if deterministic_rule:
        return apply_hard_rule(
            {"decision": "NOT_ALLOWED", "rule_id": deterministic_rule, "comment": ""},
            deterministic_rule,
            language
        )

    # AI is the authority for semantic/contextual cases, with fallback model.
    errors = []
    first_result = None

    for model in [PRIMARY_MODEL, FALLBACK_MODEL]:
        try:
            first_result = call_model(
                review, language, model, reasoning_effort="low"
            )
            first_result = validate_result(first_result)
            break
        except Exception as e:
            errors.append(e)
            # Do not repeat the same model after a network/service 403.
            # Try the configured fallback model once instead.
            if is_access_denied_error(e):
                continue
            if is_retryable_error(e):
                time.sleep(1)
                continue

    if first_result is None:
        # Safe behavior: do not fabricate a moderation decision.
        raise RuntimeError(friendly_api_error(errors[-1]))

    # Second adjudication only for potentially ambiguous results.
    if should_run_second_review(review, first_result):
        try:
            final_result = call_adjudicator(
                review, language, first_result
            )
        except Exception as e:
            # If the primary classifier succeeded, preserve it rather than
            # turning a secondary network failure into a false classification.
            final_result = first_result

    else:
        final_result = first_result

    # Final deterministic safety layer always wins.
    if detect_clear_offensive_language(review):
        final_result = apply_offensive_rule(final_result, language)

    if final_result["decision"] == "ALLOWED":
        final_result = apply_allowed_rule(
            final_result, review, language
        )

    return validate_result(final_result)


# ============================================================
# MAIN EVALUATION
# ============================================================

def evaluate_review(review, language):

    if not review or not review.strip():
        raise ValueError(
            "Please enter a customer review."
        )

    review = review.strip()

    return evaluate_with_reliability(
        review,
        language
    )


# ============================================================
# SESSION STATE
# ============================================================

if "review_input" not in st.session_state:
    st.session_state["review_input"] = ""

if "review_result" not in st.session_state:
    st.session_state["review_result"] = None

if "copy_comment" not in st.session_state:
    st.session_state["copy_comment"] = ""

if "review_input_key" not in st.session_state:
    st.session_state["review_input_key"] = 0


def reset_tool():
    """Clear the input and every displayed result before the next rerun."""
    st.session_state["review_input"] = ""
    st.session_state["review_result"] = None
    st.session_state["copy_comment"] = ""
    st.session_state["review_input_key"] = st.session_state.get("review_input_key", 0) + 1


# ============================================================
# UI
# ============================================================

st.title("Product Review Moderation Tool")


# ------------------------------------------------------------
# LANGUAGE
# ------------------------------------------------------------

language = st.radio(
    "Language",
    ["English", "Arabic"],
    horizontal=True
)


# ------------------------------------------------------------
# REVIEW INPUT
# ------------------------------------------------------------

review = st.text_area(
    "Enter Customer Review:",
    key="review_input",
    height=180,
    placeholder="Enter the customer review here..."
)


# ------------------------------------------------------------
# EVALUATE REVIEW BUTTON - RED TEXT
# ------------------------------------------------------------

st.markdown(
    """
    <style>
    div[data-testid="stHorizontalBlock"]
    div[data-testid="stColumn"]:first-child
    div[data-testid="stButton"] button {
        background-color: #ff4b4b !important;
        color: white !important;
        border: 1px solid #ff4b4b !important;
        border-radius: 6px !important;
    }

    div[data-testid="stHorizontalBlock"]
    div[data-testid="stColumn"]:first-child
    div[data-testid="stButton"] button:hover {
        background-color: #ff3333 !important;
        color: white !important;
        border-color: #ff3333 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ------------------------------------------------------------
# BUTTONS
# ------------------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    evaluate_button = st.button(
        "Evaluate Review",
        use_container_width=True
    )

with col2:
    reset_button = st.button(
        "Reset",
        use_container_width=True,
        on_click=reset_tool
    )


# ------------------------------------------------------------
# EVALUATE
# ------------------------------------------------------------

if evaluate_button:

    try:

        with st.spinner("Evaluating review..."):

            result = evaluate_review(
                review,
                language
            )

            st.session_state["review_result"] = result

    except Exception as e:

        st.error(
            f"An error occurred while evaluating the review: {friendly_api_error(e)}"
        )


# ============================================================
# RESULT DISPLAY
# ============================================================

if st.session_state.get("review_result"):

    result = st.session_state["review_result"]

    decision = result["decision"]
    rule_id = result["rule_id"]
    comment = result["comment"]

    if decision == "ALLOWED":
        decision_text = (
            "✅ Allowed — it should not be removed."
        )
    else:
        decision_text = (
            "❌ Not allowed — it should be removed"
        )

    if language == "Arabic":

        section_text = ARABIC_SECTIONS[
            RULES[rule_id]["section"]
        ]

        rule_text = ARABIC_RULES[
            rule_id
        ]

        decision_label = "Decision:"
        section_label = "Main Guideline Section:"
        rule_label = "Specific Sub-rule:"
        comment_label = "Comment:"

    else:

        section_text = RULES[
            rule_id
        ]["section"]

        rule_text = RULES[
            rule_id
        ]["rule"]

        decision_label = "Decision:"
        section_label = "Main Guideline Section:"
        rule_label = "Specific Sub-rule:"
        comment_label = "Comment:"


    st.markdown(
        f"""
**{decision_label}** {decision_text}

**{section_label}** {section_text}

**{rule_label}** {rule_text}

**{comment_label}** {comment}
"""
    )


    # --------------------------------------------------------
    # COPY COMMENT
    # --------------------------------------------------------

    copy_text = comment.replace("'", "\\'").replace("\n", "\\n")

    components.html(
        f"""
        <script>
        function copyComment() {{
            navigator.clipboard.writeText('{copy_text}');
        }}
        </script>

        <button
            onclick="copyComment()"
            style="
                padding: 8px 16px;
                border-radius: 6px;
                border: 1px solid #ccc;
                background: white;
                cursor: pointer;
                font-size: 14px;
            "
        >
            📋 Copy Comment
        </button>
        """,
        height=50
    )


# ============================================================
# GUIDELINES LINK
# ============================================================

st.markdown(
    f"""
    <div style="margin-top: 20px;">
        <a
            href="{ARTICLE_URL}"
            target="_blank"
            rel="noopener noreferrer"
        >
            Noon Customer Reviews Guidelines
        </a>
    </div>
    """,
    unsafe_allow_html=True
)
