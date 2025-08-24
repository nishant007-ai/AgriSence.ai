import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import speech_recognition as sr
from gtts import gTTS
from PIL import Image
import os
import time
import io
import base64
import openai  # pip install openai
import requests
# -------------------------
# CONFIG
# -------------------------
CHANNEL_ID = "2888465"
READ_API_KEY = "5VFH0F5WIYLIN4ES"
BASE_URL = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"

# Plant.id API Key
PLANT_ID_API_KEY = "PASTE_YOUR_PLANTID_API_KEY"  # Replace with your actual Plant.id API key

# OpenWeather
WEATHER_API_KEY = "b9737316a3c1fae00504caf5fcc25c61"
CITY_NAME = "Mumbai"

# OpenAI
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"
openai.api_key = OPENAI_API_KEY

st.set_page_config(page_title="🌱 Smart Farming AI System", layout="wide")

# -------------------------
# FETCH DATA FROM THINGSPEAK
# -------------------------
@st.cache_data(ttl=30)
def fetch_data(results=50):
    try:
        url = f"{BASE_URL}?api_key={READ_API_KEY}&results={results}"
        response = requests.get(url)
        data = response.json()
        feeds = pd.DataFrame(data["feeds"])
        for col in ["field1", "field2", "field3", "field4"]:
            feeds[col] = pd.to_numeric(feeds[col], errors="coerce")
        feeds["created_at"] = pd.to_datetime(feeds["created_at"])
        return feeds
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# -------------------------
# WEATHER DATA
# -------------------------
def fetch_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=hi"
        response = requests.get(url).json()
        temp = response["main"]["temp"]
        humidity = response["main"]["humidity"]
        desc = response["weather"][0]["description"]
        return temp, humidity, desc
    except:
        return None, None, None

