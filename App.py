import streamlit as st
import os
import streamlit.components.v1 as components
import json
import re
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
# MODELS
# ============================================================

PRIMARY_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "openai/gpt-oss-20b"


# ============================================================
# NOON PRODUCT REVIEW ARTICLE
# ============================================================
# The Article is intentionally represented as a structured
# policy object instead of one long prompt paragraph.
#
# Source:
# https://help.noon.com/portal/en/kb/articles/product-review-guidelines
#
# This structure is used to generate the AI policy prompt.
# The deterministic rules below remain separate and are not
# removed or weakened.
# ============================================================

ARTICLE_POLICY = {

    "article_name": "Noon Product Review Guidelines",

    "source": (
        "https://help.noon.com/portal/en/kb/articles/"
        "product-review-guidelines"
    ),

    "core_requirement": (
        "A product review should focus solely on the customer's "
        "personal experience with the product purchased."
    ),

    "allowed_review_focus": [
        "What the customer liked about the product.",
        "Whether the product is easy to use.",
        "Whether the product offers good value for money.",
        "Whether the customer would recommend the product.",
        "What other customers should know before buying the product.",
        "Product quality.",
        "Product performance.",
        "Product effectiveness.",
        "Product usefulness.",
        "Normal positive or negative opinions about the product."
    ],

    "important_allowed_principle": (
        "Normal criticism of the product itself is allowed. "
        "A review does not become prohibited merely because it is "
        "negative, disappointed, critical, or poorly written."
    ),

    "sections": {

        "1": {
            "name": "Community Guideline Violations",

            "rules": {

                "1.1": {
                    "name": "Promotional or advertising content",

                    "description": (
                        "Reviews containing promotional or advertising "
                        "content are not permitted."
                    ),

                    "examples": [
                        "Use my promo code.",
                        "Use my discount code.",
                        "Buy from my store.",
                        "Visit my store.",
                        "Contact me to buy.",
                        "DM me to buy."
                    ]
                },

                "1.2": {
                    "name": (
                        "Offensive, abusive, inappropriate, "
                        "vulgar, or distasteful language"
                    ),

                    "description": (
                        "Reviews containing offensive, abusive, "
                        "or illegal language are not permitted. "
                        "For classification purposes, genuinely "
                        "offensive, vulgar, abusive, inappropriate, "
                        "or distasteful language must be treated as "
                        "a violation."
                    ),

                    "examples": [
                        "Fuck this product.",
                        "Fucking garbage.",
                        "Piece of shit.",
                        "Disgusting product.",
                        "The product is disgusting.",
                        "يا غبي",
                        "المنتج زبالة",
                        "المنتج مقرف",
                        "المنتج زفت"
                    ],

                    "important_exception": (
                        "Ordinary negative product opinions such as "
                        "'bad', 'poor quality', 'not useful', "
                        "'I don't like it', or 'المنتج سيء' are not "
                        "automatically offensive."
                    )
                },

                "1.3": {
                    "name": "Hate speech or discriminatory remarks",

                    "description": (
                        "Hate speech or discriminatory remarks "
                        "directed at a person or group are not permitted."
                    )
                },

                "1.4": {
                    "name": "Personal or sensitive information",

                    "description": (
                        "Personal or sensitive information should not "
                        "be included in a product review."
                    ),

                    "examples": [
                        "Phone numbers.",
                        "Email addresses.",
                        "Physical addresses.",
                        "Other information that directly identifies a person."
                    ]
                }
            }
        },


        "2": {
            "name": "Seller, Order, or Shipping Feedback",

            "general_rule": (
                "Product reviews should only describe the product itself."
            ),

            "rules": {

                "2.1": {
                    "name": "Seller performance or reputation",

                    "description": (
                        "Reviews that focus on seller performance "
                        "or reputation are not allowed."
                    ),

                    "examples": [
                        "The seller was rude.",
                        "The seller was helpful.",
                        "Bad seller.",
                        "The seller refused my request."
                    ]
                },

                "2.2": {
                    "name": "Ordering or return experiences",

                    "description": (
                        "Reviews that focus on ordering or return "
                        "experiences are not allowed."
                    ),

                    "examples": [
                        "My order was cancelled.",
                        "Wrong order.",
                        "I returned the product.",
                        "My return was rejected.",
                        "I did not receive my refund."
                    ]
                },

                "2.3": {
                    "name": "Shipping, packaging, or delivery speed",

                    "description": (
                        "Reviews that focus on shipping, packaging, "
                        "or delivery speed are not allowed."
                    ),

                    "examples": [
                        "Delivery was late.",
                        "Shipping was delayed.",
                        "Bad packaging.",
                        "The package arrived late."
                    ]
                },

                "2.4": {
                    "name": "Product damage or missing items",

                    "description": (
                        "Reviews reporting product damage or missing "
                        "items/parts are not allowed."
                    ),

                    "examples": [
                        "The product arrived broken.",
                        "The product arrived damaged.",
                        "A part is missing.",
                        "An accessory is missing."
                    ]
                }
            }
        },


        "3": {
            "name": "Comments About Pricing or Availability",

            "rules": {

                "3.1": {
                    "name": "Finding the product cheaper elsewhere",

                    "description": (
                        "A review saying that the customer found the "
                        "same product cheaper elsewhere is not allowed."
                    ),

                    "examples": [
                        "Found it cheaper elsewhere.",
                        "I found it cheaper in another store.",
                        "Same product is cheaper somewhere else.",
                        "وجدته بسعر ارخص.",
                        "لقيته ارخص في مكان تاني.",
                        "نفس المنتج ارخص."
                    ],

                    "allowed_exception": (
                        "The customer may mention price when it relates "
                        "to the product's value."
                    ),

                    "allowed_examples": [
                        "Great quality for the price.",
                        "Good product for this price.",
                        "The price is reasonable.",
                        "Excellent value for money."
                    ]
                },

                "3.2": {
                    "name": "Stock status or availability",

                    "description": (
                        "Comments about stock status, out-of-stock "
                        "status, or store-level availability are not allowed."
                    ),

                    "examples": [
                        "Out of stock.",
                        "When will it be available?",
                        "It is no longer available.",
                        "The product is unavailable.",
                        "المنتج غير متوفر.",
                        "متى سيتوفر؟"
                    ],

                    "allowed_exception": (
                        "General wishes about availability are allowed "
                        "when they do not state or ask about actual "
                        "stock status."
                    ),

                    "allowed_examples": [
                        "Hope it comes in more colors.",
                        "I wish there were more sizes.",
                        "I wish this product came in another color."
                    ]
                }
            }
        },


        "4": {
            "name": "Conflicts of Interest",

            "general_rule": (
                "Reviews must be unbiased and independent."
            ),

            "rules": {

                "4.1": {
                    "name": "Conflict of interest",

                    "description": (
                        "A reviewer cannot create, edit, or post content "
                        "about their own products or services, or content "
                        "connected to a conflict of interest."
                    ),

                    "covered_relationships": [
                        "Own products or services.",
                        "Friends.",
                        "Family members.",
                        "Employers.",
                        "Employees.",
                        "Business partners.",
                        "Business associates.",
                        "Competitors."
                    ],

                    "examples": [
                        "I am the seller.",
                        "I work for the seller.",
                        "I am the brand owner.",
                        "My friend is the seller.",
                        "My family member is the seller.",
                        "I work for a competitor.",
                        "I am the manufacturer.",
                        "I am a Noon employee."
                    ]
                },

                "4.2": {
                    "name": "Compensation or financial incentive",

                    "description": (
                        "Reviews submitted in exchange for compensation "
                        "or any benefit are not allowed."
                    ),

                    "examples": [
                        "I was paid to review this.",
                        "I received money for this review.",
                        "I received a free product for this review.",
                        "I was compensated for this review.",
                        "I received a benefit in exchange for a review."
                    ]
                }
            }
        }
    },

    "consequences": [
        "The review may be removed.",
        "The user's ability to post or edit reviews may be restricted.",
        "Related products may be removed from listings.",
        "The user's account may be suspended or terminated.",
        "Additional action may be taken in cases involving fraud, manipulation, or local-law violations."
    ]
}


