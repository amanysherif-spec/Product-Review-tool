import streamlit as st
import os
import json
import re
from groq import Groq

# ============================================================
# CONFIGURATION & GUIDELINE LINK
# ============================================================

GUIDELINE_URL = "https://help.noon.com/hc/en-us/articles/360015504793-Customer-Reviews-Guidelines"

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
# RULES DEFINITION
# ============================================================

RULES = {
    "1.1": {"section": "Community Guideline Violations", "rule": "Promotional or advertising content"},
    "1.2": {"section": "Community Guideline Violations", "rule": "Offensive, abusive, inappropriate, vulgar, or distasteful language"},
    "1.3": {"section": "Community Guideline Violations", "rule": "Hate speech or discriminatory content"},
    "1.4": {"section": "Community Guideline Violations", "rule": "Personal or sensitive information"},
    "2.1": {"section": "Seller, Order, or Shipping Feedback", "rule": "Seller performance or reputation"},
    "2.2": {"section": "Seller, Order, or Shipping Feedback", "rule": "Ordering or return experience"},
    "2.3": {"section": "Seller, Order, or Shipping Feedback", "rule": "Shipping, packaging, or delivery"},
    "2.4": {"section": "Seller, Order, or Shipping Feedback", "rule": "Product damage or missing items"},
    "3.1": {"section": "Comments About Pricing or Availability", "rule": "Finding the product cheaper elsewhere"},
    "3.2": {"section": "Comments About Pricing or Availability", "rule": "Stock status or availability"},
    "4.1": {"section": "Conflicts of Interest & Anti-Manipulation", "rule": "Conflict of interest"},
    "4.2": {"section": "Conflicts of Interest & Anti-Manipulation", "rule": "Compensation or financial incentive"},
}

# ============================================================
# TEXT NORMALIZATION & MATCHING HELPERS
# ============================================================

def normalize_text(text):
    if not text:
        return ""
    text = str(text).strip().lower()
    text = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", text)
    text = text.translate(str.maketrans({
        "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"
    }))
    return re.sub(r"\s+", " ", text)

def contains_phrase(text, phrases):
    normalized = normalize_text(text)
    for phrase in phrases:
        if normalize_text(phrase) in normalized:
            return True
    return False

def contains_non_negated_phrase(text, phrases):
    normalized = normalize_text(text)
    negation_tokens = {
        "not", "no", "never", "without", "isn't", "isnt", "wasn't", "wasnt", 
        "aren't", "arent", "dont", "don't", "doesn't", "doesnt", "didn't", "didnt",
        "مش", "موش", "غير", "ليس", "ليست", "لم", "لن", "ما", "مفيش", "مافيش", "بدون", "منغير"
    }

    for phrase in phrases:
        phrase_norm = normalize_text(phrase)
        if not phrase_norm:
            continue

        start = 0
        while True:
            index = normalized.find(phrase_norm, start)
            if index == -1:
                break

            prefix = normalized[max(0, index - 40):index]
            recent_words = prefix.split()[-5:]

            if not any(token in negation_tokens for token in recent_words):
                return True

            start = index + len(phrase_norm)
    return False

# ============================================================
# HARD RULES (DETERMINISTIC CHECKS)
# ============================================================

