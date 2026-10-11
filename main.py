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
    "Reply in the SAME language and script the user wrote in (Hindi, English or Hinglish). "
    "Be concise, use short bullet points, give practical home-care tips, and clearly say when "
    "to see a doctor or call 108. Never give dosages for prescription-only drugs. "
    "You are not a replacement for a doctor."
)


def ask_gemini(prompt: str, search: bool = False):
    """Returns (text, error). Exactly one of them is None."""
    if not GEMINI_ENABLED:
        return None, "Gemini API key configure nahi hai (GEMINI_API_KEY)."
    try:
        cfg = None
        if search:
            cfg = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        r = client.models.generate_content(model=MODEL_NAME, contents=prompt, config=cfg)
        return (r.text or "").strip(), None
    except Exception as e:
        msg = str(e)
        if any(k in msg for k in ("503", "429", "UNAVAILABLE", "rate")):
            return None, "Server abhi busy hai ya limit khatam ho gayi. Thodi der baad try karein."
        return None, f"Gemini error: {msg}"


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

/* ---------- Hero ---------- */
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

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"]{ gap:6px; border-bottom:1px solid var(--line); flex-wrap:wrap; }
.stTabs [data-baseweb="tab"]{ height:44px; padding:0 16px; border-radius:10px 10px 0 0; color:var(--muted); font-weight:600; }
.stTabs [aria-selected="true"]{ color:var(--teal) !important; background:var(--panel); }
.stTabs [data-baseweb="tab-highlight"]{ background:var(--teal) !important; }

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"]{ background:#08131a; border-right:1px solid var(--line); }
section[data-testid="stSidebar"] .block-container{ padding-top:1rem; }
.brand{ font-family:'Bricolage Grotesque'; font-weight:800; font-size:1.5rem; color:var(--text); }
.brand span{ color:var(--teal); }

/* ---------- Inputs & buttons ---------- */
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

/* ---------- Result cards ---------- */
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
# 3. DATA
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
    {"disease": "वायरल बुखार", "symptoms": "बुखार सिरदर्द बदन दर्द खांसी कमजोरी थकान fever headache body ache cough weakness", "severity": "Mild", "advice": "🌡️ पैरासिटामॉल लें, खूब पानी पिएं और आराम करें। 5-7 दिन में ठीक।"},
    {"disease": "डेंगू", "symptoms": "तेज बुखार जोड़ों में दर्द रैश थकान आँख दर्द high fever joint pain rash fatigue", "severity": "Critical", "advice": "🚨 तुरंत अस्पताल जाएं। प्लेटलेट्स की जांच करवाएं। खूब तरल पदार्थ पिएं।"},
    {"disease": "दिल का दौरा", "symptoms": "सीने में दर्द सांस फूलना पसीना बायां हाथ दर्द chest pain shortness breath sweating left arm", "severity": "Critical", "advice": "🔥 तुरंत 108 बुलाएं। मरीज को शांत बैठाएं। खुद गाड़ी चलाकर न जाएं।"},
    {"disease": "माइग्रेन", "symptoms": "तेज सिरदर्द उल्टी रोशनी से परेशानी migraine headache nausea light sensitivity", "severity": "Moderate", "advice": "💡 अंधेरे शांत कमरे में लेटें। माथे पर ठंडी पट्टी रखें। बार-बार हो तो डॉक्टर से मिलें।"},
    {"disease": "सर्दी-जुकाम", "symptoms": "नाक बहना छींक गला खराब खांसी runny nose sneezing sore throat cough", "severity": "Mild", "advice": "☕ भाप लें, अदरक की चाय पिएं। 4-7 दिन में ठीक।"},
    {"disease": "टाइफाइड", "symptoms": "लगातार बुखार कमजोरी पेट दर्द भूख नहीं typhoid fever weakness stomach pain", "severity": "High", "advice": "🔬 Widal / ब्लड कल्चर टेस्ट करवाएं। एंटीबायोटिक सिर्फ डॉक्टर की सलाह पर लें।"},
    {"disease": "फूड पॉइजनिंग", "symptoms": "उल्टी दस्त पेट दर्द vomiting diarrhea stomach pain", "severity": "Moderate", "advice": "💧 ORS पिएं, हल्का खाना खाएं। 48 घंटे में आराम न मिले तो डॉक्टर को दिखाएं।"},
    {"disease": "निमोनिया", "symptoms": "तेज बुखार खांसी सीने में दर्द सांस फूलना pneumonia cough chest pain shortness breath", "severity": "Critical", "advice": "🚑 तुरंत अस्पताल जाएं। छाती का एक्स-रे करवाएं।"},
    {"disease": "एनीमिया", "symptoms": "थकान चक्कर कमजोरी चेहरा पीला anemia fatigue dizziness weakness", "severity": "Moderate", "advice": "🩸 खून की जांच (CBC) करवाएं। पालक, चुकंदर, अनार खाएं।"},
    {"disease": "किडनी स्टोन", "symptoms": "कमर में तेज दर्द पेशाब में खून kidney stone back pain blood urine", "severity": "Critical", "advice": "⚠️ तुरंत अस्पताल जाएं। अल्ट्रासाउंड करवाएं और खूब पानी पिएं।"},
    {"disease": "अस्थमा अटैक", "symptoms": "सांस फूलना घरघराहट सीने में जकड़न asthma wheezing shortness breath", "severity": "Critical", "advice": "💨 इनहेलर लें। आराम न मिले तो तुरंत 108 पर कॉल करें।"},
]
df = pd.DataFrame(diseases)