# -------------------------
# PLANT.ID CROP DISEASE DETECTION
# -------------------------
def detect_disease(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    payload = {
        "api_key": PLANT_ID_API_KEY,
        "images": [img_str],
        "modifiers": ["crops_simple"],
        "plant_details": ["disease", "common_names", "url", "description"]
    }

    try:
        response = requests.post("https://api.plant.id/v2/health_assessment", json=payload)
        result = response.json()

        if "health_assessment" in result and "diseases" in result["health_assessment"]:
            diseases = result["health_assessment"]["diseases"]
            if diseases:
                first_disease = diseases[0]
                name = first_disease.get("name", "Unknown Disease")
                description = first_disease.get("description", "No description available.")
                treatment = first_disease.get("treatment", {}).get("biological", "No treatment info.")
                return {"name": name, "description": description, "treatment": treatment}

        return {"error": "No disease detected"}

    except Exception as e:
        return {"error": str(e)}

# -------------------------
# DASHBOARD PAGE
# -------------------------
def dashboard():
    # Neon animation CSS and JS to remove after 2.5 seconds
    st.markdown("""
        <style>
        .neon-title-animate {
            font-size: 2.5rem;
            font-weight: bold;
            color: #39ff14;
            text-shadow:
                0 0 10px #39ff14,
                0 0 20px #39ff14,
                0 0 40px #0fa,
                0 0 80px #0fa;
            border-bottom: 4px solid #39ff14;
            display: inline-block;
            padding-bottom: 8px;
            margin-bottom: 20px;
            animation: neon-fade 2.5s ease-in-out forwards;
        }
        @keyframes neon-fade {
            0% {
                opacity: 1;
                filter: brightness(1.5);
            }
            80% {
                opacity: 1;
                filter: brightness(1.5);
            }
            100% {
                opacity: 1;
                filter: brightness(1);
                text-shadow: 0 0 5px #39ff14, 0 0 10px #39ff14;
            }
        }
        .neon-title-static {
            font-size: 2.5rem;
            font-weight: bold;
            color: #39ff14;
            text-shadow:
                0 0 5px #39ff14,
                0 0 10px #39ff14;
            border-bottom: 4px solid #39ff14;
            display: inline-block;
            padding-bottom: 8px;
            margin-bottom: 20px;
        }
        </style>
        <div id="neon-title" class="neon-title-animate">🌿 Smart Irrigation Dashboard</div>
        <script>
        setTimeout(function() {
            var el = window.parent.document.getElementById('neon-title');
            if (el) {
                el.className = 'neon-title-static';
            }
        }, 2500);
        </script>
    """, unsafe_allow_html=True)

    data = fetch_data()
    if data.empty:
        st.warning("No data available from ThingSpeak. Please check your API Key and Channel ID.")
        return

    # ...rest of your dashboard code...

    latest = data.iloc[-1]
    moisture = latest["field1"]
    air_quality = latest["field2"]
    temperature = latest["field3"]
    humidity = latest["field4"]

    weather_temp, weather_humidity, weather_desc = fetch_weather(CITY_NAME)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💧 Soil Moisture (%)", f"{moisture:.2f}")
    col2.metric("🌬 Air Quality (ppm)", f"{air_quality:.2f}")
    col3.metric("🌡 Temperature (°C)", f"{temperature:.2f}")
    col4.metric("💦 Humidity (%)", f"{humidity:.2f}")

    if weather_temp is not None:
        st.info(f"🌤 Weather: {weather_temp}°C, {weather_desc} (Humidity: {weather_humidity}%)")

    if moisture < 40 or humidity < 50 or weather_humidity < 50:
        st.warning("💧 Soil is dry - Watering Recommended")
    else:
        st.success("✅ Soil moisture levels are sufficient")

    if air_quality > 1000:
        st.error("⚠️ Poor Air Quality - Take Precautions")
    else:
        st.info("🌬 Air Quality is Good")

    st.subheader("📊 Sensor Data Trends")
    fig1 = px.line(data, x="created_at", y="field1", title="Soil Moisture Over Time")
    fig2 = px.line(data, x="created_at", y="field2", title="Air Quality Over Time")
    fig3 = px.line(data, x="created_at", y="field3", title="Temperature Over Time")
    fig4 = px.line(data, x="created_at", y="field4", title="Humidity Over Time")

    col5, col6 = st.columns(2)
    col5.plotly_chart(fig1, use_container_width=True)
    col6.plotly_chart(fig2, use_container_width=True)
    col7, col8 = st.columns(2)
    col7.plotly_chart(fig3, use_container_width=True)
    col8.plotly_chart(fig4, use_container_width=True)

    st.caption("Data Source: ThingSpeak API")

        # -------------------------
    # Farmer Advice (Below Charts)
    # -------------------------
    st.markdown("---")
    st.subheader("🗣 Farmer Voice Advice")

    # Language choice
    lang_choice = st.selectbox("Select Advice Language", ["English", "Hindi", "Marathi"])
    lang_codes = {"English": "en", "Hindi": "hi", "Marathi": "mr"}

    # Generate advice based on all readings
    advice_text = ""

    # Soil moisture check
    if moisture < 30:
        advice_text += {
            "English": "Soil moisture is very low. Water the crops immediately.\n",
            "Hindi": "मिट्टी की नमी बहुत कम है। तुरंत फसलों को पानी दें।\n",
            "Marathi": "मातीतील आर्द्रता खूप कमी आहे. त्वरित पिकांना पाणी द्या.\n"
        }[lang_choice]
    elif moisture < 40:
        advice_text += {
            "English": "Soil is getting dry. Plan watering soon.\n",
            "Hindi": "मिट्टी सूखने लगी है। जल्द पानी देने की योजना बनाएं।\n",
            "Marathi": "माती कोरडी होत आहे. लवकरच पाणी देण्याची योजना करा.\n"
        }[lang_choice]
    else:
        advice_text += {
            "English": "Soil moisture is good. No watering needed.\n",
            "Hindi": "मिट्टी की नमी अच्छी है। पानी देने की आवश्यकता नहीं है।\n",
            "Marathi": "मातीतील आर्द्रता चांगली आहे. पाणी देण्याची गरज नाही.\n"
        }[lang_choice]

    # Air quality check
    if air_quality > 2000:
        advice_text += {
            "English": "Air quality is dangerous. Avoid staying outside for long.\n",
            "Hindi": "हवा की गुणवत्ता खतरनाक है। लंबे समय तक बाहर रहने से बचें।\n",
            "Marathi": "हवेची गुणवत्ता धोकादायक आहे. जास्त वेळ बाहेर राहणे टाळा.\n"
        }[lang_choice]
    elif air_quality > 1000:
        advice_text += {
            "English": "Air quality is poor. Take precautions.\n",
            "Hindi": "हवा की गुणवत्ता खराब है। सावधान रहें।\n",
            "Marathi": "हवेची गुणवत्ता खराब आहे. काळजी घ्या.\n"
        }[lang_choice]
    else:
        advice_text += {
            "English": "Air quality is good.\n",
            "Hindi": "हवा की गुणवत्ता अच्छी है।\n",
            "Marathi": "हवेची गुणवत्ता चांगली आहे.\n"
        }[lang_choice]

    # Temperature check
    if temperature > 35:
        advice_text += {
            "English": "High temperature detected. Water crops early morning or late evening.\n",
            "Hindi": "उच्च तापमान है। फसलों को सुबह जल्दी या शाम को पानी दें।\n",
            "Marathi": "जास्त तापमान आहे. सकाळी लवकर किंवा संध्याकाळी पिकांना पाणी द्या.\n"
        }[lang_choice]
    elif temperature < 15:
        advice_text += {
            "English": "Low temperature detected. Protect crops from cold.\n",
            "Hindi": "कम तापमान है। फसलों को ठंड से बचाएं।\n",
            "Marathi": "कमी तापमान आहे. पिकांना थंडीपासून वाचा.\n"
        }[lang_choice]
    else:
        advice_text += {
            "English": "Temperature is optimal for crops.\n",
            "Hindi": "तापमान फसलों के लिए अनुकूल है।\n",
            "Marathi": "तापमान पिकांसाठी योग्य आहे.\n"
        }[lang_choice]

    # Humidity check
    if humidity < 40:
        advice_text += {
            "English": "Humidity is low. Increase watering frequency.\n",
            "Hindi": "नमी कम है। पानी देने की आवृत्ति बढ़ाएं।\n",
            "Marathi": "आर्द्रता कमी आहे. पाणी देण्याची वारंवारता वाढवा.\n"
        }[lang_choice]
    elif humidity > 80:
        advice_text += {
            "English": "Humidity is high. Watch for fungal diseases.\n",
            "Hindi": "नमी अधिक है। फफूंद रोगों के लिए सावधान रहें।\n",
            "Marathi": "आर्द्रता जास्त आहे. बुरशीजन्य रोगांपासून सावध रहा.\n"
        }[lang_choice]
    else:
        advice_text += {
            "English": "Humidity is within a healthy range.\n",
            "Hindi": "नमी स्वस्थ सीमा में है।\n",
            "Marathi": "आर्द्रता योग्य पातळीवर आहे.\n"
        }[lang_choice]

    # Weather condition
    if weather_desc and "rain" in weather_desc.lower():
        advice_text += {
            "English": "Rain expected. Reduce irrigation.\n",
            "Hindi": "बारिश की संभावना है। सिंचाई कम करें।\n",
            "Marathi": "पावसाची शक्यता आहे. सिंचन कमी करा.\n"
        }[lang_choice]
    elif weather_desc and "sun" in weather_desc.lower():
        advice_text += {
            "English": "Sunny weather. Monitor soil dryness.\n",
            "Hindi": "धूप का मौसम है। मिट्टी की नमी पर नज़र रखें।\n",
            "Marathi": "उन्हाळे हवामान आहे. मातीच्या आर्द्रतेवर लक्ष ठेवा.\n"
        }[lang_choice]

    # Show advice text
    st.write(advice_text)

    # Convert to speech
    try:
        tts_lang = lang_codes[lang_choice]
        tts = gTTS(advice_text, lang=tts_lang)
        tts_file = "farmer_advice.mp3"
        tts.save(tts_file)
        st.audio(tts_file)
    except Exception as e:
        st.error(f"TTS Error: {e}")

# -------------------------
# BLYNK Manual Motor Control
# -------------------------


BLYNK_TOKEN = "z7raHxh6KV5xky0cy-5BY72wss90d9zo"

def get_motor_status():
    """Fetch current motor state from Blynk"""
    try:
        url = f"https://blynk.cloud/external/api/get?token={BLYNK_TOKEN}&V1"
        r = requests.get(url)
        if r.status_code == 200:
            return r.text.strip() == "1"
    except:
        return None

def control_motor(state):
    """Turn motor ON or OFF"""
    url = f"https://blynk.cloud/external/api/update?token={BLYNK_TOKEN}&V1={'1' if state else '0'}"
    requests.get(url)

# Get current motor state
motor_is_on = get_motor_status()
if motor_is_on is None:
    st.error("⚠️ Unable to fetch motor status from Blynk.")
else:
    st.markdown("---")
    st.subheader("🚜 Manual Motor Control")
    
    # Toggle button for farmer
    if motor_is_on:
        if st.button("Turn Motor OFF", type="primary"):
            control_motor(False)
            st.success("✅ Motor turned OFF")
    else:
        if st.button("Turn Motor ON", type="primary"):
            control_motor(True)
            st.success("💧 Motor turned ON")
    
    # Show current status
    st.metric("Motor Status", "ON" if motor_is_on else "OFF")

# -------------------------
# VOICE ASSISTANT PAGE
# -------------------------

# -------------------------
# Helper: Call Ollama local server
# -------------------------
def voice_assistant():
    st.header("🎤 Smart Farming Voice Assistant")
    st.write("Ask your farming question in Marathi, Hindi, or English. AI will answer in the same language.")

    # Verify Ollama connection
    try:
        test_response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": "test", "stream": False},
            timeout=5
        )
        if test_response.status_code != 200:
            st.error("⚠️ Ollama server not responding properly")
            st.json(test_response.json())
            return
    except requests.exceptions.ConnectionError:
        st.error("🔌 Could not connect to Ollama. Please ensure:"
                "\n1. Ollama is installed and running (`ollama serve`)"
                "\n2. Model is downloaded (`ollama pull deepseek-r1:8b`)"
                "\n3. Port 11434 is accessible")
        return
    except Exception as e:
        st.error(f"🚨 Unexpected error testing Ollama: {str(e)}")
        return

    lang_choice = st.selectbox("Select Voice Language", ["mr-IN", "hi-IN", "en-IN"])

    if st.button("🎙 Start Listening"):
        try:
            # Record audio
            r = sr.Recognizer()
            with sr.Microphone() as source:
                st.info("🎤 Speak now (listening for 8 seconds)...")
                audio = r.listen(source, phrase_time_limit=8)
                st.success("✅ Recording captured")

            # Transcribe
            try:
                farmer_question = r.recognize_google(audio, language=lang_choice)
                st.subheader("👨‍🌾 Your Question:")
                st.markdown(f'"{farmer_question}"')
            except sr.UnknownValueError:
                st.error("🔇 Could not understand audio. Please speak clearly.")
                return
            except sr.RequestError as e:
                st.error(f"🌐 Speech API error: {str(e)}")
                return

            # Build prompt with sensor context
            sensor_data = fetch_data(results=1)
            context = "Current sensor data: "
            if not sensor_data.empty:
                latest = sensor_data.iloc[-1]
                context += (
                    f"Soil Moisture: {latest['field1']}%, "
                    f"Temperature: {latest['field3']}°C, "
                    f"Humidity: {latest['field4']}%"
                )
            else:
                context = "No sensor data available"

            prompt = {
                "model": OLLAMA_MODEL,
                "prompt": f"""You are an agricultural expert helping Indian farmers. 
                Respond in {lang_choice.split('-')[0]} language.
                Context: {context}
                Question: {farmer_question}
                Provide practical, field-ready advice:""",
                "stream": False,
                "options": {"temperature": 0.7}
            }

            # Get Ollama response
            with st.spinner("🌱 Analyzing your question..."):
                try:
                    response = requests.post(
                        OLLAMA_URL,
                        json=prompt,
                        timeout=30
                    )
                    response.raise_for_status()
                    answer = response.json().get("response", "No response generated")
                    
                    st.subheader("💡 AI Recommendation:")
                    st.markdown(answer)

                    # Convert to speech
                    try:
                        tts_lang = lang_choice.split("-")[0]
                        tts = gTTS(answer, lang=tts_lang)
                        audio_file = io.BytesIO()
                        tts.write_to_fp(audio_file)
                        audio_file.seek(0)
                        
                        st.audio(audio_file, format="audio/mp3")
                        st.success("🎧 Voice response ready!")
                    except Exception as tts_error:
                        st.warning(f"🔊 Couldn't generate voice: {str(tts_error)}")

                except requests.exceptions.Timeout:
                    st.error("⏱️ Ollama response timed out. Try again later.")
                except requests.exceptions.RequestException as e:
                    st.error(f"⚠️ Ollama API error: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Unexpected error: {str(e)}")

        except Exception as e:
            st.error(f"💥 System error: {str(e)}")