# ============================================================
# RULE MAPPING
# ============================================================

RULES = {

    "1.1": {
        "section": "Community Guideline Violations",
        "rule": "Promotional or advertising content",
    },

    "1.2": {
        "section": "Community Guideline Violations",
        "rule": (
            "Offensive, abusive, inappropriate, vulgar, "
            "or distasteful language"
        ),
    },

    "1.3": {
        "section": "Community Guideline Violations",
        "rule": "Hate speech or discriminatory content",
    },

    "1.4": {
        "section": "Community Guideline Violations",
        "rule": "Personal or sensitive information",
    },

    "2.1": {
        "section": "Seller, Order, or Shipping Feedback",
        "rule": "Seller performance or reputation",
    },

    "2.2": {
        "section": "Seller, Order, or Shipping Feedback",
        "rule": "Ordering or return experience",
    },

    "2.3": {
        "section": "Seller, Order, or Shipping Feedback",
        "rule": "Shipping, packaging, or delivery",
    },

    "2.4": {
        "section": "Seller, Order, or Shipping Feedback",
        "rule": "Product damage or missing items",
    },

    "3.1": {
        "section": "Comments About Pricing or Availability",
        "rule": "Finding the product cheaper elsewhere",
    },

    "3.2": {
        "section": "Comments About Pricing or Availability",
        "rule": "Stock status or availability",
    },

    "4.1": {
        "section": "Conflicts of Interest",
        "rule": "Conflict of interest",
    },

    "4.2": {
        "section": "Conflicts of Interest",
        "rule": "Compensation or financial incentive",
    },
}


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

    "Conflicts of Interest":
        "تعارض المصالح",
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
    text = re.sub(
        r"[\u064B-\u065F\u0670\u0640]",
        "",
        text
    )

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

        if (
            phrase_normalized
            and phrase_normalized in normalized
        ):
            return True

    return False