SEV = {
    "Mild": ("#6fd39a", "✅", "घर पर देखभाल काफी है। 2-3 दिन में सुधार न हो तो डॉक्टर से मिलें।"),
    "Moderate": ("#f4c05a", "⚠️", "24-48 घंटे में डॉक्टर से सलाह लें, खासकर लक्षण बढ़ें तो।"),
    "High": ("#fb9a52", "🛑", "आज ही डॉक्टर को दिखाएं।"),
    "Critical": ("#ff7a6b", "🚨", "तुरंत अस्पताल / इमरजेंसी (108) से संपर्क करें।"),
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
    "0 - कोई दर्द नहीं": 0, "1 - हल्का": 1, "2 - कम": 3,
    "3 - मध्यम": 5, "4 - तेज": 7, "5 - असहनीय": 10,
}
PAIN_OPTIONS = list(PAIN_LEVELS.keys())

HELPLINES = [
    ("108", "एम्बुलेंस", "Emergency ambulance"), ("112", "इमरजेंसी", "Police / Fire / Medical"),
    ("102", "मातृ-शिशु सेवा", "Mother & child ambulance"), ("14416", "Tele-MANAS", "Mental health support"),
    ("1098", "चाइल्डलाइन", "Child helpline"), ("1091", "महिला हेल्पलाइन", "Women helpline"),
]

FIRST_AID = {
    "💔 सीने में दर्द / हार्ट अटैक के संकेत": "तुरंत 108 बुलाएं। मरीज को आराम से बैठाएं, कपड़े ढीले करें और उसे चलने न दें। एस्प्रिन तभी दें जब एलर्जी न हो और इमरजेंसी ऑपरेटर/डॉक्टर कहें।",
    "🔥 जलना (Burns)": "जले हिस्से पर 15-20 मिनट बहता ठंडा (बर्फ वाला नहीं) पानी डालें। टूथपेस्ट, मक्खन या बर्फ न लगाएं। छाले न फोड़ें। बड़ा जलना हो तो अस्पताल जाएं।",
    "😮‍💨 गले में कुछ फंसना (Choking)": "वयस्क को आगे झुकाकर पीठ पर 5 जोरदार थपकी दें, फिर पेट पर 5 बार दबाव (Heimlich) दें। न खुले तो 108 बुलाएं।",
    "😵 बेहोशी (Fainting)": "मरीज को पीठ के बल लिटाएं और पैर थोड़े ऊपर उठाएं। सांस जांचें। मुंह में पानी न डालें। होश न आए तो 108 बुलाएं।",
    "🩸 तेज खून बहना": "साफ कपड़े से घाव पर सीधा और मजबूत दबाव डालें। कपड़ा भीग जाए तो हटाएं नहीं, ऊपर और कपड़ा रखें। अस्पताल पहुंचें।",
    "🐍 सांप का काटना": "मरीज को शांत और स्थिर रखें, काटे हुए अंग को हिलाएं नहीं। काटना, चूसना या कसकर बांधना न करें। तुरंत अस्पताल (एंटी-वेनम) पहुंचें।",
}

