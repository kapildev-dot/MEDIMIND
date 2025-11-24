import streamlit as st
import pandas as pd
from fuzzywuzzy import fuzz
import re
import time
from google import genai
from google.genai import types
import json
import random

# ---- Page Config ----
st.set_page_config(
    page_title="MediMind AI Doctor - PRO V10 (Ultimate Professional)",
    page_icon="⭐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---- 0. GEMINI API INITIALIZATION & TOOLS ----

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
    MODEL_NAME = 'gemini-2.5-flash'
    GEMINI_ENABLED = True
except Exception as e:
    # Changed to warning for better UX since API is optional for local features
    st.sidebar.warning("🚨 Gemini API Key लोड नहीं हो पाई। Gemini Validation Disabled.")
    GEMINI_ENABLED = False
    client = None

# ---- 1. PREMIUM CSS STYLING (V10 Enhancements) ----

# Function to render the Health Score as an attractive circle
def render_health_score_circle(score):
    color = "var(--success-color)"
    if score < 50:
        color = "var(--danger-color)"
    elif score < 75:
        color = "var(--warning-color)"

    st.markdown(f"""
    <div class="health-circle-container">
        <div class="health-circle" style="
            background: conic-gradient({color} {score}%, #1a1a1a {score}%);
            border: 5px solid #0a0a0a;
            box-shadow: 0 0 10px rgba(0, 255, 136, 0.4);
        ">
            <div class="health-score-inner">
                <span style="color: {color};">{score}%</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<style>
    /* ------------------------------------------------ */
    /* --------- V10 PREMIUM CORE THEME FIXES ---------- */
    /* ------------------------------------------------ */
    :root {
        --neon-green: #00ff88;
        --dark-bg: #121212;
        --sidebar-bg: #0a0a0a;
        --success-color: #00ff88;
        --warning-color: #ffc107;
        --danger-color: #ff4444;
        --info-color: #00b894;
    }

    section.main { background-color: var(--dark-bg); color: #e0e0e0; }
    .stApp { color: #e0e0e0; }

    /* Neon Title with Animation */
    @keyframes neon-glow {
        0% { text-shadow: 0 0 5px var(--neon-green), 0 0 10px #00b894; }
        100% { text-shadow: 0 0 20px var(--neon-green), 0 0 30px #00b894; }
    }
    .title {
        font-size: 5.8rem !important; font-weight: 900; text-align: center;
        background: linear-gradient(90deg, var(--neon-green), #00b894, var(--neon-green));
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin: 0; padding: 20px 0 10px 0;
        animation: neon-glow 1.5s ease-in-out infinite alternate;
    }

    /* Animated Gradient Line Separator */
    @keyframes moveGradient {
        0% { background-position: 0% 50%; }
        100% { background-position: 100% 50%; }
    }
    .gradient-line {
        height: 3px;
        background: linear-gradient(90deg, transparent, var(--neon-green), transparent);
        background-size: 200% 100%;
        animation: moveGradient 3s linear infinite alternate;
        margin-bottom: 20px;
        border-radius: 50px;
    }

    /* Sidebar Styling */
    .stSidebar {
        background-color: var(--sidebar-bg);
        box-shadow: 0 4px 25px rgba(0, 0, 0, 0.7);
        border-right: 4px solid var(--neon-green);
        color: #e0e0e0;
        border-radius: 0 15px 15px 0;
    }

    /* Health Score Visualization */
    .health-circle-container { display: flex; justify-content: center; align-items: center; margin-top: 15px; }
    .health-circle { position: relative; width: 120px; height: 120px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
    .health-score-inner { position: absolute; width: 100px; height: 100px; background: var(--sidebar-bg); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; font-weight: bold; }

    /* Form Button Styling (Diagnose) */
    div.stForm button {
        background-color: var(--neon-green); color: var(--dark-bg); font-weight: bold; height: 50px;
        width: 100%; border-radius: 8px; transition: all 0.3s ease;
        box-shadow: 0 0 10px rgba(0, 255, 136, 0.4);
    }
    div.stForm button:hover {
        background-color: #00b894;
        box-shadow: 0 0 25px rgba(0, 255, 136, 1);
    }

    /* Metric Card Styling */
    [data-testid="stMetric"] {
        background-color: #1a1a1a; border: 1px solid var(--neon-green); padding: 15px; border-radius: 12px;
        box-shadow: 0 0 15px rgba(0, 255, 136, 0.3); transition: all 0.3s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: scale(1.02); box-shadow: 0 0 30px rgba(0, 255, 136, 0.6);
    }

    /* Final Advice/Info box styling (Gemini Output) */
    .stAlert {
        border-radius: 12px !important; background-color: #1a1a1a !important;
        color: #e0e0e0 !important; border-left: 5px solid var(--neon-green) !important;
        padding: 15px; margin-bottom: 15px;
    }

    /* Preventive Tip Styling */
    .preventive-tip {
        border-radius: 12px !important; background-color: #1a1a1a !important;
        color: #e0e0e0 !important; border-left: 5px solid #ffc107 !important; /* Warning/Yellow color */
        padding: 15px; margin-top: 20px;
        font-style: italic;
    }

    /* NEW: Dedicated Chat Container Style */
    .chat-container {
        padding: 15px;
        border: 2px solid var(--info-color);
        border-radius: 12px;
        margin-top: 20px;
        background-color: #1a1a1a;
    }
</style>
""", unsafe_allow_html=True)

# --- [DATA & MAPPINGS REMAIN UNCHANGED] ---
LOCAL_TO_STANDARD_MAP = {
    "बुखार सा लग रहा है": "fever", "बुखार जैसा": "fever", "तेज गरम": "high fever", "शरीर तप रहा है": "high fever",
    "bukhar hai": "fever", "tez bukhar": "high fever", "जुखाम": "runny nose", "gira gira sa": "weakness",
    "कमजोरी": "weakness", "एनर्जी नहीं है": "weakness", "thakawat": "fatigue", "थकावट": "fatigue",
    "jaldi thak jana": "fatigue", "चक्कर आ रहे हैं": "dizziness", "chakkar": "dizziness",
    "bada dukh raha hai": "body ache", "बदन दुख रहा है": "body ache", "dard": "body ache",
    "जोड़ों में दर्द": "joint pain", "joint pain": "joint pain", "छाती में दर्द": "chest pain",
    "seene mein dard": "chest pain", "pet mein gudgud": "stomach pain", "पेट में गुड़गुड़": "stomach pain",
    "पेट खराब": "diarrhea", "loose motion": "diarrhea", "उल्टी जैसा": "nausea", "vomiting ho rahi है": "vomiting",
    "जलन": "acidity", "acidity": "acidity", "kabhi": "constipation", "कब्जी": "constipation",
    "पाखाना नहीं हो रहा": "constipation", "saans lene mein takleef": "shortness breath",
    "saans phoolna": "shortness breath",
}
diseases = [
    {"disease":"वायरल बुखार", "symptoms":"बुखार सिरदर्द बदन दर्द खांसी कमजोरी थकान fever headache body ache cough weakness", "severity":"Mild", "advice":"🌡️ पैरासिटामॉल लें, खूब पानी पिएं। 5-7 दिन में ठीक।"},
    {"disease":"डेंगू", "symptoms":"तेज बुखार जोड़ों में दर्द रैश थकान आँख दर्द high fever joint pain rash fatigue", "severity":"Critical", "advice":"🚨 तुरंत अस्पताल! प्लेटलेट्स चेक करवाएं। पपीता, नारियल पानी पिएं।"},
    {"disease":"दिल का दौरा", "symptoms":"सीने में दर्द सांस फूलना पसीना बायां हाथ दर्द chest pain shortness breath sweating left arm", "severity":"Critical", "advice":"🔥 108 तुरंत बुलाएं! एस्प्रिन चबाएं। अभी जाएं!"},
    {"disease":"माइग्रेन", "symptoms":"तेज सिरदर्द उल्टी रोशनी से परेशानी migraine nausea light sensitivity", "severity":"Moderate", "advice":"💡 अंधेरे में लेटें। ठंडी पट्टी रखें। डॉक्टर से सलाह लें।"},
    {"disease":"सर्दी-जुकाम", "symptoms":"नाक बहना छींक गला खराब खांसी runny nose sneezing sore throat cough", "severity":"Mild", "advice":"☕ भाप लें। अदरक चाय। 4-7 दिन में ठीक।"},
    {"disease":"टाइफाइड", "symptoms":"लगातार बुखार कमजोरी पेट दर्द भूख नहीं typhoid fever weakness", "severity":"High", "advice":"🔬 Widal टेस्ट। एंटीबायोटिक लें (डॉक्टर की सलाह पर)।"},
    {"disease":"फूड पॉइजनिंग", "symptoms":"उल्टी दस्त पेट दर्द vomiting diarrhea stomach pain", "severity":"Moderate", "advice":"💧 ORS पिएं। हल्का खाना। 48 घंटे में ठीक।"},
    {"disease":"निमोनिया", "symptoms":"तेज बुखार खांसी सीने में दर्द सांस फूलना pneumonia cough chest pain", "severity":"Critical", "advice":"🚑 तुरंत अस्पताल! एक्स-रे करवाएं। यह गंभीर हो सकता है।"},
    {"disease":"एनीमिया", "symptoms":"थकान चक्कर कमजोरी चेहरा पीला anemia fatigue dizziness", "severity":"Moderate", "advice":"🩸 खून की जांच। पालक, अनार खाएं।"},
    {"disease":"किडनी स्टोन", "symptoms":"कमर में तेज दर्द पेशाब में खून kidney stone back pain blood urine", "severity":"Critical", "advice":"⚠️ तुरंत अस्पताल! अल्ट्रासाउंड करवाएं।"},
    {"disease":"अस्थमा अटैक", "symptoms":"सांस फूलना घरघराहट सीने में जकड़न asthma wheezing shortness breath", "severity":"Critical", "advice":"💨 इनहेलर लें। नहीं रुका तो 108 पर कॉल करें!"},
]
df = pd.DataFrame(diseases)
SYMPTOM_MAPPING_FOR_UI = {
    "बुखार / Fever": "fever", "सिरदर्द / Headache": "headache", "बदन दर्द / Body Ache": "body ache",
    "खांसी / Cough": "cough", "कमजोरी / Weakness": "weakness", "थकान / Fatigue": "fatigue",
    "तेज बुखार / High Fever": "high fever", "जोड़ों में दर्द / Joint Pain": "joint pain",
    "रैश / Rash": "rash", "आँख दर्द / Eye Pain": "eye pain", "सीने में दर्द / Chest Pain": "chest pain",
    "सांस फूलना / Shortness Breath": "shortness breath", "उल्टी / Nausea": "nausea",
    "दस्त / Diarrhea": "diarrhea", "चक्कर आना / Dizziness": "dizziness", "पेट दर्द / Stomach Pain": "stomach pain",
    "गला खराब / Sore Throat": "sore throat", "नाक बहना / Runny Nose": "runny nose"
}
bilingual_symptom_options = sorted(list(SYMPTOM_MAPPING_FOR_UI.keys()))

# ---- 2. ADVANCED DIAGNOSTIC ENGINE (Functions) ----
# advanced_semantic_diagnose (Fuzzy Logic) - UNCHANGED
def advanced_semantic_diagnose(input_text, selected_symptoms_keys):
    selected_standard_symptoms = [SYMPTOM_MAPPING_FOR_UI[key] for key in selected_symptoms_keys if key in SYMPTOM_MAPPING_FOR_UI]
    # ... rest of the function logic
    combined_input = input_text.lower() + " " + " ".join(selected_standard_symptoms)
    user_clean = re.sub(r'[^a-zA-Z\u0900-\u097F\s]', ' ', combined_input)
    processed_text = user_clean
    for local_phrase, standard_symptom in LOCAL_TO_STANDARD_MAP.items():
        processed_text = processed_text.replace(local_phrase, standard_symptom)
    final_search_text = re.sub(r'\s+', ' ', processed_text).strip()

    results = []
    # Identify unique standard symptoms present in the final_search_text
    present_symptoms = set(symptom for symptom in LOCAL_TO_STANDARD_MAP.values() if symptom in final_search_text)

    for _, row in df.iterrows():
        # Get the symptoms for the disease
        disease_symptoms = row["symptoms"].split()
        # Calculate how many of the user's symptoms match the disease symptoms
        match_count = len([sym for sym in disease_symptoms if sym in present_symptoms])

        score = fuzz.token_set_ratio(final_search_text, row["symptoms"])
        min_threshold = 48
        if row["severity"] == "Critical": min_threshold = 40

        if score >= min_threshold:
            confidence = min(100, score + 10)
            results.append({"disease": row["disease"], "confidence": confidence, "severity": row["severity"], "advice": row["advice"], "raw_score": score, "match_count": match_count, "disease_symptoms": disease_symptoms})

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results, final_search_text, list(present_symptoms)

# 🛑 # 🛑 NEW: GEMINI AI REAL-TIME DIAGNOSIS (ULTRA-FLEXIBLE MULTILINGUAL PROMPT) 🛑
def gemini_search_and_diagnose(search_text):
    if not GEMINI_ENABLED:
        return "Gemini Validation: API Key कॉन्फ़िगर नहीं है।"

    prompt = f"""
    आप एक विशेषज्ञ मेडिकल सलाहकार हैं जो Google Search का उपयोग करके जानकारी को प्रमाणित करते हैं।
    उपयोगकर्ता के मुख्य लक्षण (Symptoms) हैं: "{search_text}"

    **CRITICAL**: अपनी प्रतिक्रिया (Response) **सख्त रूप से उसी भाषा** में दें जिस भाषा में उपयोगकर्ता ने मुख्य लक्षण (`search_text`) दिए हैं। आपको उपयोगकर्ता की भाषा की पहचान करके उसी भाषा में जवाब देना है।

    1. प्राथमिक संभावित रोग (Primary Disease) की पहचान करें।
    2. उस रोग के लिए गंभीरता स्तर (जैसे: Mild, Moderate, High, Critical) का अनुमान लगाएं।
    3. रोग के लिए एक संक्षिप्त, विश्वसनीय सलाह (Medical Advice) प्रदान करें।

    **Output Format (Strictly use user's language):**
    Primary Disease/रोग का नाम: [Disease Name/रोग का नाम in user's language]
    Severity/गंभीरता: [Severity Level/गंभीरता स्तर in user's language]
    AI Advice/जेमिनी की सलाह: [Advice in User's Language]
    """

    try:
        config = types.GenerateContentConfig(
            tools=[{"google_search": {}}]
        )
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=config,
        )
        return response.text
    except Exception as e:
        error_message = str(e)
        if "503 UNAVAILABLE" in error_message or "rate limit" in error_message:
            # Error message translated to be language-neutral when possible
            return "Gemini API Call Error: Server is busy or rate limit exceeded. Please try again later."
        return f"Gemini API Call Error or connection issue: {e}"