# ============================================================
# HARD RULE DETECTION
# ============================================================

def detect_hard_rules(review):

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

    text = normalize_text(review)

    offensive_phrases = [

        # ----------------------------------------------------
        # ENGLISH
        # ----------------------------------------------------

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
        # ARABIC
        # ----------------------------------------------------

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

        "وسخه",
        "وسخة",
    ]

    for phrase in offensive_phrases:

        normalized_phrase = normalize_text(phrase)

        if not normalized_phrase:
            continue

        if " " not in normalized_phrase:

            if re.search(
                r"(?<![\w])"
                + re.escape(normalized_phrase)
                + r"(?![\w])",
                text
            ):
                return True

        elif normalized_phrase in text:

            return True

    return False


# ============================================================
# HIGH-CONFIDENCE ARTICLE RULE DETECTION
# ============================================================

def detect_high_confidence_article_rule(review):

    text = normalize_text(review)

    # --------------------------------------------------------
    # 1.1 PROMOTIONAL / ADVERTISING
    # --------------------------------------------------------

    promotional_phrases = [

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
    ]

    if contains_phrase(
        text,
        promotional_phrases
    ):
        return "1.1"

    # Explicit external links / social handles
    if re.search(
        r"https?://|www\.|@[a-z0-9_.-]{3,}",
        text
    ):
        return "1.1"


    # --------------------------------------------------------
    # 1.4 PERSONAL / SENSITIVE INFORMATION
    # --------------------------------------------------------

    if re.search(
        r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b",
        text
    ):
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

    if contains_phrase(
        text,
        personal_info_phrases
    ):
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

    if contains_phrase(
        text,
        incentive_phrases
    ):
        return "4.2"


    # --------------------------------------------------------
    # 4.1 CONFLICT OF INTEREST
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

    if contains_phrase(
        text,
        conflict_phrases
    ):
        return "4.1"


    # --------------------------------------------------------
    # 2.1 SELLER PERFORMANCE
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

    if contains_phrase(
        text,
        seller_feedback_phrases
    ):
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

    if contains_phrase(
        text,
        order_experience_phrases
    ):
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

    if contains_phrase(
        text,
        shipping_experience_phrases
    ):
        return "2.3"

    return None


# ============================================================
# CLOSEST VALID RULE FOR ALLOWED REVIEWS
# ============================================================

def get_closest_rule(review):

    text = normalize_text(review)

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

    if contains_phrase(
        text,
        availability_words
    ):
        return "3.2"


    seller_words = [
        "seller",
        "seller was",
        "seller is",
        "البائع",
        "البايع",
    ]

    if contains_phrase(
        text,
        seller_words
    ):
        return "2.1"


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

    if contains_phrase(
        text,
        order_words
    ):
        return "2.2"


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

    if contains_phrase(
        text,
        shipping_words
    ):
        return "2.3"


    damage_missing_words = [

        "broken",
        "damaged",
        "missing",

        "مكسور",
        "تالف",
        "ناقص",
        "مفقود",
    ]

    if contains_phrase(
        text,
        damage_missing_words
    ):
        return "2.4"


    # Generic product feedback
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
Do not translate the review.
The final comment must be written in Arabic.
"""

    return """
Respond in English.

The review may contain English, Arabic, mixed Arabic/English,
or Arabic transliteration.

Understand the meaning and context of the review.
The final comment must be written in English.
"""


# ============================================================
# STRUCTURED ARTICLE -> AI POLICY TEXT
# ============================================================

def build_structured_policy_text():

    lines = []

    lines.append(
        "ARTICLE: Noon Product Review Guidelines"
    )

    lines.append(
        f"CORE REQUIREMENT: "
        f"{ARTICLE_POLICY['core_requirement']}"
    )

    lines.append("")

    lines.append(
        "ALLOWED REVIEW FOCUS:"
    )

    for item in ARTICLE_POLICY["allowed_review_focus"]:
        lines.append(f"- {item}")

    lines.append("")

    lines.append(
        "IMPORTANT GENERAL PRINCIPLE:"
    )

    lines.append(
        f"- {ARTICLE_POLICY['important_allowed_principle']}"
    )

    lines.append("")

    for section_id, section in ARTICLE_POLICY["sections"].items():

        lines.append(
            f"SECTION {section_id}: {section['name']}"
        )

        if section.get("general_rule"):
            lines.append(
                f"GENERAL RULE: {section['general_rule']}"
            )

        for rule_id, rule in section["rules"].items():

            lines.append(
                f"RULE {rule_id}: {rule['name']}"
            )

            if rule.get("description"):
                lines.append(
                    f"DESCRIPTION: {rule['description']}"
                )

            if rule.get("covered_relationships"):

                lines.append(
                    "COVERED RELATIONSHIPS:"
                )

                for item in rule["covered_relationships"]:
                    lines.append(
                        f"- {item}"
                    )

            if rule.get("examples"):

                lines.append(
                    "NOT-ALLOWED EXAMPLES:"
                )

                for example in rule["examples"]:
                    lines.append(
                        f"- {example}"
                    )

            if rule.get("allowed_exception"):

                lines.append(
                    "ALLOWED EXCEPTION:"
                )

                lines.append(
                    f"- {rule['allowed_exception']}"
                )

            if rule.get("allowed_examples"):

                lines.append(
                    "ALLOWED EXAMPLES:"
                )

                for example in rule["allowed_examples"]:
                    lines.append(
                        f"- {example}"
                    )

            lines.append("")

    return "\n".join(lines)


# ============================================================
# AI PROMPT
# ============================================================

def build_prompt(review, language):

    language_instruction = get_language_instruction(language)

    structured_policy = build_structured_policy_text()

    rules_text = "\n".join(
        [
            f"{rule_id}: "
            f"{data['section']} -> {data['rule']}"
            for rule_id, data in RULES.items()
        ]
    )

    return f"""