EXAMPLES = [
    "मुझे 3 दिन से बुखार सा लग रहा है, बदन दुख रहा है और बहुत कमजोरी महसूस हो रही है।",
    "naak beh rahi hai, gala kharab hai aur khansi bhi hai",
    "तेज बुखार, जोड़ों में दर्द और शरीर पर रैश हो गए हैं",
]

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
                "disease": row["disease"], "severity": row["severity"], "advice": row["advice"],
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
        cat = "कम वजन"
    elif b < 25:
        cat = "सामान्य"
    elif b < 30:
        cat = "अधिक वजन"
    else:
        cat = "मोटापा"
    return round(b, 1), cat, (round(18.5 * m * m, 1), round(24.9 * m * m, 1))


def ring_html(score):
    c = "#6fd39a" if score >= 75 else "#f4c05a" if score >= 50 else "#ff7a6b"
    label = "बढ़िया" if score >= 75 else "ध्यान दें" if score >= 50 else "सलाह लें"
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


# =====================================================================
# 5. SESSION STATE
# =====================================================================
DEFAULTS = dict(
    temp_c=36.6, temp_f=97.9, pain=PAIN_OPTIONS[0], spo2=98, pulse=78, weight=70.0, height=170.0,
    unit="°C", name="", age=25, gender="पुरुष", symptoms=[], symptom_text="", duration="1-2 दिन",
    chat=[], history=[], log=[], water=0, sleep=7.0, result=None,
)
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)


def reset_inputs():
    for k in ("temp_c", "temp_f", "pain", "spo2", "pulse", "weight", "height", "symptoms", "symptom_text", "duration"):
        st.session_state[k] = DEFAULTS[k]
    st.session_state.result = None


def use_example(text):
    st.session_state.symptom_text = text


def queue_question(q):
    st.session_state.pending_q = q


# =====================================================================
# 6. SIDEBAR - PROFILE & VITALS
# =====================================================================
with st.sidebar:
    st.markdown('<div class="brand">Medi<span>Mind</span> AI</div>', unsafe_allow_html=True)
    st.caption("आपका स्मार्ट हेल्थ साथी")

    with st.expander("👤 प्रोफाइल", expanded=False):
        st.text_input("नाम (Name)", key="name")
        c1, c2 = st.columns(2)
        c1.number_input("उम्र", 1, 110, key="age")
        c2.selectbox("लिंग", ["पुरुष", "महिला", "अन्य"], key="gender")

    st.markdown("**🩺 आपके वाइटल्स**")
    st.radio("तापमान यूनिट", ["°C", "°F"], key="unit", horizontal=True)
    if st.session_state.unit == "°C":
        st.slider("तापमान (°C)", 35.0, 42.0, step=0.1, key="temp_c")
        temp_c = st.session_state.temp_c
        temp_txt = f"{temp_c:.1f}°C"
    else:
        st.slider("Temperature (°F)", 95.0, 107.6, step=0.1, key="temp_f")
        temp_c = (st.session_state.temp_f - 32) * 5 / 9
        temp_txt = f"{st.session_state.temp_f:.1f}°F"

    st.select_slider("🤕 दर्द का स्तर", options=PAIN_OPTIONS, key="pain")
    st.slider("🫁 SpO₂ (%)", 80, 100, key="spo2")
    st.slider("❤️ पल्स (bpm)", 40, 180, key="pulse")

    c1, c2 = st.columns(2)
    c1.number_input("वजन (kg)", 20.0, 300.0, step=0.5, key="weight")
    c2.number_input("ऊंचाई (cm)", 50.0, 250.0, step=1.0, key="height")

    pain_val = PAIN_LEVELS[st.session_state.pain]
    score = health_score(temp_c, pain_val, st.session_state.spo2, st.session_state.pulse)
    bmi, bmi_cat, ideal = bmi_info(st.session_state.weight, st.session_state.height)

    st.markdown("**🚀 हेल्थ स्कोर**")
    st.markdown(ring_html(score), unsafe_allow_html=True)
    st.caption(f"BMI **{bmi}** ({bmi_cat}) · आदर्श वजन {ideal[0]}-{ideal[1]} kg")
    if st.session_state.spo2 < 94:
        st.error("SpO₂ 94% से कम है। डॉक्टर से तुरंत संपर्क करें।")

    st.button("🔄 सब कुछ रीसेट करें", on_click=reset_inputs, use_container_width=True)