# 🛑 NEW FUNCTION: GEMINI PREVENTIVE TIP (ULTRA-FLEXIBLE MULTILINGUAL PROMPT) 🛑
def gemini_get_preventive_tip(health_score, search_text):
    if not GEMINI_ENABLED:
        # Fallback in Hindi/English
        return random.choice([
            "पानी खूब पिएं और हाइड्रेटेड रहें। (Drink plenty of water and stay hydrated.)",
            "आज 30 मिनट टहलें। (Walk for 30 minutes today.)",
            "एक फल ज़रूर खाएं। (Be sure to eat one fruit.)",
            "7 घंटे की नींद पूरी करें। (Complete 7 hours of sleep.)"
        ])

    prompt = f"""
    यूजर का हेल्थ स्कोर {health_score}% है, और उन्होंने हाल ही में इन लक्षणों की जांच की: "{search_text}".
    
    **CRITICAL**: स्कोर और लक्षणों को ध्यान में रखते हुए, उन्हें एक **एकल, संक्षिप्त, दैनिक निवारक स्वास्थ्य टिप (preventive health tip)** उसी भाषा में दें, जिस भाषा में मुख्य लक्षण दिए गए थे। टिप 15 शब्दों से अधिक नहीं होनी चाहिए।
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except:
        return "आपके स्वास्थ्य स्कोर के लिए एक खास टिप: आज 7-8 गिलास पानी पिएं! 💧"

# 🛑 NEW FUNCTION: GEMINI MEDICATION INTERACTION CHECKER (ULTRA-FLEXIBLE MULTILINGUAL PROMPT) 🛑
def gemini_check_interaction(med_a, med_b):
    if not GEMINI_ENABLED:
        return "Gemini API अनुपलब्ध है। इंटरेक्शन की जाँच नहीं की जा सकती।"

    prompt = f"""
    आप एक विशेषज्ञ फार्मासिस्ट हैं। आपको Google Search का उपयोग करके यह जाँच करनी है कि क्या दवा '{med_a}' और दवा '{med_b}' के बीच कोई गंभीर या मध्यम इंटरैक्शन (Interaction) है या नहीं।
    
    **CRITICAL**: अपनी प्रतिक्रिया (Response) **सख्त रूप से उसी भाषा** में दें, जिस भाषा में दवा के नाम या प्रश्न पूछे गए हैं।
    
    1. इंटरैक्शन का प्रकार (जैसे: कोई नहीं, हल्का, मध्यम, गंभीर) बताएं।
    2. एक संक्षिप्त सलाह दें कि क्या उन्हें एक साथ लेना सुरक्षित है या नहीं।
    
    **Output Format (Strictly use user's language):**
    इंटरैक्शन प्रकार/Interaction Type: [प्रकार/Type in user's language]
    सुरक्षा सलाह/Safety Advice: [सलाह/Advice in user's language]
    """
    try:
        config = types.GenerateContentConfig(
            tools=[{"google_search": {}}]
        )
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=config,
        )
        return response.text
    except Exception as e:
        return f"Gemini API त्रुटि: {e}"

# 🛑 NEW FUNCTION: GEMINI DIET PLAN GENERATOR (ULTRA-FLEXIBLE MULTILINGUAL PROMPT) 🛑
def gemini_generate_diet_plan(disease_name):
    if not GEMINI_ENABLED:
        return "Gemini API अनुपलब्ध है। डाइट प्लान जनरेट नहीं किया जा सकता।"
        
    prompt = f"""
    आप एक विशेषज्ञ आहार विशेषज्ञ (Dietician) हैं। कृपया '{disease_name}' के लिए एक संक्षिप्त, सरल, और प्रभावी आहार योजना (Diet Plan) बनाएं।
    
    **CRITICAL**: डाइट प्लान की प्रतिक्रिया (Response) **सख्त रूप से उसी भाषा** में दें, जिस भाषा में रोग का नाम ('{disease_name}') दिया गया है।
    
    कम से कम 3 'क्या खाएं' (Do's) और 3 'क्या न खाएं' (Don'ts) बुलेट पॉइंट्स में प्रदान करें।
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"Gemini API त्रुटि: {e}"

# Health Score Calculation (Retained)
def calculate_health_score(temp, pain):
    score = 100
    temp_deviation = abs(temp - 36.6)
    temp_penalty = temp_deviation * 8
    score -= temp_penalty
    pain_penalty = pain * 4
    score -= pain_penalty
    score = max(0, min(100, score))
    return int(score)

# NEW FUNCTION: BMI Calculation
def calculate_bmi(weight_kg, height_cm):
    if height_cm <= 0:
        return 0.0, "अवैध ऊंचाई"
    # Convert height from cm to meters
    height_m = height_cm / 100
    # BMI formula: weight (kg) / height (m)^2
    bmi = weight_kg / (height_m ** 2)
    
    category = "सामान्य (Normal)"
    if bmi < 18.5:
        category = "कम वजन (Underweight)"
    elif bmi >= 25.0 and bmi < 30.0:
        category = "अधिक वजन (Overweight)"
    elif bmi >= 30.0:
        category = "मोटापा (Obese)"
        
    return round(bmi, 2), category


# ---- 3. UI/UX: Sidebar and Main Input (V10 Implementation) ----
# --- जरूरी फंक्शन (Function to Convert C to F) ---
def c_to_f(celsius):
    return (celsius * 9/5) + 32

# --- दर्द स्तरों के लिए मैपिंग (Mapping for Pain Levels) ---
PAIN_LEVELS = {
    "0 - कोई दर्द नहीं (None)": 0,
    "1 - हल्का दर्द (Mild)": 1,
    "2 - कम दर्द (Low)": 3,
    "3 - मध्यम दर्द (Moderate)": 5,
    "4 - तेज दर्द (High)": 7,
    "5 - असहनीय दर्द (Severe)": 10
}
pain_options = list(PAIN_LEVELS.keys())

# --- Streamlit Sidebar UI (Updated) ---

st.sidebar.markdown('## 🔬 स्वास्थ्य ट्रैकर & टूल्स 🩺')

# Use Tabs for a cleaner sidebar
tab_symptoms, tab_tracker, tab_tools = st.sidebar.tabs(["लक्षण", "ट्रैकर", "टूल"])

# --- Tab 1: Symptoms ---
with tab_symptoms:
    st.header("1️⃣ लक्षण चुनें (Bilingual)")
    selected_ui_symptoms = st.multiselect(
        "अपने लक्षण चुनें (Select Symptoms)", bilingual_symptom_options, default=[], key="ui_symptoms"
    )

    if st.button("🔄 सभी इनपुट साफ करें", key="reset_button_sidebar"):
        # Reset all relevant session state variables
        st.session_state.ui_symptoms = []
        st.session_state.temp_unit = "C"
        st.session_state.temp_tracker = 36.6
        if 'temp_tracker_f' in st.session_state: del st.session_state.temp_tracker_f # Clean F tracker
        st.session_state.pain_tracker = pain_options[0]
        st.session_state.text_input_key = ""
        st.session_state.weight_kg = 70.0 # Reset BMI to default
        st.session_state.height_cm = 170.0 # Reset BMI to default
        st.rerun()

# --- Tab 2: Tracker (Temp, Pain, BMI) ---
with tab_tracker:
    st.header("2️⃣ मुख्य मेट्रिक्स")

    # --- Temperature Unit Selection (C/F) ---
    if 'temp_unit' not in st.session_state:
        st.session_state.temp_unit = "C"

    temp_unit = st.radio(
        "🌡️ तापमान यूनिट चुनें (Unit)",
        ("C", "F"),
        key="temp_unit",
        horizontal=True
    )

    # --- Temperature Slider based on Unit ---
    if temp_unit == "C":
        temp = st.slider("तापमान (°C)", 35.0, 42.0, 36.6, 0.1, key="temp_tracker", help="अगर बुखार है तो ज़रूर डालें")
        temp_calc = temp
        temp_display = f"{temp}°C"
    else: # F
        min_f, max_f, default_f = c_to_f(35.0), c_to_f(42.0), c_to_f(36.6)
        temp_f = st.slider("Temperature (°F)", min_f, max_f, default_f, 0.2, key="temp_tracker_f", help="Select temperature in Fahrenheit")
        temp_calc = (temp_f - 32) * 5/9 # Convert back to C for calculation
        temp_display = f"{temp_f:.1f}°F" # Display F value

    # --- Pain Level Selection (Words) ---
    pain_level_text = st.selectbox(
        "🤕 दर्द का स्तर (Pain Level)",
        pain_options,
        key="pain_tracker",
        help="0=कोई दर्द नहीं, 5=असहनीय दर्द"
    )
    # Get the numeric value for calculation
    pain_value = PAIN_LEVELS[pain_level_text]

    # --- BMI Inputs ---
    st.markdown("---")
    st.subheader("⚖️ $\text{BMI}$ कैलकुलेटर")
    if 'weight_kg' not in st.session_state: st.session_state.weight_kg = 70.0
    if 'height_cm' not in st.session_state: st.session_state.height_cm = 170.0
    
    weight_kg = st.number_input("वजन (Weight in kg)", 20.0, 300.0, st.session_state.weight_kg, 0.1, key="weight_kg")
    height_cm = st.number_input("ऊंचाई (Height in cm)", 50.0, 250.0, st.session_state.height_cm, 1.0, key="height_cm")
    
    bmi, bmi_category = calculate_bmi(weight_kg, height_cm)

    st.caption(f"आपका BMI: **{bmi}** ({bmi_category})")


    # --- Health Score Display ---
    current_score = calculate_health_score(temp_calc, pain_value)

    st.markdown("---")
    st.subheader("🚀 आपका हेल्थ स्कोर")
    render_health_score_circle(current_score)
    st.caption(f"Temp: **{temp_display}** | Pain: **{pain_level_text}**") # Added display for clarity

# --- Tab 3: Advanced Gemini Tools ---
with tab_tools:
    st.header("4️⃣ एडवांस्ड $\text{Gemini}$ टूल्स")
    
    # 1. Medication Interaction Checker
    st.subheader("💊 दवा इंटरेक्शन चेक")
    med_a = st.text_input("दवा $\text{A}$ का नाम", placeholder="Paracetamol", key="med_a")
    med_b = st.text_input("दवा $\text{B}$ का नाम", placeholder="Ibuprofen", key="med_b")
    if st.button("🔍 इंटरेक्शन चेक करें", key="check_interaction_button"):
        if med_a and med_b:
            with st.spinner('⏳ $\text{Gemini}$ इंटरैक्शन की जाँच कर रहा है...'):
                interaction_result = gemini_check_interaction(med_a, med_b)
                st.markdown(f'<div class="stAlert" style="border-left: 5px solid var(--info-color) !important;">{interaction_result}</div>', unsafe_allow_html=True)
        else:
            st.warning("कृपया दोनों दवाओं के नाम दर्ज करें।")

    st.markdown("---")
    
    # 2. Personalized Diet Plan Generator (uses top result from diagnosis)
    st.subheader("🍎 डाइट प्लान जेनरेटर")
    # Show the disease if diagnosis was run, otherwise let user input
    default_disease = st.session_state.get('last_diagnosed_disease', 'वायरल बुखार')
    diet_disease = st.text_input("रोग का नाम (जिसके लिए डाइट चाहिए)", value=default_disease, key="diet_disease_input")
    
    if st.button("🥗 डाइट प्लान बनाएं", key="generate_diet_button"):
        if diet_disease:
            with st.spinner('⏳ $\text{Gemini}$ डाइट प्लान बना रहा है...'):
                diet_plan = gemini_generate_diet_plan(diet_disease)
                st.markdown(f'<div class="stAlert" style="border-left: 5px solid var(--info-color) !important;">{diet_plan}</div>', unsafe_allow_html=True)
        else:
            st.warning("कृपया रोग का नाम दर्ज करें।")


# --- Main Area UI ---
st.markdown('<div class="title">MediMind Ultimate PRO</div>', unsafe_allow_html=True)
st.markdown('<div class="gradient-line"></div>', unsafe_allow_html=True)
submitted = False
with st.form("diagnosis_form", clear_on_submit=False):
    input_text = st.text_area(
        "या यहाँ अपनी भाषा में लिखें (हिंदी/English/Hinglish) 💬",
        value=st.session_state.get('text_input_key', ''),
        height=150,
        placeholder="मुझे 3 दिन से बुखार सा लग रहा है, बदन दुख रहा है और बहुत कमजोरी महसूस हो रही है।",
        key="text_input_key"
    )
    submitted = st.form_submit_button("⚡️ Diagnose / निदान करें", type="primary")

st.markdown("---")

# ---- 4. HYBRID PREDICTION & OUTPUT ----

if submitted or (st.session_state.get('ui_symptoms') and not input_text.strip()):

    # Emergency check (Retained)
    if any(k in input_text.lower() for k in ["सीने में दर्द", "chest pain", "सांस नहीं", "heart attack", "108", "बेहोश", "दम घुट रहा है"]):
        st.markdown('<div class="emergency">🚨 EMERGENCY ALERT! तुरंत 108 बुलाएं या नजदीकी अस्पताल जाएं! 🚨</div>', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center;'><a href='tel:108' style='color:#00ff88;'>📞 108 डायल करें</a></h2>", unsafe_allow_html=True)
        st.stop()

    # 💥 AI THINKING ANIMATION 💥
    with st.spinner('🧠 MediMind AI Diagnosis Engine सोच रहा है... (Applying Semantic NLP & Fuzzy Logic)'):
        time.sleep(1.5)

    # Run Local Diagnosis
    results, processed_text, present_symptoms = advanced_semantic_diagnose(input_text, st.session_state.get('ui_symptoms', []))

    # Run Gemini Phase 1: Diagnosis and Validation
    if GEMINI_ENABLED:
        with st.spinner('🌐 Google Gemini AI से रियल-टाइम वैलिडेशन प्राप्त कर रहा है...'):
            gemini_advice = gemini_search_and_diagnose(processed_text)
            time.sleep(1)
    else:
        gemini_advice = "Gemini Validation: API Key कॉन्फ़िगर नहीं है।"

    # --- Display Local Diagnosis ---
    st.markdown("<p style='color:#00ff88; font-size: 1.5rem; font-weight: bold;'>🧠 MediMind AI (Local DB Match)</p>", unsafe_allow_html=True)

    if results:
        top = results[0]
        # Store top disease for diet plan tool
        st.session_state['last_diagnosed_disease'] = top['disease']
        
        emoji_map = {"Mild":"✅", "Moderate":"⚠️", "High":"🛑", "Critical":"🚨"}

        col1, col2, col3 = st.columns([3, 2, 2])

        with col1:
            st.markdown(f"## {emoji_map.get(top['severity'])} {top['disease']}")
            st.progress(top['confidence'] / 100)
            st.markdown(f'<p style="color:#e0e0e0; font-style: italic;">निष्कर्ष: आपका हेल्थ स्कोर **{current_score}%** है।</p>', unsafe_allow_html=True)

        with col2:
            st.markdown(f'<div data-testid="stMetric">**विश्वसनीयता**<p style="font-size: 1.8rem; color: #00ff88; font-weight: bold;">{top["confidence"]}%</p></div>', unsafe_allow_html=True)

        with col3:
            st.markdown(f'<div data-testid="stMetric">**गंभीरता स्तर**<p style="font-size: 1.8rem; color: #e0e0e0; font-weight: bold;">{top["severity"]}</p></div>', unsafe_allow_html=True)


        st.markdown(f'<div class="severity-{top["severity"].lower()}">**👨‍⚕️ लोकल डेटाबेस की सलाह:** {top["advice"]}</div>', unsafe_allow_html=True)

        st.markdown("---")

        # Symptom Match Visualization
        st.subheader("📊 लक्षण मिलान विश्लेषण (Symptom Match Analysis)")

        # Data for charting
        chart_data = []
        # Get top 3 diseases for comparison
        for res in results[:3]:
            # Calculate match ratio for charting
            match_ratio = res['match_count'] / len(res['disease_symptoms']) if res['disease_symptoms'] else 0
            chart_data.append({
                'बीमारी': res['disease'],
                'मिलान प्रतिशत': match_ratio * 100
            })

        chart_df = pd.DataFrame(chart_data)
        st.bar_chart(chart_df, x='बीमारी', y='मिलान प्रतिशत', color='#00ff88')


        if len(results) > 1:
            with st.expander("💡 अन्य संभावित अंतर (Differential Diagnosis) देखें"):
                other_results = pd.DataFrame(results[1:4])[["disease", "confidence"]]
                other_results["confidence"] = other_results["confidence"].apply(lambda x: f"{x}%")
                other_results.rename(columns={"disease": "बीमारी", "confidence": "विश्वसनीयता"}, inplace=True)
                st.table(other_results)

    else:
        st.warning("कोई भी बीमारी 40% से अधिक आत्मविश्वास से नहीं मिली।")

    st.markdown("---")

    # --- Display Gemini Phase 1: Validation ---
    st.markdown("<p style='color:#00ff88; font-size: 1.5rem; font-weight: bold;'>🌐 Google Gemini AI (Real-time Validation)</p>", unsafe_allow_html=True)

    if gemini_advice and isinstance(gemini_advice, str) and 'Gemini API कॉल में त्रुटि' not in gemini_advice:
        formatted_advice = gemini_advice.replace(
            "रोग का नाम:", "**रोग का नाम:**"
        ).replace(
            "गंभीरता:", "\n\n**गंभीरता:**"
        ).replace(
            "जेमिनी की सलाह:", "\n\n**जेमिनी की सलाह:**"
        )
        st.markdown(f'<div class="stAlert">{formatted_advice}</div>', unsafe_allow_html=True)
    elif gemini_advice and isinstance(gemini_advice, str):
        st.error(f"⚠️ Gemini AI से रियल-टाइम सलाह प्राप्त नहीं हो सकी। कारण: {gemini_advice}")
    else:
        st.warning("⚠️ Gemini AI से रियल-टाइम सलाह प्राप्त नहीं हो सकी।")

    st.markdown("---")

    # --- Display Gemini Phase 2: Preventive Tip ---
    with st.spinner('✨ Gemini AI से व्यक्तिगत स्वास्थ्य टिप प्राप्त कर रहा है...'):
        preventive_tip = gemini_get_preventive_tip(current_score, processed_text)
        time.sleep(0.5)
        st.markdown("<p style='color:#ffc107; font-size: 1.5rem; font-weight: bold;'>🌟 आपका व्यक्तिगत निवारक स्वास्थ्य टिप</p>", unsafe_allow_html=True)
        st.markdown(f'<div class="preventive-tip">**टिप:** {preventive_tip}</div>', unsafe_allow_html=True)


    # Final Warning/Debug Info
    with st.expander("🛠️ Advanced Debug Info"):
        st.info(f"AI सर्च टेक्स्ट: **{processed_text}**")
        st.write(f"वर्तमान हेल्थ स्कोर: **{current_score}%**")
        st.write(f"वर्तमान BMI: **{bmi}** ({bmi_category})")
        st.write(f"पहचाने गए लक्षण: **{', '.join(present_symptoms)}**")

else:
    st.info("⬆️ ऊपर लक्षण चुनें या अपनी भाषा में लिखें, फिर **'Diagnose / निदान करें'** बटन दबाएं। AI तुरंत डायग्नोसिस देगा!")

st.markdown("---")

# 🛑 NEW SECTION: CHAT WITH GEMINI AI 🛑
st.subheader("💬 MediMind AI से सामान्य स्वास्थ्य चैट (Real-time Search Enabled)")
if GEMINI_ENABLED:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    chat_question = st.text_input("अपने स्वास्थ्य से संबंधित कोई भी सामान्य प्रश्न पूछें:", placeholder="कमजोरी महसूस होने पर क्या खाना चाहिए?", key="chat_input")
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
        
    if st.button("❓ सवाल पूछें", key="chat_button") and chat_question:
        
        # 1. Add user query to history
        st.session_state.chat_history.append({"role": "user", "text": chat_question})
        
        try:
            with st.spinner('⏳ Gemini जवाब तैयार कर रहा है... (Google Search का उपयोग करके)'):
                
                # 💥 CRITICAL IMPROVEMENT: Add Google Search Tool configuration
                config = types.GenerateContentConfig(
                    tools=[{"google_search": {}}]
                )
                
                chat_response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=chat_question,
                    config=config,  # <--- CONFIG ADDED HERE
                )
                
                # 2. Add AI response to history
                st.session_state.chat_history.append({"role": "ai", "text": chat_response.text})
                
        except Exception as e:
            st.session_state.chat_history.append({"role": "ai", "text": f"क्षमा करें, Gemini चैट में त्रुटि आ गई: {e}"})

    # Display chat history
    # NOTE: The LaTeX fix for MediMind AI (removing $) is applied here.
    for message in reversed(st.session_state.chat_history):
        if message["role"] == "user":
            st.markdown(f'**👤 आप:** {message["text"]}')
        else:
            st.markdown(f'**🤖 MediMind AI:** {message["text"]}')

    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.warning("💬 Gemini चैट टूल API की अनुपलब्धता के कारण अक्षम है।")


st.caption("© 2025 MediMind Ultimate PRO V10 | **Disclaimer:** यह AI सिमुलेशन है – अंतिम और सटीक निदान के लिए हमेशा एक योग्य डॉक्टर से सलाह लें।")