You are a strict Noon Product Review moderation classifier.

Your job is to determine whether the customer review is ALLOWED
or NOT_ALLOWED according ONLY to the structured Noon Product Review
Guidelines supplied below.

Do not invent policy.
Do not expand policy.
Do not substitute your own standards.
Do not create a violation simply because the review is negative.

{language_instruction}

============================================================
STRUCTURED NOON ARTICLE POLICY
============================================================

{structured_policy}

============================================================
CLASSIFICATION RULES
============================================================

1. The review must focus on the customer's personal experience
   with the product.

2. Normal product criticism is allowed.

3. A negative opinion about the product itself is NOT automatically
   a policy violation.

4. A clear violation of a specific Article rule must be classified
   as NOT_ALLOWED.

5. If there is no clear Article violation, classify the review
   as ALLOWED.

6. Use the most direct applicable rule when a violation exists.

7. Do not classify a review as NOT_ALLOWED merely because it:
   - is negative,
   - says the product is bad,
   - says the quality is poor,
   - says the product is ineffective,
   - says the customer dislikes it,
   - says the customer is disappointed,
   - mentions buying or ordering the product,
   - mentions the product price without an invalid comparison,
   - mentions a seller without actually reviewing seller performance,
   - expresses a general wish for more colors or sizes.

============================================================
ORDINARY PRODUCT CRITICISM
============================================================

These examples MUST remain ALLOWED unless another Article rule
is clearly violated:

- The product is bad.
- The quality is poor.
- The battery drains quickly.
- The product is not useful.
- I don't like the product.
- The product disappointed me.
- The product does not work well.
- The product is not effective.
- المنتج سيء
- المنتج وحش
- مش عاجبني المنتج
- المنتج مش مفيد
- البطارية بتخلص بسرعة
- المنتج لم يعجبني
- الجودة ضعيفة

============================================================
OFFENSIVE LANGUAGE
============================================================

Genuinely offensive, abusive, vulgar, inappropriate, or
distasteful language must be NOT_ALLOWED under 1.2.

Examples:

- disgusting product
- This product is disgusting
- fucking garbage
- piece of shit
- shit product
- fuck this
- fuck you
- المنتج مقرف
- المنتج زبالة
- المنتج زفت
- يا غبي

Do NOT classify normal negative product criticism as offensive.

For example:

"The product is bad"
"The quality is poor"
"I don't like it"
"المنتج سيء"

must remain ALLOWED unless another rule applies.

============================================================
PRICING
============================================================

A review saying that the same product was found cheaper elsewhere
is NOT_ALLOWED under 3.1.

Examples:

- Found it cheaper elsewhere.
- I found it cheaper in another store.
- Same product is cheaper somewhere else.
- لقيته ارخص في مكان تاني.
- وجدته بسعر ارخص.

However, value-for-money comments are ALLOWED:

- Great quality for the price.
- Good product for this price.
- The price is reasonable.
- Excellent value for money.

============================================================
AVAILABILITY
============================================================

Actual stock or store-level availability comments are NOT_ALLOWED
under 3.2.

Examples:

- Out of stock.
- When will it be available?
- It is no longer available.
- المنتج غير متوفر.
- متى سيتوفر؟

General wishes are ALLOWED:

- Hope it comes in more colors.
- I wish there were more sizes.

============================================================
DAMAGE / MISSING ITEMS
============================================================

If the review says that the purchased product arrived broken,
damaged, or with missing parts/items, classify it as NOT_ALLOWED
under 2.4.

============================================================
SELLER / ORDER / SHIPPING
============================================================

Use:

2.1 for actual seller performance or reputation feedback.

2.2 for ordering or return experiences.

2.3 for shipping, packaging, or delivery speed.

2.4 for product damage or missing items.

A simple mention of "seller", "order", "delivery", or "shipping"
does not automatically create a violation.

The context must actually describe the prohibited experience.

============================================================
CONFLICT OF INTEREST
============================================================