# =====================================================================
# 7. HERO
# =====================================================================
status_pill = (
    '<span class="pill on">● Gemini Live जुड़ा है</span>' if GEMINI_ENABLED
    else '<span class="pill off">● Gemini बंद (API key नहीं मिली)</span>'
)
st.markdown(
    f"""
<div class="hero">
  <h1 class="display">MediMind AI</h1>
  <p>लक्षण बताइए, कुछ ही सेकंड में संभावित कारण, गंभीरता और अगला कदम जानिए। हिंदी, English या Hinglish में।</p>
  <div class="pills">{status_pill}<span class="pill">11 रोगों का लोकल डेटाबेस</span><span class="pill">Google Search से वैलिडेशन</span></div>
  <svg class="ecg" viewBox="0 0 600 120" preserveAspectRatio="none" aria-hidden="true">
    <path d="M0 70 H110 L135 70 L150 30 L172 108 L192 12 L212 70 H300 L322 70 L336 46 L352 70 H600"/>
  </svg>
</div>
""",
    unsafe_allow_html=True,
)

tab_dx, tab_chat, tab_med, tab_diet, tab_track, tab_sos = st.tabs(
    ["🩺 जांच", "💬 AI चैट", "💊 दवा", "🥗 डाइट", "📈 ट्रैकर", "🚑 इमरजेंसी"]
)