# -------------------------
# VOICE ASSISTANT (REPLACEMENT)
# -------------------------
def voice_assistant():
    st.header("🎤 Smart Farming Voice Assistant")
    st.write("Ask your farming question in Marathi, Hindi, or English. AI will answer in the same language.")

    # Verify Ollama connection first
    try:
        test_response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        if test_response.status_code != 200:
            st.error("Ollama server not responding properly")
            st.markdown("""
            **Troubleshooting Steps:**
            1. Open Terminal and run: `ollama serve`
            2. Download model: `ollama pull deepseek-r1:8b`
            3. Keep the terminal running Ollama open
            """)
            return
    except requests.exceptions.ConnectionError:
        st.error("""
        **Ollama Not Running!**
        - First install Ollama from [ollama.ai](https://ollama.ai)
        - Then run these commands:
        ```
        ollama serve
        ollama pull deepseek-r1:8b
        ```
        """)
        return

    lang_choice = st.selectbox("Select Voice Language", ["mr-IN", "hi-IN", "en-IN"])

    if st.button("🎙 Start Listening"):
        try:
            # 1. Audio Recording
            r = sr.Recognizer()
            with sr.Microphone() as source:
                st.info("🎤 Speak your farming question now...")
                r.adjust_for_ambient_noise(source, duration=1)
                try:
                    audio = r.listen(source, timeout=8, phrase_time_limit=10)
                    st.success("✅ Recording complete")
                except sr.WaitTimeoutError:
                    st.error("No speech detected. Please try again.")
                    return

            # 2. Speech Recognition
            try:
                farmer_question = r.recognize_google(audio, language=lang_choice)
                if len(farmer_question.strip()) < 3:
                    raise ValueError("Question too short")
                st.subheader("👨‍🌾 Your Question:")
                st.markdown(f'"{farmer_question}"')
            except Exception as e:
                st.error(f"🔊 Could not understand audio: {str(e)}")
                return

            # 3. Call Ollama with better timeout handling
            prompt = {
                "model": "deepseek-r1:8b",
                "prompt": f"""You are an agricultural expert helping Indian farmers.
                Respond in {lang_choice.split('-')[0]}.
                Question: {farmer_question}
                Provide 3 practical suggestions:""",
                "stream": False,
                "options": {"temperature": 0.5}
            }

            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # First try with shorter timeout
                for i in range(1, 51, 5):
                    progress_bar.progress(i)
                    status_text.text(f"Processing ({i}%)...")
                    time.sleep(0.1)

                response = requests.post(
                    "http://127.0.0.1:11434/api/generate",
                    json=prompt,
                    timeout=15
                )
                
                # If first attempt fails, try with longer timeout
                if response.status_code != 200:
                    for i in range(51, 101, 5):
                        progress_bar.progress(i)
                        status_text.text(f"Retrying ({i}%)...")
                        time.sleep(0.1)
                    
                    response = requests.post(
                        "http://127.0.0.1:11434/api/generate",
                        json=prompt,
                        timeout=25
                    )
                
                response.raise_for_status()
                answer = response.json().get("response")
                
                progress_bar.progress(100)
                status_text.text("Done!")
                time.sleep(0.5)
                progress_bar.empty()
                status_text.empty()

                if not answer:
                    raise ValueError("Empty response from AI")

                st.subheader("🌱 AI Recommendation:")
                st.markdown(answer)

                # Text-to-Speech
                try:
                    tts = gTTS(answer, lang=lang_choice.split('-')[0])
                    audio_bytes = io.BytesIO()
                    tts.write_to_fp(audio_bytes)
                    audio_bytes.seek(0)
                    st.audio(audio_bytes, format="audio/mp3")
                except Exception as tts_error:
                    st.warning(f"Voice generation failed: {str(tts_error)}")

            except requests.exceptions.Timeout:
                st.error("""
                ⏳ Response timeout. Please:
                1. Check Ollama is running in terminal
                2. Try simpler/shorter questions
                3. Restart the app if persists
                """)
            except Exception as e:
                st.error(f"Processing failed: {str(e)}")

        except Exception as e:
            st.error(f"System error: {str(e)}")