Section 4 concerns unbiased and independent reviews.

4.1 applies to conflicts such as:

- Own products or services.
- Friends.
- Family members.
- Employers.
- Employees.
- Business partners.
- Business associates.
- Competitors.

4.2 applies when the review is posted in exchange for
compensation, money, a free product, or another benefit.

============================================================
VALID RULE IDS
============================================================

{rules_text}

============================================================
FINAL DECISION
============================================================

If there is a clear Article violation:
decision = NOT_ALLOWED

If there is no clear Article violation:
decision = ALLOWED

Do not invent a violation.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON:

{{
  "decision": "ALLOWED" or "NOT_ALLOWED",
  "rule_id": "1.1" through "4.2",
  "comment": "short explanation"
}}

Never return markdown.
Never return additional fields.
Never return NONE.
Never return an invalid rule_id.

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
            "enum": [
                "ALLOWED",
                "NOT_ALLOWED"
            ]
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
# GROQ CLIENT
# ============================================================

@st.cache_resource(show_spinner=False)
def get_groq_client():

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:

        try:
            api_key = st.secrets["GROQ_API_KEY"]

        except Exception:
            api_key = None

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured."
        )

    return Groq(api_key=api_key)


# ============================================================
# MODEL CALL
# ============================================================

def call_model(
    review,
    language,
    model,
    reasoning_effort=None
):

    client = get_groq_client()

    prompt = build_prompt(
        review,
        language
    )

    kwargs = {

        "model": model,

        "messages": [

            {
                "role": "system",
                "content": (
                    "You are a strict Noon Product Review "
                    "moderation classifier. "
                    "Follow the structured Article policy exactly. "
                    "Return the required JSON only."
                )
            },

            {
                "role": "user",
                "content": prompt
            }
        ],

        "temperature": 0,

        "response_format": {
            "type": "json_schema",

            "json_schema": {
                "name": "review_moderation",
                "strict": True,
                "schema": REVIEW_SCHEMA
            }
        }
    }

    if reasoning_effort:
        kwargs["reasoning_effort"] = reasoning_effort

    response = client.chat.completions.create(
        **kwargs
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "Empty model response."
        )

    return json.loads(content)


# ============================================================
# VALIDATE RESULT
# ============================================================

def validate_result(result):

    if not isinstance(result, dict):
        raise ValueError(
            "Model result is not a dictionary."
        )

    decision = result.get("decision")
    rule_id = result.get("rule_id")
    comment = result.get("comment")

    if decision not in [
        "ALLOWED",
        "NOT_ALLOWED"
    ]:
        raise ValueError(
            "Invalid decision."
        )

    if rule_id not in RULES:
        raise ValueError(
            "Invalid rule_id."
        )

    if not isinstance(comment, str):
        raise ValueError(
            "Invalid comment."
        )

    return {
        "decision": decision,
        "rule_id": rule_id,
        "comment": comment.strip()
    }


# ============================================================
# HARD RULE OVERRIDE
# ============================================================