# =====================================================================
# 8. TAB - DIAGNOSE
# =====================================================================
def render_result(res):
    if res["emergency"]:
        st.markdown(
            '<div class="sos"><b>🚨 इमरजेंसी के संकेत मिले हैं</b><br>'
            'देर न करें। तुरंत <a href="tel:108">📞 108 डायल करें</a> या नजदीकी अस्पताल जाएं।</div>',
            unsafe_allow_html=True,
        )

    results = res["local"]
    if results:
        top = results[0]
        color, emoji, triage = SEV[top["severity"]]
        chips = "".join(f'<span class="chip">{m}</span>' for m in top["matched"][:10])
        st.markdown(
            f"""
<div class="verdict" style="--sev:{color}">
  <span class="badge">{emoji} {top['severity']}</span>
  <div class="name">{top['disease']}</div>
  <div class="advice">{top['advice']}</div>
  <div class="triage"><b>अगला कदम:</b> {triage}</div>
  <div style="margin-top:12px" class="muted">मिले हुए लक्षण: {chips}</div>
</div>""",
            unsafe_allow_html=True,
        )
        m1, m2, m3 = st.columns(3)
        m1.metric("विश्वसनीयता", f"{top['confidence']}%")
        m2.metric("लक्षण मिलान", f"{top['ratio']}%")
        m3.metric("हेल्थ स्कोर", f"{res['score']}/100")

        if len(results) > 1:
            st.markdown('<div class="section-title">अन्य संभावनाएं</div>', unsafe_allow_html=True)
            for r in results[1:4]:
                c = SEV[r["severity"]][0]
                st.markdown(
                    f'<div style="--sev:{c}"><div class="diff-row"><span>{r["disease"]} '
                    f'<span class="muted">· {r["severity"]}</span></span><b>{r["confidence"]}%</b></div>'
                    f'<div class="bar"><i style="width:{r["confidence"]}%"></i></div></div>',
                    unsafe_allow_html=True,
                )
    else:
        st.warning("लोकल डेटाबेस में कोई मजबूत मिलान नहीं मिला। नीचे Gemini की राय देखें या लक्षण थोड़े और विस्तार से लिखें।")

    st.markdown('<div class="section-title" style="margin-top:22px">🌐 Gemini की राय (Google Search के साथ)</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if res["gemini"]:
            st.markdown(res["gemini"])
        else:
            st.info(res["gemini_err"] or "Gemini से जवाब नहीं मिला।")

    if res["tip"]:
        st.success(f"🌟 **आज की टिप:** {res['tip']}")

    d1, d2 = st.columns(2)
    d1.download_button("⬇️ रिपोर्ट डाउनलोड करें", build_report(res), file_name="medimind_report.txt", use_container_width=True)
    if d2.button("➕ ट्रैकर में सेव करें", use_container_width=True, key="save_from_result"):
        st.session_state.log.append({
            "समय": res["time"], "तापमान °C": round(res["temp"], 1), "SpO₂": res["spo2"],
            "पल्स": res["pulse"], "स्कोर": res["score"], "टिप्पणी": results[0]["disease"] if results else "-",
        })
        st.toast("ट्रैकर में सेव हो गया ✅")


with tab_dx:
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        with st.form("dx_form"):
            st.markdown('<div class="section-title">अपने लक्षण बताएं</div>', unsafe_allow_html=True)
            st.multiselect("लक्षण चुनें (Select symptoms)", SYMPTOM_OPTIONS, key="symptoms")
            st.text_area(
                "या अपनी भाषा में लिखें (हिंदी / English / Hinglish)",
                key="symptom_text", height=130,
                placeholder="जैसे: मुझे 3 दिन से बुखार सा लग रहा है और बदन दुख रहा है…",
            )
            st.select_slider("कब से हैं?", ["कुछ घंटे", "1-2 दिन", "3-5 दिन", "1 हफ्ते से ज्यादा", "कई हफ्ते"], key="duration")
            submitted = st.form_submit_button("⚡ जांच करें", use_container_width=True)
        st.caption("कोशिश करके देखें:")
        for i, ex in enumerate(EXAMPLES):
            st.button(f"“{ex[:48]}…”", key=f"ex{i}", on_click=use_example, args=(ex,), use_container_width=True)

    with right:
        st.markdown('<div class="section-title">लाइव वाइटल्स</div>', unsafe_allow_html=True)
        v1, v2 = st.columns(2)
        v1.metric("तापमान", temp_txt)
        v2.metric("SpO₂", f"{st.session_state.spo2}%")
        v3, v4 = st.columns(2)
        v3.metric("पल्स", f"{st.session_state.pulse} bpm")
        v4.metric("BMI", f"{bmi}", bmi_cat)
        with st.container(border=True):
            st.markdown("**ऐसे लिखें तो बेहतर नतीजे मिलेंगे**")
            st.markdown("- कितने दिन से और कितना तेज\n- साथ में कोई और दिक्कत\n- कोई पुरानी बीमारी या चल रही दवा")

    if submitted:
        text = st.session_state.symptom_text
        ui = st.session_state.symptoms
        if not text.strip() and not ui:
            st.warning("कृपया कम से कम एक लक्षण चुनें या लिखें।")
        else:
            with st.status("MediMind आपके लक्षणों का विश्लेषण कर रहा है…", expanded=True) as status:
                st.write("🔎 लोकल डेटाबेस से मिलान…")
                local, processed = local_diagnose(text, ui)
                emergency = any(k in (text or "").lower() for k in EMERGENCY_WORDS) or "chest pain" in processed
                profile = dict(name=st.session_state.name, age=st.session_state.age, gender=st.session_state.gender)

                st.write("🌐 Gemini से वैलिडेशन…")
                prompt = (
                    f"{STYLE_RULES}\n\nPatient: age {profile['age']}, {profile['gender']}. "
                    f"Symptoms: \"{text}\" {', '.join(ui)}. Duration: {st.session_state.duration}. "
                    f"Vitals: temp {temp_c:.1f}C, SpO2 {st.session_state.spo2}%, pulse {st.session_state.pulse}.\n"
                    "Give, in markdown with bold headings: 1) Most likely condition and 1-2 alternatives, "
                    "2) Severity (Mild/Moderate/High/Critical), 3) Home-care steps, 4) Red-flag signs that need a doctor now."
                )
                g_text, g_err = ask_gemini(prompt, search=True)

                st.write("✨ पर्सनल टिप तैयार हो रही है…")
                tip, _ = ask_gemini(
                    f"{STYLE_RULES}\nUser health score {score}/100, symptoms: {processed}. "
                    "Give ONE daily preventive health tip in under 15 words, in the language of the symptoms."
                )
                if not tip:
                    tip = random.choice([
                        "आज 7-8 गिलास पानी पिएं। 💧", "आज 30 मिनट टहलें।", "7 घंटे की नींद पूरी करें।", "एक ताजा फल जरूर खाएं।",
                    ])
                status.update(label="विश्लेषण पूरा ✅", state="complete", expanded=False)

            res = dict(
                time=datetime.now().strftime("%d %b %Y, %I:%M %p"), input=text, symptoms=ui, duration=st.session_state.duration,
                emergency=emergency, local=local, gemini=g_text, gemini_err=g_err, tip=tip, score=score,
                temp=temp_c, spo2=st.session_state.spo2, pulse=st.session_state.pulse, profile=profile,
            )
            st.session_state.result = res
            st.session_state.last_disease = local[0]["disease"] if local else ""
            st.session_state.history.append({
                "समय": res["time"], "संभावित रोग": local[0]["disease"] if local else "-",
                "गंभीरता": local[0]["severity"] if local else "-", "स्कोर": score,
            })

    if st.session_state.result:
        st.markdown("---")
        render_result(st.session_state.result)
    else:
        st.info("⬆️ ऊपर लक्षण भरें और **जांच करें** दबाएं। नतीजे यहां दिखेंगे।")

# =====================================================================
# 9. TAB - CHAT
# =====================================================================
with tab_chat:
    st.markdown('<div class="section-title">MediMind से कुछ भी पूछें</div>', unsafe_allow_html=True)
    st.caption("सामान्य स्वास्थ्य सवाल, खान-पान, नींद, घरेलू नुस्खे। जवाब Google Search की मदद से आते हैं।")
    if not GEMINI_ENABLED:
        st.warning("चैट के लिए GEMINI_API_KEY सेट करना जरूरी है।")
    else:
        sugg = ["कमजोरी में क्या खाएं?", "बुखार में डॉक्टर के पास कब जाएं?", "अच्छी नींद के आसान तरीके", "घर पर ORS कैसे बनाएं?"]
        cols = st.columns(len(sugg))
        for i, s in enumerate(sugg):
            cols[i].button(s, key=f"sg{i}", on_click=queue_question, args=(s,), use_container_width=True)

        for m in st.session_state.chat:
            with st.chat_message("user" if m["role"] == "user" else "assistant", avatar="🧑" if m["role"] == "user" else "🩺"):
                st.markdown(m["text"])

        q = st.chat_input("अपना सवाल लिखें…") or st.session_state.pop("pending_q", None)
        if q:
            st.session_state.chat.append({"role": "user", "text": q})
            with st.chat_message("user", avatar="🧑"):
                st.markdown(q)
            ctx = "\n".join(
                f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['text']}" for m in st.session_state.chat[-8:]
            )
            with st.chat_message("assistant", avatar="🩺"):
                with st.spinner("जवाब तैयार हो रहा है…"):
                    ans, err = ask_gemini(f"{STYLE_RULES}\n\nConversation:\n{ctx}\nAssistant:", search=True)
                reply = ans or f"माफ़ कीजिए, जवाब नहीं मिल पाया। {err}"
                st.markdown(reply)
            st.session_state.chat.append({"role": "ai", "text": reply})

        if st.session_state.chat:
            st.button("🧹 चैट साफ करें", on_click=lambda: st.session_state.update(chat=[]))