# -------------------------
# CROP DISEASE DETECTION PAGE
# -------------------------
def crop_disease_detection():
    st.header("📷 Crop Disease Detection")
    st.write("Upload or capture a crop image to detect possible diseases using AI.")

    camera_image = st.camera_input("Take a photo of your crop")
    uploaded_file = st.file_uploader("Or upload a crop image", type=["jpg", "png", "jpeg"])

    image = None
    if camera_image:
        image = Image.open(camera_image)
    elif uploaded_file:
        image = Image.open(uploaded_file)

    if image:
        st.image(image, caption="Uploaded Crop Image", use_column_width=True)
        with st.spinner("Analyzing with Plant.id..."):
            result = detect_disease(image)

        if "error" in result:
            st.error("⚠️ Could not detect disease. Please try again with a clearer image.")
        else:
            st.success(f"🩺 Disease: {result['name']}")
            st.info(f"📖 Description: {result['description']}")
            st.warning(f"💊 Treatment: {result['treatment']}")

# -------------------------
# AI-POWERED CROP ADVISORY PAGE
# -------------------------


def crop_advisory():
    st.header("🌾 Personalized Crop Advisory (AI Powered)")
    st.write("Get AI-generated advice for your crop based on type, stage, location, sensor data, and an optional image.")

    crop = st.selectbox("Select Crop", ["Wheat", "Rice", "Maize", "Cotton", "Soybean", "Other"])
    stage = st.selectbox("Growth Stage", ["Sowing", "Vegetative", "Flowering", "Fruiting", "Harvest"])
    location = st.text_input("Enter your location (village/city/state)")
    lang_choice = st.selectbox("Preferred Language", ["mr-IN", "hi-IN", "en-IN"])

    st.markdown("**(Optional)** Upload a photo of your crop or field for more personalized advice.")
    uploaded_file = st.file_uploader("Upload Crop/Field Image", type=["jpg", "png", "jpeg"])

    image_desc = ""
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        image_desc = "The farmer has uploaded a crop/field image. Consider this while giving advice."

    # Fetch latest sensor data from ThingSpeak
    data = fetch_data(results=1)
    if not data.empty:
        latest = data.iloc[-1]
        sensor_desc = (
            f"Current sensor readings: "
            f"Soil Moisture: {latest['field1']}%, "
            f"Air Quality: {latest['field2']} ppm, "
            f"Temperature: {latest['field3']}°C, "
            f"Humidity: {latest['field4']}%."
        )
    else:
        sensor_desc = "Sensor data is not available right now."

    if st.button("Get Advisory"):
        prompt = (
            f"Give detailed, practical farming advice for {crop} at the {stage} stage in {location}. "
            f"Include watering, fertilizer, pest/disease management, and weather tips. "
            f"{sensor_desc} {image_desc} Respond in the language code: {lang_choice}."
        )
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            answer = response.choices[0].message["content"]
            st.success("🌱 AI Advisory:")
            st.write(answer)
            tts = gTTS(answer, lang=lang_choice.split("-")[0])
            tts.save("advisory.mp3")
            st.audio("advisory.mp3")
        except Exception as e:
            st.error(f"Could not generate advisory: {e}")
# -------------------------
# SIDEBAR NAVIGATION
# -------------------------
menu = st.sidebar.radio(
    "📌 Navigation",
    ["Dashboard", "Voice Assistant", "Crop Disease Detection", "Crop Advisory", "About Project"]
)

if menu == "Dashboard":
    dashboard()
elif menu == "Voice Assistant":
    voice_assistant()
elif menu == "Crop Disease Detection":
    crop_disease_detection()
elif menu == "Crop Advisory":
    crop_advisory()
elif menu == "About Project":
    st.header("ℹ️ About Project")
    st.write("""
    This AI-based Smart Farming System combines:
    - Live IoT data from ThingSpeak
    - Multi-language professional voice assistant
    - AI crop disease detection from images using Plant.id
    - Weather-based irrigation logic
    - Personalized crop advisory using OpenAI
    - Step-by-step decision-making
    - Farmer-friendly mobile dashboard
    """)