def apply_hard_rule(
    result,
    rule_id,
    language
):

    result = dict(result)

    result["decision"] = "NOT_ALLOWED"
    result["rule_id"] = rule_id

    if language == "Arabic":

        comments = {

            "1.1":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتضمن محتوى ترويجيًا أو إعلانيًا، مثل الترويج لمنتج أو متجر، مشاركة كود خصم، أو توجيه العملاء إلى وسيلة شراء أو تواصل. وفقًا للبند 1.1 من إرشادات تقييمات العملاء في نون، يجب أن يركز التقييم على تجربة العميل مع المنتج نفسه، ولذلك لا يمكن الإبقاء على هذا التقييم بصيغته الحالية.",

            "1.2":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتضمن ألفاظًا أو تعبيرات مسيئة أو مبتذلة أو غير لائقة أو غير مناسبة. وفقًا للبند 1.2 من إرشادات تقييمات العملاء في نون، هذا النوع من المحتوى يخالف قواعد المحتوى المسيء أو غير المناسب، ولذلك لا يمكن الإبقاء على التقييم.",

            "1.3":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتضمن خطاب كراهية أو محتوى تمييزيًا تجاه شخص أو فئة. وفقًا للبند 1.3 من إرشادات تقييمات العملاء في نون، لا يُسمح بالمحتوى الذي يتضمن كراهية أو تمييزًا، ولذلك لا يمكن الإبقاء على هذا التقييم.",

            "1.4":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتضمن معلومات شخصية أو حساسة، مثل رقم الهاتف أو البريد الإلكتروني أو عنوان أو بيانات يمكن استخدامها للتعرف على شخص. وفقًا للبند 1.4 من إرشادات تقييمات العملاء في نون، لا يُسمح بمشاركة هذا النوع من المعلومات داخل تقييم المنتج، ولذلك لا يمكن الإبقاء على التقييم.",

            "2.1":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يقدم ملاحظات عن البائع أو أدائه أو سمعته بدلًا من التركيز على تجربة العميل مع المنتج نفسه. وفقًا للبند 2.1 من إرشادات تقييمات العملاء في نون، تعليقات أداء البائع أو سمعته لا تُعد محتوى مناسبًا لتقييم المنتج، ولذلك لا يمكن الإبقاء على التقييم.",

            "2.2":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتناول تجربة الطلب أو الإرجاع، مثل إلغاء الطلب أو رفض الإرجاع أو مشكلة في استرداد المبلغ. وفقًا للبند 2.2 من إرشادات تقييمات العملاء في نون، يجب أن يركز التقييم على تجربة المنتج وليس على إجراءات الطلب أو الإرجاع، ولذلك لا يمكن الإبقاء على هذا التقييم.",

            "2.3":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتناول الشحن أو التغليف أو سرعة التوصيل أو تأخر وصول الطلب. وفقًا للبند 2.3 من إرشادات تقييمات العملاء في نون، هذه الملاحظات تتعلق بعملية التوصيل وليس بتجربة استخدام المنتج، ولذلك لا يمكن الإبقاء على التقييم.",

            "2.4":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يذكر أن المنتج وصل تالفًا أو مكسورًا أو أن جزءًا أو عنصرًا من المنتج مفقود. وفقًا للبند 2.4 من إرشادات تقييمات العملاء في نون، تعليقات التلف أو العناصر المفقودة تتعلق بحالة أو اكتمال الطلب عند الاستلام وليست بتجربة استخدام المنتج، ولذلك لا يمكن الإبقاء على التقييم.",

            "3.1":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يذكر أن العميل وجد نفس المنتج بسعر أرخص في مكان آخر أو يقارن سعر المنتج بسعر جهة أخرى. وفقًا للبند 3.1 من إرشادات تقييمات العملاء في نون، التعليقات التي تشير إلى العثور على المنتج بسعر أرخص في مكان آخر غير مسموح بها، ولذلك لا يمكن الإبقاء على التقييم.",

            "3.2":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتناول توفر المنتج أو حالة المخزون، مثل الإشارة إلى أن المنتج غير متوفر أو السؤال عن موعد توفره مرة أخرى. وفقًا للبند 3.2 من إرشادات تقييمات العملاء في نون، يجب ألا يتناول تقييم المنتج حالة المخزون أو توفره، ولذلك لا يمكن الإبقاء على التقييم.",

            "4.1":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يتضمن تعارضًا في المصالح أو يشير إلى علاقة بين كاتب التقييم والبائع أو الموظف أو المنافس أو جهة مرتبطة بالمنتج. وفقًا للبند 4.1 من إرشادات تقييمات العملاء في نون، يجب أن يكون التقييم تجربة عميل مستقلة، ولذلك لا يمكن الإبقاء على هذا التقييم.",

            "4.2":
                "بخصوص التقييم المذكور، يرجى العلم بأنه غير مسموح لأنه يشير إلى كتابة التقييم مقابل مقابل مادي أو منتج مجاني أو حافز مالي أو منفعة أخرى. وفقًا للبند 4.2 من إرشادات تقييمات العملاء في نون، التقييمات المنشورة مقابل تعويض أو حافز غير مسموح بها، ولذلك لا يمكن الإبقاء على التقييم.",
        }

    else:

        comments = {

            "1.1":
                "Regarding the submitted review, please note that it is not allowed because it contains promotional or advertising content, such as promoting a product or store, sharing a discount code, or directing customers to a purchasing or contact method. Under Section 1.1 of the Noon Customer Review guidelines, reviews should focus on the customer's experience with the product itself, so this review cannot remain in its current form.",

            "1.2":
                "Regarding the submitted review, please note that it is not allowed because it contains offensive, abusive, vulgar, inappropriate, or distasteful language. Under Section 1.2 of the Noon Customer Review guidelines, this type of content violates the rule covering offensive or inappropriate language, so the review cannot remain.",

            "1.3":
                "Regarding the submitted review, please note that it is not allowed because it contains hate speech or discriminatory content directed at a person or group. Under Section 1.3 of the Noon Customer Review guidelines, hate speech and discriminatory content are not allowed, so the review cannot remain.",

            "1.4":
                "Regarding the submitted review, please note that it is not allowed because it contains personal or sensitive information, such as a phone number, email address, physical address, or information that can directly identify a person. Under Section 1.4 of the Noon Customer Review guidelines, this type of information should not be included in a product review, so the review cannot remain.",

            "2.1":
                "Regarding the submitted review, please note that it is not allowed because it provides feedback about the seller's performance or reputation instead of focusing on the customer's experience with the product itself. Under Section 2.1 of the Noon Customer Review guidelines, seller performance or reputation feedback is not permitted in a product review, so the review cannot remain.",

            "2.2":
                "Regarding the submitted review, please note that it is not allowed because it discusses the ordering or return experience, such as an order cancellation, rejected return, or refund issue. Under Section 2.2 of the Noon Customer Review guidelines, reviews should focus on the product experience rather than the order or return process, so the review cannot remain.",

            "2.3":
                "Regarding the submitted review, please note that it is not allowed because it discusses shipping, packaging, delivery speed, or a delayed delivery. Under Section 2.3 of the Noon Customer Review guidelines, these comments concern the delivery process rather than the product experience, so the review cannot remain.",

            "2.4":
                "Regarding the submitted review, please note that it is not allowed because it reports that the product arrived damaged or broken, or that an item, part, or accessory was missing. Under Section 2.4 of the Noon Customer Review guidelines, damage and missing-item comments concern the condition or completeness of the delivered order rather than the normal product experience, so the review cannot remain.",

            "3.1":
                "Regarding the submitted review, please note that it is not allowed because it states that the customer found the same product cheaper elsewhere or compares the product's price with another seller or source. Under Section 3.1 of the Noon Customer Review guidelines, comments about finding the product cheaper elsewhere are not allowed, so the review cannot remain.",

            "3.2":
                "Regarding the submitted review, please note that it is not allowed because it discusses the product's stock status or availability, such as saying that the item is unavailable or asking when it will be available again. Under Section 3.2 of the Noon Customer Review guidelines, stock and availability comments are not allowed in a product review, so the review cannot remain.",

            "4.1":
                "Regarding the submitted review, please note that it is not allowed because it indicates a conflict of interest or a relationship between the reviewer and the seller, employee, competitor, or another party connected to the product. Under Section 4.1 of the Noon Customer Review guidelines, reviews must represent an independent customer experience, so this review cannot remain.",

            "4.2":
                "Regarding the submitted review, please note that it is not allowed because it indicates that the review was submitted in exchange for compensation, a free product, a financial incentive, or another benefit. Under Section 4.2 of the Noon Customer Review guidelines, reviews submitted in exchange for compensation or incentives are not allowed, so the review cannot remain.",
        }

    result["comment"] = comments.get(
        rule_id,
        result.get("comment", "")
    )

    return result