# =====================================================================
# 10. TAB - MEDICINE
# =====================================================================
with tab_med:
    st.markdown('<div class="section-title">दवा की जानकारी और इंटरैक्शन</div>', unsafe_allow_html=True)
    mode = st.radio("क्या करना है?", ["दो दवाओं का इंटरैक्शन", "एक दवा की जानकारी"], horizontal=True)
    if mode.startswith("दो"):
        c1, c2 = st.columns(2)
        med_a = c1.text_input("दवा A", placeholder="Paracetamol")
        med_b = c2.text_input("दवा B", placeholder="Ibuprofen")
        if st.button("🔍 इंटरैक्शन जांचें", type="primary"):
            if med_a and med_b:
                with st.spinner("जांच हो रही है…"):
                    ans, err = ask_gemini(
                        f"{STYLE_RULES}\nCheck interaction between '{med_a}' and '{med_b}'. In markdown give: "
                        "**Interaction level** (None/Mild/Moderate/Severe), **What can happen**, **Safety advice**. "
                        "Reply in the language the user used for the names/question (default Hinglish).",
                        search=True,
                    )
                with st.container(border=True):
                    st.markdown(ans) if ans else st.error(err)
            else:
                st.warning("दोनों दवाओं के नाम लिखें।")
    else:
        med = st.text_input("दवा का नाम", placeholder="Azithromycin")
        if st.button("📖 जानकारी दिखाएं", type="primary"):
            if med:
                with st.spinner("जानकारी ला रहे हैं…"):
                    ans, err = ask_gemini(
                        f"{STYLE_RULES}\nExplain medicine '{med}' in markdown: **Used for**, **Common side effects**, "
                        "**Who should avoid it**, **Important precautions**. Do not give a personal dosage.",
                        search=True,
                    )
                with st.container(border=True):
                    st.markdown(ans) if ans else st.error(err)
            else:
                st.warning("दवा का नाम लिखें।")
    st.caption("⚠️ कोई भी दवा शुरू या बंद करने से पहले डॉक्टर / फार्मासिस्ट से पूछें।")

