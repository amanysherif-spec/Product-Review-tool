import streamlit as st

import os

import streamlit.components.v1 as components

import json

import re

import time

import hashlib

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

# NOON CUSTOMER REVIEW GUIDELINES

# ============================================================



RULES = {

    "1.1": {

        "section": "Community Guideline Violations",

        "rule": "Promotional or advertising content",

    },

    "1.2": {

        "section": "Community Guideline Violations",

        "rule": "Offensive, abusive, inappropriate, vulgar, or distasteful language",

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

        "section": "Conflicts of Interest & Anti-Manipulation",

        "rule": "Conflict of interest",

    },

    "4.2": {

        "section": "Conflicts of Interest & Anti-Manipulation",

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





def contains_non_negated_phrase(text, phrases):

    """

    Detect a policy phrase unless the phrase is explicitly negated.



    This prevents false positives such as:

        - not broken

        - not damaged

        - no missing parts

        - not cheaper elsewhere

        - المنتج مش مكسور

        - المنتج غير تالف

    """



    normalized = normalize_text(text)



    negation_tokens = {

        "not", "no", "never", "without", "isn't", "isnt",

        "wasn't", "wasnt", "aren't", "arent", "dont", "don't",

        "doesn't", "doesnt", "didn't", "didnt",

        "مش", "موش", "مشا", "غير", "ليس", "ليست", "لم", "لن",

        "ما", "مفيش", "مافيش", "بدون", "منغير", "من غير"

    }



    for phrase in phrases:

        phrase_normalized = normalize_text(phrase)

        if not phrase_normalized:

            continue



        start = 0

        while True:

            index = normalized.find(phrase_normalized, start)

            if index == -1:

                break



            prefix = normalized[max(0, index - 40):index]

            prefix_words = prefix.split()



            # Check the few words immediately before the matched phrase.

            # We deliberately keep this local to avoid suppressing a real

            # violation because of an unrelated negation elsewhere.

            recent_words = prefix_words[-5:]



            if not any(token in negation_tokens for token in recent_words):

                return True



            start = index + len(phrase_normalized)



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

        "more expensive here than elsewhere",

        "more expensive than another store",

        "more expensive than elsewhere",

        "more expensive here compared with another store",

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



    if contains_non_negated_phrase(text, price_phrases):

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



    if contains_non_negated_phrase(text, availability_phrases):

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



    if contains_non_negated_phrase(text, damage_phrases):

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



    if contains_non_negated_phrase(text, missing_phrases):

        return "2.4"





    return None





# ============================================================

# HIGH CONFIDENCE OFFENSIVE LANGUAGE DETECTION

# ============================================================



def detect_clear_offensive_language(review):

    """

    High-confidence offensive / vulgar / distasteful phrases.



    This is intentionally not a generic negative-word detector.

    Normal criticism such as:

        bad

        poor quality

        not useful

        I don't like it

    should remain allowed.



    Contextual offensive language is primarily handled by the AI.

    """



    text = normalize_text(review)



    offensive_phrases = [



        # ----------------------------------------------------

        # ENGLISH - HIGH CONFIDENCE

        # ----------------------------------------------------



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

        if normalize_text(phrase) in text:

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



    rules_text = "\n".join(

        [

            f"{rule_id}: {data['section']} -> {data['rule']}"

            for rule_id, data in RULES.items()

        ]

    )



    return f"""

You are a strict Noon Customer Review moderation classifier.



Your job is to determine whether the customer review is ALLOWED

or NOT_ALLOWED according to the Noon Customer Reviews Article.



{language_instruction}



============================================================

NOON CUSTOMER REVIEW GUIDELINES

============================================================



{rules_text}



============================================================

IMPORTANT GENERAL PRINCIPLES

============================================================



1. Reviews should focus solely on the customer's personal

   experience with the product purchased.



2. Normal product criticism is allowed.



Examples of ALLOWED normal criticism:



- The product is bad.

- The quality is poor.

- The battery drains quickly.

- The product is not useful.

- I don't like the product.

- The product disappointed me.

- المنتج سيء

- المنتج وحش

- مش عاجبني المنتج

- المنتج مش مفيد

- البطارية بتخلص بسرعة

- المنتج لم يعجبني



These are opinions about the product and are NOT automatically

offensive language.



============================================================

OFFENSIVE / INAPPROPRIATE LANGUAGE

============================================================



Any genuinely offensive, abusive, vulgar, inappropriate, or

distasteful language must be classified as NOT_ALLOWED under 1.2.



This applies to both English and Arabic.



Examples that MUST be NOT_ALLOWED:



- disgusting product

- This product is disgusting

- The product is disgusting

- What a disgusting product

- fucking garbage

- piece of shit

- shit product

- fuck this

- fuck you



Arabic examples that MUST be NOT_ALLOWED:



- المنتج مقرف

- منتج مقرف

- المنتج زبالة

- منتج زبالة

- يا غبي

- البائع غبي

- المنتج وسخ

- المنتج زفت

- خرا

- قرف

- ألفاظ بذيئة أو مهينة أو غير لائقة



IMPORTANT:



Do not confuse ordinary negative product feedback with offensive

language.



For example:



"The product is bad"

"The quality is poor"

"I don't like it"

"المنتج سيء"



must remain ALLOWED unless another guideline is violated.



However, if the wording is genuinely vulgar, abusive, insulting,

inappropriate, or distasteful according to normal language usage,

classify it as NOT_ALLOWED under 1.2.



Use contextual understanding, not only keyword matching.



============================================================

PRICING

============================================================



A review saying that the customer found the same product cheaper

elsewhere is NOT_ALLOWED under 3.1.



Examples:



- Found it cheaper elsewhere

- I found it cheaper in another store

- Same product is cheaper somewhere else

- لقيته ارخص في مكان تاني

- وجدته بسعر ارخص



These MUST be NOT_ALLOWED.



However, normal value-for-money opinions are allowed:



- Great quality for the price.

- Good product for this price.

- The price is reasonable.



============================================================

AVAILABILITY

============================================================



Comments specifically about stock or availability are NOT_ALLOWED

under 3.2.



Examples:



- Out of stock

- When will it be available?

- It is no longer available.

- المنتج غير متوفر

- متى سيتوفر؟



General product wishes are allowed:



- Hope it comes in more colors.

- I wish there were more sizes.



============================================================

DAMAGE / MISSING ITEMS

============================================================



If the review complains that the purchased product arrived broken,

damaged, or with missing parts/items, classify it as NOT_ALLOWED

under 2.4.



============================================================

OTHER VIOLATIONS

============================================================



1.1:

Promotional or advertising content.



1.3:

Hate speech or discriminatory content.



1.4:

Personal or sensitive information.



2.1:

Seller performance or seller reputation.



2.2:

Ordering or return experience.



2.3:

Shipping, packaging, or delivery issues.



4.1:

Conflict of interest, including reviews written by seller,

competitor, employee, friend, family member, or business partner.



4.2:

Reviews posted in exchange for compensation, financial incentive,

or other benefit.



============================================================

IMPORTANT CLASSIFICATION RULE

============================================================



If there is a clear guideline violation, choose NOT_ALLOWED.



If there is no guideline violation, choose ALLOWED.



Do not invent a violation simply because the review is negative.



FINAL QUALITY CHECK BEFORE RETURNING THE JSON:

1. Read the full review, including mixed Arabic/English wording.

2. Identify the exact words or meaning that support the selected rule.

3. The selected rule must be directly supported by the review itself.

4. Do not infer seller, order, delivery, pricing, stock, compensation,

   conflict-of-interest, or personal-information violations from unrelated

   mentions of those topics.

5. A normal opinion about product quality, taste, effectiveness, size,

   value, usefulness, or satisfaction is ALLOWED unless a specific Article

   violation is actually present.

6. If the evidence does not clearly support a removal rule, choose ALLOWED.

7. For NOT_ALLOWED, select the most directly applicable rule only.



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



    prompt = build_prompt(review, language)



    kwargs = {

        "model": model,

        "messages": [

            {

                "role": "system",

                "content": (

                    "You are a strict Noon Customer Review "

                    "moderation classifier. Follow the supplied "

                    "guidelines exactly. Return the required JSON only."

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



    response = client.chat.completions.create(**kwargs)



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

                "وفقًا للبند 1.2 من إرشادات تقييمات العملاء في نون، هذا النوع من المحتوى يخالف قواعد المحتوى المسيء أو غير ا 