# ============================================================
# OFFENSIVE LANGUAGE OVERRIDE
# ============================================================

def apply_offensive_rule(
    result,
    language
):

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

def apply_allowed_rule(
    result,
    review,
    language
):

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

def call_adjudicator(
    review,
    language,
    first_result
):

    structured_policy = build_structured_policy_text()

    adjudicator_prompt = f"""
You are the final quality-control reviewer for Noon Product Reviews.

Your task is to independently verify the first classifier result.

============================================================
STRUCTURED NOON ARTICLE POLICY
============================================================

{structured_policy}

============================================================
FIRST CLASSIFIER RESULT
============================================================

{json.dumps(
    first_result,
    ensure_ascii=False
)}

============================================================
CUSTOMER REVIEW
============================================================

{review}

============================================================
QUALITY CONTROL RULES
============================================================

Normal product criticism = ALLOWED.

Do not mark a review NOT_ALLOWED merely because it is:

- negative,
- disappointed,
- critical,
- poorly written,
- a simple mention of an order,
- a simple mention of a seller,
- a simple mention of price,
- a general wish for more colors or sizes.

A clear Article violation must be NOT_ALLOWED.

Use the most direct applicable rule.

Specific reminders:

1.1 = Promotional or advertising content.

1.2 = Offensive, abusive, inappropriate, vulgar, or distasteful language.

1.3 = Hate speech or discriminatory remarks.

1.4 = Personal or sensitive information.

2.1 = Seller performance or reputation.

2.2 = Ordering or return experiences.

2.3 = Shipping, packaging, or delivery speed.

2.4 = Product damage or missing items.

3.1 = Finding the same product cheaper elsewhere.

3.2 = Actual stock status or store-level availability.

4.1 = Conflict of interest or non-independent review.

4.2 = Compensation, financial incentive, free product, or another benefit.

============================================================
DECISION
============================================================

If a clear Article violation exists:
NOT_ALLOWED.

Otherwise:
ALLOWED.

Return ONLY valid JSON with:

decision
rule_id
comment

No markdown.
No additional fields.
"""

    client = get_groq_client()

    response = client.chat.completions.create(

        model=PRIMARY_MODEL,

        messages=[

            {
                "role": "system",
                "content": (
                    "You are a final quality-control reviewer. "
                    "Follow the structured Noon Product Review "
                    "Article exactly and return JSON only."
                )
            },

            {
                "role": "user",
                "content": adjudicator_prompt
            }
        ],

        temperature=0,

        reasoning_effort="low",

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
        raise ValueError(
            "Empty adjudicator response."
        )

    return validate_result(
        json.loads(content)
    )


# ============================================================
# SECOND REVIEW DECISION
# ============================================================

def should_run_second_review(
    review,
    first_result
):

    decision = first_result.get(
        "decision"
    )

    # NOT_ALLOWED AI results get verification.
    if decision == "NOT_ALLOWED":
        return True

    text = normalize_text(review)

    ambiguous_cues = [

        "seller",
        "البائع",
        "البايع",

        "order",
        "ordered",
        "return",
        "refund",
        "طلب",
        "ارجاع",
        "استرجاع",

        "delivery",
        "shipping",
        "package",
        "packaging",
        "توصيل",
        "شحن",
        "تغليف",

        "price",
        "cheaper",
        "expensive",
        "سعر",
        "ارخص",

        "stock",
        "available",
        "availability",
        "متوفر",
        "مخزون",

        "promo",
        "discount",
        "coupon",
        "كود",
        "خصم",

        "email",
        "phone",
        "address",
        "رقم",
        "ايميل",
        "عنوان",

        "competitor",
        "employee",
        "manufacturer",
        "paid",
        "free product",

        "منافس",
        "موظف",
        "مصنع",
        "مدفوع",
        "فلوس",
        "منتج مجاني"
    ]

    return any(
        cue in text
        for cue in ambiguous_cues
    )


# ============================================================
# RELIABLE EVALUATION
# ============================================================

def evaluate_with_reliability(
    review,
    language
):

    # --------------------------------------------------------
    # FIRST: DETERMINISTIC ARTICLE RULES
    # --------------------------------------------------------

    hard_rule = detect_hard_rules(review)

    if not hard_rule:

        hard_rule = detect_high_confidence_article_rule(
            review
        )

    clear_offensive = (
        detect_clear_offensive_language(
            review
        )
    )

    # --------------------------------------------------------
    # INSTANT FINALIZATION
    # --------------------------------------------------------

    deterministic_rule = hard_rule

    if (
        clear_offensive
        and not deterministic_rule
    ):
        deterministic_rule = "1.2"

    if deterministic_rule:

        result = {
            "decision": "NOT_ALLOWED",
            "rule_id": deterministic_rule,
            "comment": ""
        }

        return apply_hard_rule(
            result,
            deterministic_rule,
            language
        )

    # --------------------------------------------------------
    # FIRST AI CALL
    # --------------------------------------------------------

    try:

        first_result = call_model(
            review,
            language,
            PRIMARY_MODEL,
            reasoning_effort="low"
        )

        first_result = validate_result(
            first_result
        )

    except Exception:

        try:

            first_result = call_model(
                review,
                language,
                FALLBACK_MODEL,
                reasoning_effort="low"
            )

            first_result = validate_result(
                first_result
            )

        except Exception:
            raise

    # --------------------------------------------------------
    # SECOND AI REVIEW
    # --------------------------------------------------------

    if should_run_second_review(
        review,
        first_result
    ):

        try:

            final_result = call_adjudicator(
                review,
                language,
                first_result
            )

        except Exception:

            final_result = first_result

    else:

        final_result = first_result

    # --------------------------------------------------------
    # FINAL DETERMINISTIC SAFETY CHECK
    # --------------------------------------------------------

    if detect_clear_offensive_language(
        review
    ):

        final_result = apply_offensive_rule(
            final_result,
            language
        )

    # --------------------------------------------------------
    # FINAL ALLOWED NORMALIZATION
    # --------------------------------------------------------

    if final_result["decision"] == "ALLOWED":

        final_result = apply_allowed_rule(
            final_result,
            review,
            language
        )

    return validate_result(
        final_result
    )


# ============================================================
# MAIN EVALUATION
# ============================================================

def evaluate_review(
    review,
    language
):

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


def reset_tool():

    st.session_state["review_input"] = ""

    st.session_state["review_result"] = None

    st.session_state["copy_comment"] = ""


# ============================================================
# UI
# ============================================================

st.title(
    "Product Review Moderation Tool"
)


# ------------------------------------------------------------
# LANGUAGE
# ------------------------------------------------------------

language = st.radio(
    "Language",
    ["English", "Arabic"],
    horizontal=True
)


# ============================================================
# GUIDELINES LINK
# ============================================================

st.markdown(
    """
    <div style="margin-top: 20px;">

        <a
            href="https://help.noon.com/portal/en/kb/articles/product-review-guidelines"
            target="_blank"
        >
            Noon Customer Reviews Guidelines
        </a>

    </div>
    """,
    unsafe_allow_html=True
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
# BUTTON STYLE
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

        with st.spinner(
            "Evaluating review..."
        ):

            result = evaluate_review(
                review,
                language
            )

            st.session_state[
                "review_result"
            ] = result

    except Exception as e:

        st.error(
            f"An error occurred while evaluating the review: {str(e)}"
        )


# ============================================================
# RESULT DISPLAY
# ============================================================

if st.session_state.get(
    "review_result"
):

    result = st.session_state[
        "review_result"
    ]

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

    copy_text = (
        comment
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
    )

    components.html(
        f"""
        <script>

        function copyComment() {{

            navigator.clipboard.writeText(
                '{copy_text}'
            );

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
    """
    <div style="margin-top: 20px;">

        <a
            href="https://help.noon.com/portal/en/kb/articles/product-review-guidelines"
            target="_blank"
        >
            Noon Customer Reviews Guidelines
        </a>

    </div>
    """,
    unsafe_allow_html=True
)