# =====================================================================
# 11. TAB - DIET
# =====================================================================
with tab_diet:
    st.markdown('<div class="section-title">पर्सनल डाइट प्लान</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.4, 1, 1])
    disease_in = c1.text_input("स्थिति / रोग", value=st.session_state.get("last_disease", "") or "वायरल बुखार")
    pref = c2.selectbox("खान-पान", ["शाकाहारी", "मांसाहारी", "वीगन", "जैन"])
    goal = c3.selectbox("मकसद", ["जल्दी रिकवरी", "वजन घटाना", "वजन बढ़ाना", "एनर्जी बढ़ाना"])
    if st.button("🥗 डाइट प्लान बनाएं", type="primary"):
        if disease_in.strip():
            with st.spinner("प्लान बन रहा है…"):
                ans, err = ask_gemini(
                    f"{STYLE_RULES}\nCreate a simple Indian diet plan for '{disease_in}'. Diet type: {pref}. Goal: {goal}. "
                    f"Person: BMI {bmi} ({bmi_cat}). Use markdown: **क्या खाएं** (3+ bullets), **क्या न खाएं** (3+ bullets), "
                    "and a **1-day sample meal plan** (breakfast, lunch, snack, dinner). Reply in the language of the condition name."
                )
            with st.container(border=True):
                st.markdown(ans) if ans else st.error(err)
        else:
            st.warning("रोग / स्थिति का नाम लिखें।")

# =====================================================================
# 12. TAB - TRACKER
# =====================================================================
with tab_track:
    st.markdown('<div class="section-title">हेल्थ ट्रैकर</div>', unsafe_allow_html=True)
    t1, t2 = st.columns([1.2, 1], gap="large")
    with t1:
        if st.button("💾 आज के वाइटल्स सेव करें", type="primary"):
            st.session_state.log.append({
                "समय": datetime.now().strftime("%d %b %Y, %I:%M %p"), "तापमान °C": round(temp_c, 1),
                "SpO₂": st.session_state.spo2, "पल्स": st.session_state.pulse, "स्कोर": score, "टिप्पणी": f"BMI {bmi}",
            })
            st.toast("सेव हो गया ✅")
        if st.session_state.log:
            log_df = pd.DataFrame(st.session_state.log)
            st.line_chart(log_df.set_index("समय")[["स्कोर"]], color="#47d1c0", height=220)
            st.line_chart(log_df.set_index("समय")[["तापमान °C"]], color="#ff7a6b", height=180)
            st.dataframe(log_df, use_container_width=True, hide_index=True)
            e1, e2 = st.columns(2)
            e1.download_button("⬇️ CSV डाउनलोड", log_df.to_csv(index=False).encode("utf-8-sig"), "medimind_log.csv", use_container_width=True)
            e2.button("🗑️ लॉग साफ करें", on_click=lambda: st.session_state.update(log=[]), use_container_width=True)
        else:
            st.info("अभी कोई एंट्री नहीं है। ऊपर बटन से पहली एंट्री सेव करें।")
        if st.session_state.history:
            with st.expander("🕘 पिछली जांचें"):
                st.dataframe(pd.DataFrame(st.session_state.history[::-1]), use_container_width=True, hide_index=True)
    with t2:
        with st.container(border=True):
            st.markdown("**💧 आज का पानी**")
            st.progress(min(st.session_state.water / 8, 1.0), text=f"{st.session_state.water} / 8 गिलास")
            w1, w2 = st.columns(2)
            w1.button("➕ एक गिलास", on_click=lambda: st.session_state.update(water=st.session_state.water + 1), use_container_width=True)
            w2.button("➖ घटाएं", on_click=lambda: st.session_state.update(water=max(0, st.session_state.water - 1)), use_container_width=True)
        with st.container(border=True):
            st.markdown("**😴 कल रात की नींद**")
            st.slider("घंटे", 0.0, 12.0, step=0.5, key="sleep", label_visibility="collapsed")
            sl = st.session_state.sleep
            st.caption("बढ़िया, 7-9 घंटे सही रेंज है ✅" if 7 <= sl <= 9 else "नींद थोड़ी कम है, आज जल्दी सोने की कोशिश करें।" if sl < 7 else "थोड़ी ज्यादा है, दिनचर्या पर ध्यान दें।")

# =====================================================================
# 13. TAB - EMERGENCY
# =====================================================================
with tab_sos:
    st.markdown('<div class="section-title">इमरजेंसी नंबर (भारत)</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, (num, hi, en) in enumerate(HELPLINES):
        cols[i % 3].markdown(
            f'<div class="help-card"><a href="tel:{num}"><div class="num">📞 {num}</div></a>'
            f'<b>{hi}</b><br><span class="muted">{en}</span></div>',
            unsafe_allow_html=True,
        )
        if i % 3 == 2:
            cols = st.columns(3)
    st.markdown('<div class="section-title" style="margin-top:24px">फर्स्ट-एड गाइड</div>', unsafe_allow_html=True)
    for title, body in FIRST_AID.items():
        with st.expander(title):
            st.write(body)
    st.caption("ये सिर्फ शुरुआती मदद के सामान्य कदम हैं। गंभीर स्थिति में पहले 108 पर कॉल करें।")

st.markdown(
    '<div class="disclaimer">© 2025 MediMind AI · <b>Disclaimer:</b> यह एक AI सिमुलेशन है, डॉक्टर का विकल्प नहीं। '
    "सटीक निदान और इलाज के लिए हमेशा योग्य डॉक्टर से सलाह लें।</div>",
    unsafe_allow_html=True,
)