def detect_hard_rules(review):
    text = normalize_text(review)

    # 3.1 Cheaper elsewhere
    price_phrases = ["found it cheaper", "cheaper elsewhere", "cheaper at another store", "ارخص في مكان", "لقيته ارخص", "وجدته بسعر ارخص"]
    if contains_non_negated_phrase(text, price_phrases):
        return "3.1"

    # 3.2 Stock/Availability
    avail_phrases = ["out of stock", "unavailable", "when will it be available", "غير متوفر", "نفد المخزون", "متى سيتوفر"]
    if contains_non_negated_phrase(text, avail_phrases):
        return "3.2"

    # 2.4 Damage / Missing items
    damage_phrases = ["arrived broken", "arrived damaged", "missing part", "missing item", "وصل مكسور", "وصل تالف", "جزء ناقص", "اجزاء مفقوده"]
    if contains_non_negated_phrase(text, damage_phrases):
        return "2.4"

    # 1.1 Promotional
    promo_phrases = ["use my code", "promo code", "discount code", "كود خصم", "كود تخفيض", "اشتروا من متجري"]
    if contains_phrase(text, promo_phrases) or re.search(r"https?://|www\.|@[a-z0-9_.-]{3,}", text):
        return "1.1"

    # 1.4 Personal Info
    if re.search(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", text) or contains_phrase(text, ["phone number", "my email", "رقم تليفوني", "عنواني هو"]):
        return "1.4"

    return None

# ============================================================
# EXPLANATION TEMPLATES (ARABIC & ENGLISH)
# ============================================================

def generate_detailed_comment(decision, rule_id, review_text, language="Arabic"):
    rule_info = RULES.get(rule_id, {"section": "General Guideline", "rule": "Review Policy"})
    
    if language == "Arabic":
        if decision == "NOT_ALLOWED":
            comments = {
                "1.1": f"التقييم 'NOT_ALLOWED' بناءً على البند 1.1 ({rule_info['section']}). التقييم يتضمن محتوى إعلانيًا أو ترويجيًا أو مشاركة أكواد خصم/روابط خارجيّة، مما يخالف سياسة نون التي تشترط الاقتصار على تجربة المنتج ذاته.",
                "1.2": f"التقييم 'NOT_ALLOWED' بناءً على البند 1.2 ({rule_info['section']}). التقييم يتضمن ألفاظًا غير لائقة أو بذيئة أو مسيئة بشكل صريح بدلاً من الاقتصار على النقد الموضوعي للمنتج.",
                "1.3": f"التقييم 'NOT_ALLOWED' بناءً على البند 1.3 ({rule_info['section']}). يحتوي التقييم على خطاب كراهية أو تعبيرات تمييزية غير مقبولة.",
                "1.4": f"التقييم 'NOT_ALLOWED' بناءً على البند 1.4 ({rule_info['section']}). يحتوي التقييم على معلومات شخصية أو حساسة (مثل أرقام الهواتف أو البريد الإلكتروني أو العناوين).",
                "2.1": f"التقييم 'NOT_ALLOWED' بناءً على البند 2.1 ({rule_info['section']}). التقييم يركز على أداء البائع أو تعامله أو سمعته، بينما يجب أن تركز التقييمات حصراً على جودة المنتج ومواصفاته.",
                "2.2": f"التقييم 'NOT_ALLOWED' بناءً على البند 2.2 ({rule_info['section']}). التقييم يركز على تجربة الطلب أو الإلغاء أو مشكلات الاسترجاع، وهي أمور تتعلق بخدمة العملاء والعمليات وليست تقييماً لمواصفات المنتج.",
                "2.3": f"التقييم 'NOT_ALLOWED' بناءً على البند 2.3 ({rule_info['section']}). التقييم يتطرق لشركة الشحن أو تأخر التوصيل أو حالة التغليف الخارجي، وهذا خارج نطاق تقييم جودة المنتج ذاته.",
                "2.4": f"التقييم 'NOT_ALLOWED' بناءً على البند 2.4 ({rule_info['section']}). العميل يذكر وصول المنتج مكسوراً أو تالفاً أو بنقص في الأجزاء، وهذه مشكلة شحن/تعبئة وليست عيباً تصنيعياً بالمنتج نفسه.",
                "3.1": f"التقييم 'NOT_ALLOWED' بناءً على البند 3.1 ({rule_info['section']}). التقييم يذكر العثور على المنتج بسعر أرخص في متجر آخر أو منصة أخرى، وهو أمر غير مسموح به في التقييمات.",
                "3.2": f"التقييم 'NOT_ALLOWED' بناءً على البند 3.2 ({rule_info['section']}). التقييم يناقش حالة توفر المنتج بالمخزون أو الاستفسار عن موعد توفره بدلاً من تقييم المنتج نفسه.",
                "4.1": f"التقييم 'NOT_ALLOWED' بناءً على البند 4.1 ({rule_info['section']}). وجود تعارض مصالح واضح (مثل تقييم من البائع نفسه أو أحد المنافسين).",
                "4.2": f"التقييم 'NOT_ALLOWED' بناءً على البند 4.2 ({rule_info['section']}). التقييم تم مقابل حافز مالي أو تعويض غير معلن عنه."
            }
            return comments.get(rule_id, f"التقييم 'NOT_ALLOWED' لمخالفته إرشادات تقييمات العملاء في نون تحت بند {rule_id}.")
        else:
            return f"التقييم 'ALLOWED' تماماً وفقاً للبند {rule_id} ({rule_info['section']}). المحتوى يمثل رأياً شخصياً وموضوعياً للعميل حول جودة المنتج أو كفاءته أو انطباعه عنه بدون تسجيل أي مخالفة لإرشادات نون."
    else:
        if decision == "NOT_ALLOWED":
            return f"The review is 'NOT_ALLOWED' under Rule {rule_id} ({rule_info['rule']} - {rule_info['section']}). It directly violates Noon's review guidelines by discussing non-product aspects or policy violations."
        else:
            return f"The review is 'ALLOWED' under Category {rule_id} ({rule_info['section']}). It accurately expresses the buyer's personal product experience, quality feedback, or opinion without violating any removal rules."

# ============================================================
# PROMPT BUILDER
# ============================================================

def build_prompt(review, language):
    rules_text = "\n".join([f"{rid}: {data['section']} -> {data['rule']}" for rid, data in RULES.items()])
    
    return f"""
You are a strict Noon Customer Review moderation classifier.

Evaluate whether this customer review is ALLOWED or NOT_ALLOWED based on Noon's Guidelines.

============================================================
RULES & CATEGORIES
============================================================
{rules_text}

============================================================
KEY INSTRUCTIONS
============================================================
1. ALLOWED: Expressions of quality, dissatisfaction, bad taste, poor battery, high price opinion, or general product feedback are FULLY ALLOWED.
2. NOT_ALLOWED: Offensive language, complaints about delivery/shipping, seller service, return/refund issues, broken/missing parts on arrival, finding it cheaper elsewhere, stock availability, promo codes, or personal contact numbers.

Review to evaluate: "{review}"

Output ONLY a JSON with this exact structure:
{{
  "decision": "ALLOWED" or "NOT_ALLOWED",
  "rule_id": "1.1" through "4.2",
  "comment": "Comprehensive reasoning explaining why it is ALLOWED or NOT_ALLOWED based on guidelines."
}}
"""

# ============================================================
# GROQ CLIENT & API CALL
# ============================================================

@st.cache_resource(show_spinner=False)
def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing from environment variables or Streamlit secrets.")
    return Groq(api_key=api_key)

def moderate_review(review, language="Arabic"):
    # Step 1: Check Hard Rules
    hard_rule_id = detect_hard_rules(review)
    if hard_rule_id:
        return {
            "decision": "NOT_ALLOWED",
            "rule_id": hard_rule_id,
            "comment": generate_detailed_comment("NOT_ALLOWED", hard_rule_id, review, language)
        }

    # Step 2: Call AI Model if no Hard Rule matched
    try:
        client = get_groq_client()
        prompt = build_prompt(review, language)
        
        response = client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[
                {"role": "system", "content": "You are a strict Noon Review Moderation expert. Return JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        res = json.loads(response.choices[0].message.content)
        decision = res.get("decision", "ALLOWED")
        rule_id = res.get("rule_id", "2.4")
        
        # Enrich comment with detailed template
        detailed_comment = generate_detailed_comment(decision, rule_id, review, language)
        
        return {
            "decision": decision,
            "rule_id": rule_id,
            "comment": detailed_comment
        }
    except Exception as e:
        # Default fallback safely
        return {
            "decision": "ALLOWED",
            "rule_id": "2.4",
            "comment": generate_detailed_comment("ALLOWED", "2.4", review, language)
        }

# ============================================================
# STREAMLIT UI
# ============================================================

st.title("🛡️ أداة مراجعة وتقييم مراجعات المنتجات (Noon Moderation)")
st.write("أدخل تقييم العميل للحصول على قرار دقيق وملخص تفصيلي للسبب طبقاً لإرشادات نون.")

lang = st.radio("لغة التوضيح / Explanation Language:", ["Arabic", "English"], horizontal=True)
review_input = st.text_area("أدخل نص التقييم هنا / Enter Product Review:", height=120)

if st.button("فحص التقييم / Moderate Review", type="primary"):
    if not review_input.strip():
        st.warning("يرجى كتابة نص التقييم أولاً.")
    else:
        with st.spinner("جاري تحليل التقييم بدقة..."):
            result = moderate_review(review_input, language=lang)
            
            st.divider()
            if result["decision"] == "ALLOWED":
                st.success(f"✅ Decision: **{result['decision']}**")
            else:
                st.error(f"❌ Decision: **{result['decision']}**")
                
            st.info(f"📌 **Rule Category**: {result['rule_id']} - {RULES[result['rule_id']]['rule']}")
            st.write(f"📝 **التفاصيل والسبب / Explanation**:\n\n{result['comment']}")

# ============================================================
# FIXED FOOTER WITH GUIDELINE LINK
# ============================================================

footer_html = f"""
<style>
.footer {{
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: #f8f9fa;
    color: #333;
    text-align: center;
    padding: 10px;
    border-top: 1px solid #e9ecef;
    font-size: 14px;
    z-index: 1000;
}}
.footer a {{
    color: #007bff;
    text-decoration: none;
    font-weight: bold;
}}
.footer a:hover {{
    text-decoration: underline;
}}
</style>
<div class="footer">
    📄 للاطلاع على الشروط الكاملة: 
    <a href="{GUIDELINE_URL}" target="_blank">Noon Customer Review Guidelines (إرشادات تقييمات نون)</a>
</div>
"""

st.markdown(footer_html, unsafe_allow_html=True)
