import os
import re
import random
from datetime import datetime

import pandas as pd
import streamlit as st
from fuzzywuzzy import fuzz
from google import genai
from google.genai import types

# =====================================================================
# 0. PAGE CONFIG
# =====================================================================
st.set_page_config(
    page_title="MediMind AI | Smart Health Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================================
# 5. SESSION STATE & LANGUAGE SETUP (Moved up for global access)
# =====================================================================
DEFAULTS = dict(
    lang="हिंदी", temp_c=36.6, temp_f=97.9, pain="0 - No Pain / कोई दर्द नहीं", spo2=98, pulse=78, 
    weight=70.0, height=170.0, unit="°C", name="", age=25, gender="Male / पुरुष", 
    symptoms=[], symptom_text="", duration="1-2 days / दिन",
    chat=[], history=[], log=[], water=0, sleep=7.0, result=None,
)
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

def t(en, hi):
    """Helper to switch text based on selected language."""
    return en if st.session_state.get("lang", "हिंदी") == "English" else hi

def reset_inputs():
    for k in ("temp_c", "temp_f", "spo2", "pulse", "weight", "height", "symptoms", "symptom_text"):
        st.session_state[k] = DEFAULTS[k]
    st.session_state.pain = PAIN_OPTIONS[0]
    st.session_state.duration = DURATION_OPTIONS[1]
    st.session_state.result = None

# =====================================================================
# 1. GEMINI SETUP
# =====================================================================
MODEL_NAME = "gemini-2.5-flash"
client = None
GEMINI_ENABLED = False
try:
    API_KEY = os.environ.get("GEMINI_API_KEY")
    if not API_KEY:
        try:
            API_KEY = st.secrets.get("GEMINI_API_KEY")  # local dev fallback
        except Exception:
            API_KEY = None
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY not found")
    client = genai.Client(api_key=API_KEY)
    GEMINI_ENABLED = True
except Exception:
    GEMINI_ENABLED = False

STYLE_RULES = (
    "You are MediMind AI, a friendly and careful health assistant for users in India. "
    "Be concise, use short bullet points, give practical home-care tips, and clearly say when "
    "to see a doctor or call 108. Never give dosages for prescription-only drugs. "
    "You are not a replacement for a doctor. "
)

def ask_gemini(prompt: str, search: bool = False):
    """Returns (text, error). Exactly one of them is None."""
    if not GEMINI_ENABLED:
        return None, t("Gemini API key is not configured.", "Gemini API key configure nahi hai (GEMINI_API_KEY).")
    
    # Enforce language
    lang_prompt = f"{prompt}\n\nIMPORTANT: You must reply entirely in {st.session_state.lang}."
    
    try:
        cfg = None
        if search:
            cfg = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        r = client.models.generate_content(model=MODEL_NAME, contents=lang_prompt, config=cfg)
        return (r.text or "").strip(), None
    except Exception as e:
        msg = str(e)
        if any(k in msg for k in ("503", "429", "UNAVAILABLE", "rate")):
            return None, t("Server busy or limit reached. Try later.", "Server abhi busy hai ya limit khatam ho gayi. Thodi der baad try karein.")
        return None, f"Gemini error: {msg}"

def show_ai(ans, err):
    if ans:
        st.markdown(ans)
    else:
        st.error(err or t("No response received.", "जवाब नहीं मिला।"))

# =====================================================================
# 2. DESIGN SYSTEM (CSS)
# =====================================================================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;700;800&family=Hind:wght@400;500;600&display=swap');
:root{
  --ink:#0b1820; --panel:#11242e; --panel-2:#16303c; --line:#24424f;
  --text:#e6f0ee; --muted:#8fa9b0;
  --teal:#47d1c0; --coral:#ff7a6b; --amber:#f4c05a; --leaf:#6fd39a; --orange:#fb9a52;
}
html, body, .stApp, [class*="css"]{ font-family:'Hind','Noto Sans Devanagari',sans-serif; }
.stApp{ background:var(--ink); color:var(--text); }
h1,h2,h3,h4,.display{ font-family:'Bricolage Grotesque','Hind',sans-serif !important; letter-spacing:-.01em; }
#MainMenu, footer{ visibility:hidden; }
header[data-testid="stHeader"]{ background:transparent; }
.block-container{ padding-top:1.4rem; max-width:1180px; }
.hero{
  position:relative; overflow:hidden; border-radius:26px; padding:34px 38px 30px;
  background:linear-gradient(135deg,#123241 0%,#0e2530 60%,#0b1820 100%);
  border:1px solid var(--line); margin-bottom:18px;
}
.hero h1{ font-size:3.1rem; font-weight:800; margin:0 0 6px; color:var(--text); line-height:1.05; }
.hero p{ color:var(--muted); font-size:1.08rem; margin:0; max-width:560px; }
.hero .pills{ margin-top:18px; display:flex; gap:10px; flex-wrap:wrap; }
.pill{ border:1px solid var(--line); border-radius:999px; padding:5px 14px; font-size:.86rem; color:var(--text); background:rgba(255,255,255,.03); }
.pill.on{ border-color:var(--teal); color:var(--teal); }
.pill.off{ border-color:var(--coral); color:var(--coral); }
.ecg{ position:absolute; right:-10px; bottom:12px; width:58%; opacity:.9; pointer-events:none; }
.ecg path{ fill:none; stroke:var(--teal); stroke-width:3; stroke-linecap:round; stroke-linejoin:round;
  stroke-dasharray:1400; stroke-dashoffset:1400; animation:draw 2.8s ease-out forwards; }
@keyframes draw{ to{ stroke-dashoffset:0; } }
@media (prefers-reduced-motion:reduce){ .ecg path{ animation:none; stroke-dashoffset:0; } }
@media (max-width:760px){ .hero h1{font-size:2.1rem;} .ecg{opacity:.25; width:90%;} .hero{padding:24px 20px;} }
.stTabs [data-baseweb="tab-list"]{ gap:6px; border-bottom:1px solid var(--line); flex-wrap:wrap; }
.stTabs [data-baseweb="tab"]{ height:44px; padding:0 16px; border-radius:10px 10px 0 0; color:var(--muted); font-weight:600; }
.stTabs [aria-selected="true"]{ color:var(--teal) !important; background:var(--panel); }
.stTabs [data-baseweb="tab-highlight"]{ background:var(--teal) !important; }
section[data-testid="stSidebar"]{ background:#08131a; border-right:1px solid var(--line); }
section[data-testid="stSidebar"] .block-container{ padding-top:1rem; }
.brand{ font-family:'Bricolage Grotesque'; font-weight:800; font-size:1.5rem; color:var(--text); }
.brand span{ color:var(--teal); }
.stButton>button, .stDownloadButton>button, div[data-testid="stFormSubmitButton"]>button{
  border-radius:10px; border:1px solid var(--line); background:var(--panel-2); color:var(--text);
  font-weight:600; transition:border-color .15s, background .15s;
}
.stButton>button:hover, .stDownloadButton>button:hover{ border-color:var(--teal); color:var(--teal); }
.stButton>button:focus-visible{ outline:2px solid var(--teal); outline-offset:2px; }
div[data-testid="stFormSubmitButton"]>button{
  background:var(--teal); color:#062922; border:none; height:3rem; font-size:1.05rem;
}
div[data-testid="stFormSubmitButton"]>button:hover{ background:#6ee3d4; color:#062922; }
div[data-testid="stForm"]{ border:1px solid var(--line); border-radius:18px; background:var(--panel); padding:20px; }
[data-testid="stMetric"]{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:12px 16px; }
div[data-testid="stVerticalBlockBorderWrapper"]{ border-radius:16px; }
.verdict{
  border-radius:18px; padding:22px 26px; background:var(--panel);
  border:1px solid var(--line); border-left:8px solid var(--sev); margin-bottom:14px;
}
.verdict .name{ font-family:'Bricolage Grotesque'; font-size:2.1rem; font-weight:800; line-height:1.1; }
.badge{ display:inline-block; padding:3px 12px; border-radius:6px; font-weight:600; font-size:.88rem;
  background:color-mix(in srgb, var(--sev) 18%, transparent); color:var(--sev); border:1px solid var(--sev); }
.verdict .advice{ margin-top:12px; color:var(--text); font-size:1.05rem; }
.triage{ margin-top:12px; padding:10px 14px; border-radius:10px; background:rgba(255,255,255,.04); color:var(--muted); font-size:.95rem; }
.diff-row{ margin:10px 0 4px; display:flex; justify-content:space-between; font-size:.98rem; }
.bar{ height:8px; border-radius:6px; background:rgba(255,255,255,.07); overflow:hidden; }
.bar>i{ display:block; height:100%; border-radius:6px; background:var(--sev); }
.chip{ display:inline-block; margin:3px 6px 3px 0; padding:2px 11px; border-radius:6px; font-size:.86rem;
  background:var(--panel-2); border:1px solid var(--line); color:var(--teal); }
.sos{ border-radius:16px; padding:18px 22px; background:rgba(255,122,107,.12); border:2px solid var(--coral); margin-bottom:14px; }
.sos b{ color:var(--coral); font-size:1.25rem; }
.sos a{ color:var(--coral); font-weight:700; }
.help-card{ border:1px solid var(--line); background:var(--panel); border-radius:14px; padding:14px 16px; height:100%; }
.help-card .num{ font-family:'Bricolage Grotesque'; font-size:1.8rem; font-weight:800; color:var(--coral); }
.help-card a{ text-decoration:none; }
.section-title{ font-family:'Bricolage Grotesque'; font-size:1.35rem; font-weight:700; margin:4px 0 2px; }
.muted{ color:var(--muted); }
.ring-wrap{ display:flex; justify-content:center; margin:6px 0 2px; }
.ring{ width:128px; height:128px; border-radius:50%; display:grid; place-items:center; }
.ring-in{ width:100px; height:100px; border-radius:50%; background:#08131a; display:grid; place-items:center; text-align:center; }
.ring-in b{ font-family:'Bricolage Grotesque'; font-size:2rem; line-height:1; }
.ring-in small{ color:var(--muted); font-size:.75rem; }
.disclaimer{ color:var(--muted); font-size:.85rem; text-align:center; padding:18px 0 8px; border-top:1px solid var(--line); margin-top:26px; }
</style>
""",
    unsafe_allow_html=True,
)

# =====================================================================
# 3. DATA & CONSTANTS
# =====================================================================
LOCAL_TO_STANDARD_MAP = {
    "बुखार सा लग रहा है": "fever", "बुखार जैसा": "fever", "तेज गरम": "high fever",
    "शरीर तप रहा है": "high fever", "bukhar hai": "fever", "tez bukhar": "high fever",
    "bukhar": "fever", "बुखार": "fever", "जुखाम": "runny nose", "zukam": "runny nose",
    "gira gira sa": "weakness", "कमजोरी": "weakness", "kamzori": "weakness",
    "एनर्जी नहीं है": "weakness", "thakawat": "fatigue", "थकावट": "fatigue", "थकान": "fatigue",
    "jaldi thak jana": "fatigue", "चक्कर आ रहे हैं": "dizziness", "chakkar": "dizziness",
    "bada dukh raha hai": "body ache", "बदन दुख रहा है": "body ache", "बदन दर्द": "body ache",
    "जोड़ों में दर्द": "joint pain", "छाती में दर्द": "chest pain", "seene mein dard": "chest pain",
    "pet mein gudgud": "stomach pain", "पेट में गुड़गुड़": "stomach pain", "पेट दर्द": "stomach pain",
    "पेट खराब": "diarrhea", "loose motion": "diarrhea", "दस्त": "diarrhea",
    "उल्टी जैसा": "nausea", "उल्टी": "vomiting", "vomiting ho rahi hai": "vomiting",
    "जलन": "acidity", "कब्जी": "constipation", "पाखाना नहीं हो रहा": "constipation",
    "saans lene mein takleef": "shortness breath", "saans phoolna": "shortness breath",
    "सांस फूलना": "shortness breath", "सिरदर्द": "headache", "sar dard": "headache",
    "खांसी": "cough", "khansi": "cough", "गला खराब": "sore throat", "नाक बहना": "runny nose",
}

diseases = [
    {"disease_hi": "वायरल बुखार", "disease_en": "Viral Fever", "symptoms": "बुखार सिरदर्द बदन दर्द खांसी कमजोरी थकान fever headache body ache cough weakness", "severity": "Mild", "advice_hi": "🌡️ पैरासिटामॉल लें, खूब पानी पिएं और आराम करें। 5-7 दिन में ठीक।", "advice_en": "🌡️ Take Paracetamol, drink plenty of fluids and rest. Recovers in 5-7 days."},
    {"disease_hi": "डेंगू", "disease_en": "Dengue", "symptoms": "तेज बुखार जोड़ों में दर्द रैश थकान आँख दर्द high fever joint pain rash fatigue", "severity": "Critical", "advice_hi": "🚨 तुरंत अस्पताल जाएं। प्लेटलेट्स की जांच करवाएं। खूब तरल पदार्थ पिएं।", "advice_en": "🚨 Visit a hospital immediately. Check platelets. Drink abundant fluids."},
    {"disease_hi": "दिल का दौरा", "disease_en": "Heart Attack", "symptoms": "सीने में दर्द सांस फूलना पसीना बायां हाथ दर्द chest pain shortness breath sweating left arm", "severity": "Critical", "advice_hi": "🔥 तुरंत 108 बुलाएं। मरीज को शांत बैठाएं। खुद गाड़ी चलाकर न जाएं।", "advice_en": "🔥 Call ambulance immediately. Keep patient calm. Do not drive yourself."},
    {"disease_hi": "माइग्रेन", "disease_en": "Migraine", "symptoms": "तेज सिरदर्द उल्टी रोशनी से परेशानी migraine headache nausea light sensitivity", "severity": "Moderate", "advice_hi": "💡 अंधेरे शांत कमरे में लेटें। माथे पर ठंडी पट्टी रखें। बार-बार हो तो डॉक्टर से मिलें।", "advice_en": "💡 Lie down in a dark quiet room. Use a cold compress. Consult a doctor if frequent."},
    {"disease_hi": "सर्दी-जुकाम", "disease_en": "Common Cold", "symptoms": "नाक बहना छींक गला खराब खांसी runny nose sneezing sore throat cough", "severity": "Mild", "advice_hi": "☕ भाप लें, अदरक की चाय पिएं। 4-7 दिन में ठीक।", "advice_en": "☕ Take steam, drink ginger tea. Recovers in 4-7 days."},
    {"disease_hi": "टाइफाइड", "disease_en": "Typhoid", "symptoms": "लगातार बुखार कमजोरी पेट दर्द भूख नहीं typhoid fever weakness stomach pain", "severity": "High", "advice_hi": "🔬 Widal / ब्लड कल्चर टेस्ट करवाएं। एंटीबायोटिक सिर्फ डॉक्टर की सलाह पर लें।", "advice_en": "🔬 Get a Widal / blood culture test. Take antibiotics only if prescribed."},
    {"disease_hi": "फूड पॉइजनिंग", "disease_en": "Food Poisoning", "symptoms": "उल्टी दस्त पेट दर्द vomiting diarrhea stomach pain", "severity": "Moderate", "advice_hi": "💧 ORS पिएं, हल्का खाना खाएं। 48 घंटे में आराम न मिले तो डॉक्टर को दिखाएं।", "advice_en": "💧 Drink ORS, eat light. See a doctor if no relief in 48 hours."},
    {"disease_hi": "निमोनिया", "disease_en": "Pneumonia", "symptoms": "तेज बुखार खांसी सीने में दर्द सांस फूलना pneumonia cough chest pain shortness breath", "severity": "Critical", "advice_hi": "🚑 तुरंत अस्पताल जाएं। छाती का एक्स-रे करवाएं।", "advice_en": "🚑 Visit a hospital immediately. Get a chest X-ray."},
    {"disease_hi": "एनीमिया", "disease_en": "Anemia", "symptoms": "थकान चक्कर कमजोरी चेहरा पीला anemia fatigue dizziness weakness", "severity": "Moderate", "advice_hi": "🩸 खून की जांच (CBC) करवाएं। पालक, चुकंदर, अनार खाएं।", "advice_en": "🩸 Get a CBC blood test. Eat spinach, beetroot, pomegranate."},
    {"disease_hi": "किडनी स्टोन", "disease_en": "Kidney Stone", "symptoms": "कमर में तेज दर्द पेशाब में खून kidney stone back pain blood urine", "severity": "Critical", "advice_hi": "⚠️ तुरंत अस्पताल जाएं। अल्ट्रासाउंड करवाएं और खूब पानी पिएं।", "advice_en": "⚠️ Visit a hospital immediately. Get an ultrasound and drink plenty of water."},
    {"disease_hi": "अस्थमा अटैक", "disease_en": "Asthma Attack", "symptoms": "सांस फूलना घरघराहट सीने में जकड़न asthma wheezing shortness breath", "severity": "Critical", "advice_hi": "💨 इनहेलर लें। आराम न मिले तो तुरंत 108 पर कॉल करें।", "advice_en": "💨 Use an inhaler. Call ambulance immediately if no relief."},
]
df = pd.DataFrame(diseases)

def get_sev_dict():
    return {
        "Mild": ("#6fd39a", "✅", t("Home care is sufficient. See doctor if no improvement in 2-3 days.", "घर पर देखभाल काफी है। 2-3 दिन में सुधार न हो तो डॉक्टर से मिलें।")),
        "Moderate": ("#f4c05a", "⚠️", t("Consult a doctor within 24-48 hours, especially if symptoms worsen.", "24-48 घंटे में डॉक्टर से सलाह लें, खासकर लक्षण बढ़ें तो।")),
        "High": ("#fb9a52", "🛑", t("See a doctor today.", "आज ही डॉक्टर को दिखाएं।")),
        "Critical": ("#ff7a6b", "🚨", t("Contact hospital / emergency (108) immediately.", "तुरंत अस्पताल / इमरजेंसी (108) से संपर्क करें।")),
    }

SYMPTOM_UI = {
    "बुखार / Fever": "fever", "सिरदर्द / Headache": "headache", "बदन दर्द / Body ache": "body ache",
    "खांसी / Cough": "cough", "कमजोरी / Weakness": "weakness", "थकान / Fatigue": "fatigue",
    "तेज बुखार / High fever": "high fever", "जोड़ों में दर्द / Joint pain": "joint pain",
    "रैश / Rash": "rash", "आँख दर्द / Eye pain": "eye pain", "सीने में दर्द / Chest pain": "chest pain",
    "सांस फूलना / Shortness of breath": "shortness breath", "उल्टी / Nausea": "nausea",
    "दस्त / Diarrhea": "diarrhea", "चक्कर आना / Dizziness": "dizziness", "पेट दर्द / Stomach pain": "stomach pain",
    "गला खराब / Sore throat": "sore throat", "नाक बहना / Runny nose": "runny nose",
}
SYMPTOM_OPTIONS = sorted(SYMPTOM_UI.keys())

EMERGENCY_WORDS = [
    "सीने में दर्द", "chest pain", "सांस नहीं", "cant breathe", "can't breathe", "heart attack",
    "बेहोश", "behosh", "दम घुट", "seene mein dard", "बहुत खून", "stroke", "लकवा", "सांप ने काटा",
]

PAIN_LEVELS = {
    "0 - No Pain / कोई दर्द नहीं": 0, "1 - Mild / हल्का": 1, "2 - Moderate / कम": 3,
    "3 - High / मध्यम": 5, "4 - Severe / तेज": 7, "5 - Unbearable / असहनीय": 10,
}
PAIN_OPTIONS = list(PAIN_LEVELS.keys())

DURATION_OPTIONS = [
    "A few hours / कुछ घंटे", "1-2 days / दिन", "3-5 days / दिन", 
    "More than 1 week / 1 हफ्ते से ज्यादा", "Multiple weeks / कई हफ्ते"
]

HELPLINES = [
    ("108", "एम्बुलेंस", "Emergency ambulance"), ("112", "इमरजेंसी", "Police / Fire / Medical"),
    ("102", "मातृ-शिशु सेवा", "Mother & child ambulance"), ("14416", "Tele-MANAS", "Mental health support"),
    ("1098", "चाइल्डलाइन", "Child helpline"), ("1091", "महिला हेल्पलाइन", "Women helpline"),
]

FIRST_AID = {
    "💔 Chest Pain / Heart Attack Signs | सीने में दर्द / हार्ट अटैक": t(
        "Call ambulance immediately. Sit the patient down, loosen clothing, keep them calm. Give Aspirin only if not allergic and advised by doctor.",
        "तुरंत 108 बुलाएं। मरीज को आराम से बैठाएं, कपड़े ढीले करें और उसे चलने न दें। एस्प्रिन तभी दें जब एलर्जी न हो और इमरजेंसी ऑपरेटर/डॉक्टर कहें।"
    ),
    "🔥 Burns | जलना": t(
        "Run cool (not ice cold) water over the burn for 15-20 mins. Don't apply toothpaste or butter. Don't pop blisters. Seek hospital for large burns.",
        "जले हिस्से पर 15-20 मिनट बहता ठंडा (बर्फ वाला नहीं) पानी डालें। टूथपेस्ट, मक्खन या बर्फ न लगाएं। छाले न फोड़ें। बड़ा जलना हो तो अस्पताल जाएं।"
    ),
    "😮‍💨 Choking | गले में कुछ फंसना": t(
        "Give 5 firm back blows, then 5 abdominal thrusts (Heimlich maneuver). Call emergency if airways don't clear.",
        "वयस्क को आगे झुकाकर पीठ पर 5 जोरदार थपकी दें, फिर पेट पर 5 बार दबाव (Heimlich) दें। न खुले तो 108 बुलाएं।"
    ),
}

# =====================================================================
# 4. LOGIC
# =====================================================================
def local_diagnose(text, ui_keys):
    selected = [SYMPTOM_UI[k] for k in ui_keys if k in SYMPTOM_UI]
    combined = (text.lower() + " " + " ".join(selected)).strip()
    cleaned = re.sub(r"[^a-zA-Z\u0900-\u097F\s']", " ", combined)
    for phrase in sorted(LOCAL_TO_STANDARD_MAP, key=len, reverse=True):
        cleaned = cleaned.replace(phrase, LOCAL_TO_STANDARD_MAP[phrase])
    final_text = re.sub(r"\s+", " ", cleaned).strip()
    user_tokens = set(final_text.split())

    results = []
    for _, row in df.iterrows():
        d_tokens = row["symptoms"].split()
        matched = sorted({t for t in d_tokens if t in user_tokens})
        score = fuzz.token_set_ratio(final_text, row["symptoms"])
        threshold = 40 if row["severity"] == "Critical" else 48
        if score >= threshold and matched:
            results.append({
                "disease": row["disease_en"] if st.session_state.lang == "English" else row["disease_hi"], 
                "severity": row["severity"], 
                "advice": row["advice_en"] if st.session_state.lang == "English" else row["advice_hi"],
                "confidence": min(100, score + 10), "matched": matched,
                "ratio": round(100 * len(matched) / len(set(d_tokens))),
            })
    results.sort(key=lambda r: (r["confidence"], len(r["matched"])), reverse=True)
    return results, final_text

def health_score(temp_c, pain, spo2, pulse):
    s = 100 - abs(temp_c - 36.6) * 8 - pain * 4
    if spo2 < 95:
        s -= (95 - spo2) * 3
    if pulse < 60 or pulse > 100:
        s -= min(15, (60 - pulse if pulse < 60 else pulse - 100) * 0.5)
    return int(max(0, min(100, s)))

def bmi_info(w, h):
    if h <= 0:
        return 0.0, "—", (0, 0)
    m = h / 100
    b = w / (m * m)
    if b < 18.5:
        cat = t("Underweight", "कम वजन")
    elif b < 25:
        cat = t("Normal", "सामान्य")
    elif b < 30:
        cat = t("Overweight", "अधिक वजन")
    else:
        cat = t("Obese", "मोटापा")
    return round(b, 1), cat, (round(18.5 * m * m, 1), round(24.9 * m * m, 1))

def ring_html(score):
    c = "#6fd39a" if score >= 75 else "#f4c05a" if score >= 50 else "#ff7a6b"
    label = t("Good", "बढ़िया") if score >= 75 else t("Caution", "ध्यान दें") if score >= 50 else t("Consult", "सलाह लें")
    return (
        f'<div class="ring-wrap"><div class="ring" style="background:conic-gradient({c} {score}%, rgba(255,255,255,.08) 0)">'
        f'<div class="ring-in"><div><b style="color:{c}">{score}</b><br><small>{label}</small></div></div></div></div>'
    )

def build_report(res):
    lines = [
        "MediMind AI - Health Report",
        f"Date: {res['time']}",
        f"Name: {res['profile'].get('name') or '-'} | Age: {res['profile'].get('age')} | Gender: {res['profile'].get('gender')}",
        f"Vitals: Temp {res['temp']:.1f}C, SpO2 {res['spo2']}%, Pulse {res['pulse']}, Health score {res['score']}/100",
        f"Symptoms: {res['input'] or '-'} {', '.join(res['symptoms'])}",
        f"Duration: {res['duration']}",
        "",
        "--- Local database match ---",
    ]
    for r in res["local"][:4]:
        lines.append(f"- {r['disease']} ({r['severity']}) confidence {r['confidence']}%")
    lines += ["", "--- Gemini AI opinion ---", res["gemini"] or (res["gemini_err"] or "-"), "",
              "Disclaimer: AI simulation. Please consult a qualified doctor."]
    return "\n".join(lines)

def use_example(text):
    st.session_state.symptom_text = text

def queue_question(q):
    st.session_state.pending_q = q

# =====================================================================
# 6. SIDEBAR - PROFILE & VITALS
# =====================================================================
with st.sidebar:
    st.session_state.lang = st.radio("🌐 Language / भाषा", ["English", "हिंदी"], horizontal=True)
    st.markdown('<div class="brand">Medi<span>Mind</span> AI</div>', unsafe_allow_html=True)
    st.caption(t("Your Smart Health Companion", "आपका स्मार्ट हेल्थ साथी"))

    with st.expander(t("👤 Profile", "👤 प्रोफाइल"), expanded=False):
        st.text_input(t("Name", "नाम (Name)"), key="name")
        c1, c2 = st.columns(2)
        c1.number_input(t("Age", "उम्र"), 1, 110, key="age")
        c2.selectbox(t("Gender", "लिंग"), [t("Male / पुरुष", "Male / पुरुष"), t("Female / महिला", "Female / महिला"), t("Other / अन्य", "Other / अन्य")], key="gender")

    st.markdown(t("**🩺 Your Vitals**", "**🩺 आपके वाइटल्स**"))
    st.radio(t("Temperature Unit", "तापमान यूनिट"), ["°C", "°F"], key="unit", horizontal=True)
    if st.session_state.unit == "°C":
        st.slider(t("Temperature (°C)", "तापमान (°C)"), 35.0, 42.0, step=0.1, key="temp_c")
        temp_c = st.session_state.temp_c
        temp_txt = f"{temp_c:.1f}°C"
    else:
        st.slider(t("Temperature (°F)", "तापमान (°F)"), 95.0, 107.6, step=0.1, key="temp_f")
        temp_c = (st.session_state.temp_f - 32) * 5 / 9
        temp_txt = f"{st.session_state.temp_f:.1f}°F"

    st.select_slider(t("🤕 Pain Level", "🤕 दर्द का स्तर"), options=PAIN_OPTIONS, key="pain")
    st.slider(t("🫁 SpO₂ (%)", "🫁 SpO₂ (%)"), 80, 100, key="spo2")
    st.slider(t("❤️ Pulse (bpm)", "❤️ पल्स (bpm)"), 40, 180, key="pulse")

    c1, c2 = st.columns(2)
    c1.number_input(t("Weight (kg)", "वजन (kg)"), 20.0, 300.0, step=0.5, key="weight")
    c2.number_input(t("Height (cm)", "ऊंचाई (cm)"), 50.0, 250.0, step=1.0, key="height")

    pain_val = PAIN_LEVELS[st.session_state.pain]
    score = health_score(temp_c, pain_val, st.session_state.spo2, st.session_state.pulse)
    bmi, bmi_cat, ideal = bmi_info(st.session_state.weight, st.session_state.height)

    st.markdown(t("**🚀 Health Score**", "**🚀 हेल्थ स्कोर**"))
    st.markdown(ring_html(score), unsafe_allow_html=True)
    st.caption(f"BMI **{bmi}** ({bmi_cat}) · {t('Ideal Weight', 'आदर्श वजन')} {ideal[0]}-{ideal[1]} kg")
    if st.session_state.spo2 < 94:
        st.error(t("SpO₂ below 94%. Consult doctor immediately.", "SpO₂ 94% से कम है। डॉक्टर से तुरंत संपर्क करें।"))

    st.button(t("🔄 Reset Everything", "🔄 सब कुछ रीसेट करें"), on_click=reset_inputs, use_container_width=True)

# =====================================================================
# 7. HERO
# =====================================================================
status_pill = (
    f'<span class="pill on">● {t("Gemini Live Connected", "Gemini Live जुड़ा है")}</span>' if GEMINI_ENABLED
    else f'<span class="pill off">● {t("Gemini Disabled (No key)", "Gemini बंद (API key नहीं मिली)")}</span>'
)
st.markdown(
    f"""
<div class="hero">
  <h1 class="display">MediMind AI</h1>
  <p>{t("Describe your symptoms to get potential causes, severity, and actionable next steps in seconds.", "लक्षण बताइए, कुछ ही सेकंड में संभावित कारण, गंभीरता और अगला कदम जानिए।")}</p>
  <div class="pills">{status_pill}<span class="pill">{t("11 Local Diseases Database", "11 रोगों का लोकल डेटाबेस")}</span><span class="pill">{t("Google Search Validation", "Google Search से वैलिडेशन")}</span></div>
  <svg class="ecg" viewBox="0 0 600 120" preserveAspectRatio="none" aria-hidden="true">
    <path d="M0 70 H110 L135 70 L150 30 L172 108 L192 12 L212 70 H300 L322 70 L336 46 L352 70 H600"/>
  </svg>
</div>
""",
    unsafe_allow_html=True,
)

tab_dx, tab_chat, tab_med, tab_diet, tab_track, tab_sos = st.tabs(
    [t("🩺 Diagnose", "🩺 जांच"), t("💬 AI Chat", "💬 AI चैट"), t("💊 Medicine", "💊 दवा"), 
     t("🥗 Diet", "🥗 डाइट"), t("📈 Tracker", "📈 ट्रैकर"), t("🚑 Emergency", "🚑 इमरजेंसी")]
)

# =====================================================================
# 8. TAB - DIAGNOSE
# =====================================================================
def render_result(res):
    if res["emergency"]:
        st.markdown(
            f'<div class="sos"><b>🚨 {t("Emergency signs detected", "इमरजेंसी के संकेत मिले हैं")}</b><br>'
            f'{t("Do not delay. Call <a href=\'tel:108\'>📞 108</a> or go to the nearest hospital immediately.", "देर न करें। तुरंत <a href=\'tel:108\'>📞 108 डायल करें</a> या नजदीकी अस्पताल जाएं।")}</div>',
            unsafe_allow_html=True,
        )

    results = res["local"]
    if results:
        top = results[0]
        SEV = get_sev_dict()
        color, emoji, triage = SEV.get(top["severity"], SEV["Mild"])
        chips = "".join(f'<span class="chip">{m}</span>' for m in top["matched"][:10])
        st.markdown(
            f"""
<div class="verdict" style="--sev:{color}">
  <span class="badge">{emoji} {t(top['severity'], top['severity'])}</span>
  <div class="name">{top['disease']}</div>
  <div class="advice">{top['advice']}</div>
  <div class="triage"><b>{t("Next Step:", "अगला कदम:")}</b> {triage}</div>
  <div style="margin-top:12px" class="muted">{t("Matched Symptoms:", "मिले हुए लक्षण:")} {chips}</div>
</div>""",
            unsafe_allow_html=True,
        )
        m1, m2, m3 = st.columns(3)
        m1.metric(t("Confidence", "विश्वसनीयता"), f"{top['confidence']}%")
        m2.metric(t("Match Ratio", "लक्षण मिलान"), f"{top['ratio']}%")
        m3.metric(t("Health Score", "हेल्थ स्कोर"), f"{res['score']}/100")

        if len(results) > 1:
            st.markdown(f'<div class="section-title">{t("Other Possibilities", "अन्य संभावनाएं")}</div>', unsafe_allow_html=True)
            for r in results[1:4]:
                c = SEV.get(r["severity"], SEV["Mild"])[0]
                st.markdown(
                    f'<div style="--sev:{c}"><div class="diff-row"><span>{r["disease"]} '
                    f'<span class="muted">· {r["severity"]}</span></span><b>{r["confidence"]}%</b></div>'
                    f'<div class="bar"><i style="width:{r["confidence"]}%"></i></div></div>',
                    unsafe_allow_html=True,
                )
    else:
        st.warning(t("No strong match in the local database. See Gemini's opinion below or describe symptoms in more detail.", "लोकल डेटाबेस में कोई मजबूत मिलान नहीं मिला। नीचे Gemini की राय देखें या लक्षण थोड़े और विस्तार से लिखें।"))

    st.markdown(f'<div class="section-title" style="margin-top:22px">🌐 {t("Gemini AI Opinion (with Google Search)", "Gemini की राय (Google Search के साथ)")}</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if res["gemini"]:
            st.markdown(res["gemini"])
        else:
            st.info(res["gemini_err"] or t("No response from Gemini.", "Gemini से जवाब नहीं मिला।"))

    if res["tip"]:
        st.success(f"🌟 **{t('Daily Tip:', 'आज की टिप:')}** {res['tip']}")

    d1, d2 = st.columns(2)
    d1.download_button(t("⬇️ Download Report", "⬇️ रिपोर्ट डाउनलोड करें"), build_report(res), file_name="medimind_report.txt", use_container_width=True)
    if d2.button(t("➕ Save to Tracker", "➕ ट्रैकर में सेव करें"), use_container_width=True, key="save_from_result"):
        st.session_state.log.append({
            t("Time", "समय"): res["time"], t("Temp °C", "तापमान °C"): round(res["temp"], 1), "SpO₂": res["spo2"],
            t("Pulse", "पल्स"): res["pulse"], t("Score", "स्कोर"): res["score"], t("Note", "टिप्पणी"): results[0]["disease"] if results else "-",
        })
        st.toast(t("Saved to tracker ✅", "ट्रैकर में सेव हो गया ✅"))

with tab_dx:
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        with st.form("dx_form"):
            st.markdown(f'<div class="section-title">{t("Describe your symptoms", "अपने लक्षण बताएं")}</div>', unsafe_allow_html=True)
            st.multiselect(t("Select symptoms", "लक्षण चुनें (Select symptoms)"), SYMPTOM_OPTIONS, key="symptoms")
            st.text_area(
                t("Or write in your own words", "या अपनी भाषा में लिखें (हिंदी / English / Hinglish)"),
                key="symptom_text", height=130,
                placeholder=t("e.g. I have been feeling feverish and body ache for 3 days...", "जैसे: मुझे 3 दिन से बुखार सा लग रहा है और बदन दुख रहा है…"),
            )
            st.select_slider(t("Duration?", "कब से हैं?"), DURATION_OPTIONS, key="duration")
            submitted = st.form_submit_button(t("⚡ Analyze", "⚡ जांच करें"), use_container_width=True)
        st.caption(t("Try an example:", "कोशिश करके देखें:"))
        EXAMPLES = [
            t("I've had a fever for 3 days, body aches, and extreme weakness.", "मुझे 3 दिन से बुखार सा लग रहा है, बदन दुख रहा है और बहुत कमजोरी महसूस हो रही है।"),
            "naak beh rahi hai, gala kharab hai aur khansi bhi hai",
            t("High fever, joint pain, and rashes on the body.", "तेज बुखार, जोड़ों में दर्द और शरीर पर रैश हो गए हैं"),
        ]
        for i, ex in enumerate(EXAMPLES):
            st.button(f"“{ex[:48]}…”", key=f"ex{i}", on_click=use_example, args=(ex,), use_container_width=True)

    with right:
        st.markdown(f'<div class="section-title">{t("Live Vitals", "लाइव वाइटल्स")}</div>', unsafe_allow_html=True)
        v1, v2 = st.columns(2)
        v1.metric(t("Temp", "तापमान"), temp_txt)
        v2.metric("SpO₂", f"{st.session_state.spo2}%")
        v3, v4 = st.columns(2)
        v3.metric(t("Pulse", "पल्स"), f"{st.session_state.pulse} bpm")
        v4.metric("BMI", f"{bmi}", bmi_cat)
        with st.container(border=True):
            st.markdown(t("**Pro tips for better results:**", "**ऐसे लिखें तो बेहतर नतीजे मिलेंगे**"))
            st.markdown(t("- Mention duration and severity\n- Any accompanying issues\n- Existing conditions or meds", "- कितने दिन से और कितना तेज\n- साथ में कोई और दिक्कत\n- कोई पुरानी बीमारी या चल रही दवा"))

    if submitted:
        text = st.session_state.symptom_text
        ui = st.session_state.symptoms
        if not text.strip() and not ui:
            st.warning(t("Please select or describe at least one symptom.", "कृपया कम से कम एक लक्षण चुनें या लिखें।"))
        else:
            with st.status(t("MediMind is analyzing your symptoms…", "MediMind आपके लक्षणों का विश्लेषण कर रहा है…"), expanded=True) as status:
                st.write(t("🔎 Checking local database…", "🔎 लोकल डेटाबेस से मिलान…"))
                local, processed = local_diagnose(text, ui)
                emergency = any(k in (text or "").lower() for k in EMERGENCY_WORDS) or "chest pain" in processed
                profile = dict(name=st.session_state.name, age=st.session_state.age, gender=st.session_state.gender)

                st.write(t("🌐 Validating with Gemini…", "🌐 Gemini से वैलिडेशन…"))
                prompt = (
                    f"{STYLE_RULES}\n\nPatient: age {profile['age']}, {profile['gender']}. "
                    f"Symptoms: \"{text}\" {', '.join(ui)}. Duration: {st.session_state.duration}. "
                    f"Vitals: temp {temp_c:.1f}C, SpO2 {st.session_state.spo2}%, pulse {st.session_state.pulse}.\n"
                    "Give, in markdown with bold headings: 1) Most likely condition and 1-2 alternatives, "
                    "2) Severity (Mild/Moderate/High/Critical), 3) Home-care steps, 4) Red-flag signs that need a doctor now."
                )
                g_text, g_err = ask_gemini(prompt, search=True)

                st.write(t("✨ Generating personal tip…", "✨ पर्सनल टिप तैयार हो रही है…"))
                tip, _ = ask_gemini(
                    f"{STYLE_RULES}\nUser health score {score}/100, symptoms: {processed}. "
                    "Give ONE daily preventive health tip in under 15 words."
                )
                if not tip:
                    tip = random.choice([
                        t("Drink 7-8 glasses of water today. 💧", "आज 7-8 गिलास पानी पिएं। 💧"), 
                        t("Take a 30-minute walk today.", "आज 30 मिनट टहलें।"), 
                        t("Get 7 hours of sleep tonight.", "7 घंटे की नींद पूरी करें।"), 
                        t("Eat a fresh fruit today.", "एक ताजा फल जरूर खाएं।")
                    ])
                status.update(label=t("Analysis Complete ✅", "विश्लेषण पूरा ✅"), state="complete", expanded=False)

            res = dict(
                time=datetime.now().strftime("%d %b %Y, %I:%M %p"), input=text, symptoms=ui, duration=st.session_state.duration,
                emergency=emergency, local=local, gemini=g_text, gemini_err=g_err, tip=tip, score=score,
                temp=temp_c, spo2=st.session_state.spo2, pulse=st.session_state.pulse, profile=profile,
            )
            st.session_state.result = res
            st.session_state.last_disease = local[0]["disease"] if local else ""
            st.session_state.history.append({
                t("Time", "समय"): res["time"], t("Possible Condition", "संभावित रोग"): local[0]["disease"] if local else "-",
                t("Severity", "गंभीरता"): local[0]["severity"] if local else "-", t("Score", "स्कोर"): score,
            })

    if st.session_state.result:
        st.markdown("---")
        render_result(st.session_state.result)
    else:
        st.info(t("⬆️ Enter symptoms above and click **Analyze**. Results will appear here.", "⬆️ ऊपर लक्षण भरें और **जांच करें** दबाएं। नतीजे यहां दिखेंगे।"))

# =====================================================================
# 9. TAB - CHAT
# =====================================================================
with tab_chat:
    st.markdown(f'<div class="section-title">{t("Ask MediMind Anything", "MediMind से कुछ भी पूछें")}</div>', unsafe_allow_html=True)
    st.caption(t("General health questions, diet, sleep, home remedies. Answers backed by Google Search.", "सामान्य स्वास्थ्य सवाल, खान-पान, नींद, घरेलू नुस्खे। जवाब Google Search की मदद से आते हैं।"))
    
    if not GEMINI_ENABLED:
        st.warning(t("GEMINI_API_KEY is required for chat.", "चैट के लिए GEMINI_API_KEY सेट करना जरूरी है।"))
    else:
        sugg = [
            t("What to eat during weakness?", "कमजोरी में क्या खाएं?"), 
            t("When to see a doctor for fever?", "बुखार में डॉक्टर के पास कब जाएं?"), 
            t("Tips for better sleep", "अच्छी नींद के आसान तरीके"), 
            t("How to make ORS at home?", "घर पर ORS कैसे बनाएं?")
        ]
        cols = st.columns(len(sugg))
        for i, s in enumerate(sugg):
            cols[i].button(s, key=f"sg{i}", on_click=queue_question, args=(s,), use_container_width=True)

        for m in st.session_state.chat:
            with st.chat_message("user" if m["role"] == "user" else "assistant", avatar="🧑" if m["role"] == "user" else "🩺"):
                st.markdown(m["text"])

        q = st.chat_input(t("Type your question…", "अपना सवाल लिखें…")) or st.session_state.pop("pending_q", None)
        if q:
            st.session_state.chat.append({"role": "user", "text": q})
            with st.chat_message("user", avatar="🧑"):
                st.markdown(q)
            ctx = "\n".join(f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['text']}" for m in st.session_state.chat[-8:])
            with st.chat_message("assistant", avatar="🩺"):
                with st.spinner(t("Generating response…", "जवाब तैयार हो रहा है…")):
                    ans, err = ask_gemini(f"{STYLE_RULES}\n\nConversation:\n{ctx}\nAssistant:", search=True)
                reply = ans or f"{t('Sorry, could not generate a response.', 'माफ़ कीजिए, जवाब नहीं मिल पाया।')} {err}"
                st.markdown(reply)
            st.session_state.chat.append({"role": "ai", "text": reply})

        if st.session_state.chat:
            st.button(t("🧹 Clear Chat", "🧹 चैट साफ करें"), on_click=lambda: st.session_state.update(chat=[]))

# =====================================================================
# 10. TAB - MEDICINE
# =====================================================================
with tab_med:
    st.markdown(f'<div class="section-title">{t("Medicine Info & Interactions", "दवा की जानकारी और इंटरैक्शन")}</div>', unsafe_allow_html=True)
    mode = st.radio(t("What do you want to check?", "क्या करना है?"), [t("Interaction between 2 meds", "दो दवाओं का इंटरैक्शन"), t("Info on a single med", "एक दवा की जानकारी")], horizontal=True)
    
    if mode.startswith("दो") or mode.startswith("Interaction"):
        c1, c2 = st.columns(2)
        med_a = c1.text_input(t("Medicine A", "दवा A"), placeholder="Paracetamol")
        med_b = c2.text_input(t("Medicine B", "दवा B"), placeholder="Ibuprofen")
        if st.button(t("🔍 Check Interaction", "🔍 इंटरैक्शन जांचें"), type="primary"):
            if med_a and med_b:
                with st.spinner(t("Checking…", "जांच हो रही है…")):
                    ans, err = ask_gemini(
                        f"{STYLE_RULES}\nCheck interaction between '{med_a}' and '{med_b}'. In markdown give: "
                        "**Interaction level** (None/Mild/Moderate/Severe), **What can happen**, **Safety advice**. ",
                        search=True,
                    )
                with st.container(border=True):
                    show_ai(ans, err)
            else:
                st.warning(t("Enter both medicine names.", "दोनों दवाओं के नाम लिखें।"))
    else:
        med = st.text_input(t("Medicine Name", "दवा का नाम"), placeholder="Azithromycin")
        if st.button(t("📖 Show Info", "📖 जानकारी दिखाएं"), type="primary"):
            if med:
                with st.spinner(t("Fetching info…", "जानकारी ला रहे हैं…")):
                    ans, err = ask_gemini(
                        f"{STYLE_RULES}\nExplain medicine '{med}' in markdown: **Used for**, **Common side effects**, "
                        "**Who should avoid it**, **Important precautions**. Do not give a personal dosage.",
                        search=True,
                    )
                with st.container(border=True):
                    show_ai(ans, err)
            else:
                st.warning(t("Enter a medicine name.", "दवा का नाम लिखें।"))
    st.caption(t("⚠️ Always consult a doctor/pharmacist before starting or stopping any medication.", "⚠️ कोई भी दवा शुरू या बंद करने से पहले डॉक्टर / फार्मासिस्ट से पूछें।"))

# =====================================================================
# 11. TAB - DIET
# =====================================================================
with tab_diet:
    st.markdown(f'<div class="section-title">{t("Personalized Diet Plan", "पर्सनल डाइट प्लान")}</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.4, 1, 1])
    disease_in = c1.text_input(t("Condition / Illness", "स्थिति / रोग"), value=st.session_state.get("last_disease", "") or t("Viral Fever", "वायरल बुखार"))
    pref = c2.selectbox(t("Diet Preference", "खान-पान"), [t("Vegetarian", "शाकाहारी"), t("Non-Vegetarian", "मांसाहारी"), t("Vegan", "वीगन"), t("Jain", "जैन")])
    goal = c3.selectbox(t("Goal", "मकसद"), [t("Fast Recovery", "जल्दी रिकवरी"), t("Weight Loss", "वजन घटाना"), t("Weight Gain", "वजन बढ़ाना"), t("Energy Boost", "एनर्जी बढ़ाना")])
    if st.button(t("🥗 Generate Diet Plan", "🥗 डाइट प्लान बनाएं"), type="primary"):
        if disease_in.strip():
            with st.spinner(t("Generating plan…", "प्लान बन रहा है…")):
                ans, err = ask_gemini(
                    f"{STYLE_RULES}\nCreate a simple Indian diet plan for '{disease_in}'. Diet type: {pref}. Goal: {goal}. "
                    f"Person: BMI {bmi} ({bmi_cat}). Use markdown: **Foods to eat** (3+ bullets), **Foods to avoid** (3+ bullets), "
                    "and a **1-day sample meal plan** (breakfast, lunch, snack, dinner)."
                )
            with st.container(border=True):
                show_ai(ans, err)
        else:
            st.warning(t("Enter condition or illness name.", "रोग / स्थिति का नाम लिखें।"))

# =====================================================================
# 12. TAB - TRACKER
# =====================================================================
with tab_track:
    st.markdown(f'<div class="section-title">{t("Health Tracker", "हेल्थ ट्रैकर")}</div>', unsafe_allow_html=True)
    t1, t2 = st.columns([1.2, 1], gap="large")
    with t1:
        if st.button(t("💾 Save Today's Vitals", "💾 आज के वाइटल्स सेव करें"), type="primary"):
            st.session_state.log.append({
                t("Time", "समय"): datetime.now().strftime("%d %b %Y, %I:%M %p"), t("Temp °C", "तापमान °C"): round(temp_c, 1),
                "SpO₂": st.session_state.spo2, t("Pulse", "पल्स"): st.session_state.pulse, t("Score", "स्कोर"): score, t("Note", "टिप्पणी"): f"BMI {bmi}",
            })
            st.toast(t("Saved ✅", "सेव हो गया ✅"))
        if st.session_state.log:
            log_df = pd.DataFrame(st.session_state.log)
            st.line_chart(log_df.set_index(t("Time", "समय"))[[t("Score", "स्कोर")]], color="#47d1c0", height=220)
            st.line_chart(log_df.set_index(t("Time", "समय"))[[t("Temp °C", "तापमान °C")]], color="#ff7a6b", height=180)
            st.dataframe(log_df, use_container_width=True, hide_index=True)
            e1, e2 = st.columns(2)
            e1.download_button(t("⬇️ Download CSV", "⬇️ CSV डाउनलोड"), log_df.to_csv(index=False).encode("utf-8-sig"), "medimind_log.csv", use_container_width=True)
            e2.button(t("🗑️ Clear Log", "🗑️ लॉग साफ करें"), on_click=lambda: st.session_state.update(log=[]), use_container_width=True)
        else:
            st.info(t("No entries yet. Save your first entry using the button above.", "अभी कोई एंट्री नहीं है। ऊपर बटन से पहली एंट्री सेव करें।"))
        if st.session_state.history:
            with st.expander(t("🕘 Past Diagnoses", "🕘 पिछली जांचें")):
                st.dataframe(pd.DataFrame(st.session_state.history[::-1]), use_container_width=True, hide_index=True)
    with t2:
        with st.container(border=True):
            st.markdown(t("**💧 Water Intake Today**", "**💧 आज का पानी**"))
            st.progress(min(st.session_state.water / 8, 1.0), text=f"{st.session_state.water} / 8 {t('glasses', 'गिलास')}")
            w1, w2 = st.columns(2)
            w1.button(t("➕ Add a glass", "➕ एक गिलास"), on_click=lambda: st.session_state.update(water=st.session_state.water + 1), use_container_width=True)
            w2.button(t("➖ Remove", "➖ घटाएं"), on_click=lambda: st.session_state.update(water=max(0, st.session_state.water - 1)), use_container_width=True)
        with st.container(border=True):
            st.markdown(t("**😴 Sleep Last Night**", "**😴 कल रात की नींद**"))
            st.slider(t("Hours", "घंटे"), 0.0, 12.0, step=0.5, key="sleep", label_visibility="collapsed")
            sl = st.session_state.sleep
            st.caption(t("Great, 7-9 hours is optimal ✅", "बढ़िया, 7-9 घंटे सही रेंज है ✅") if 7 <= sl <= 9 else t("A bit low, try to sleep early tonight.", "नींद थोड़ी कम है, आज जल्दी सोने की कोशिश करें।") if sl < 7 else t("Slightly high, keep an eye on your routine.", "थोड़ी ज्यादा है, दिनचर्या पर ध्यान दें।"))

# =====================================================================
# 13. TAB - EMERGENCY
# =====================================================================
with tab_sos:
    st.markdown(f'<div class="section-title">{t("Emergency Numbers (India)", "इमरजेंसी नंबर (भारत)")}</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, (num, hi, en) in enumerate(HELPLINES):
        label = t(en, hi)
        cols[i % 3].markdown(
            f'<div class="help-card"><a href="tel:{num}"><div class="num">📞 {num}</div></a>'
            f'<b>{label}</b><br><span class="muted">{num}</span></div>',
            unsafe_allow_html=True,
        )
        if i % 3 == 2:
            cols = st.columns(3)
    st.markdown(f'<div class="section-title" style="margin-top:24px">{t("First-Aid Guide", "फर्स्ट-एड गाइड")}</div>', unsafe_allow_html=True)
    for title, body in FIRST_AID.items():
        with st.expander(title):
            st.write(body)
    st.caption(t("These are general guidelines. Always call 108 first in severe situations.", "ये सिर्फ शुरुआती मदद के सामान्य कदम हैं। गंभीर स्थिति में पहले 108 पर कॉल करें।"))

st.markdown(
    f'<div class="disclaimer">© 2025 MediMind AI · <b>Disclaimer:</b> {t("This is an AI simulation, not a substitute for professional medical advice. Always consult a qualified doctor.", "यह एक AI सिमुलेशन है, डॉक्टर का विकल्प नहीं। सटीक निदान और इलाज के लिए हमेशा योग्य डॉक्टर से सलाह लें।")}</div>',
    unsafe_allow_html=True,
)
