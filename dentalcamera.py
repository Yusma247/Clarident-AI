import streamlit as st
from PIL import Image
from datetime import datetime
import os
import speech_recognition as sr
import shutil

# --- Page Configuration ---
st.set_page_config(page_title="DentalVision AI", page_icon="🦷", layout="wide")

# --- Session State Initialization ---
def init_session_state():
    defaults = {
        'patient_name': "", 'tooth_number': "", 'image_path': None,
        'transcribed_text': "", 'timestamp': "", 'is_recording': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
init_session_state()


# --- CSS Styling ---
def load_css():
    st.markdown("""
        <style>
            header {visibility: hidden;}
            .stApp { background-color: #0E4E5A; }
            .block-container { padding-top: 2rem !important; max-width: 95%; }
            .stTextInput label, .stTextArea label { color: #FFFFFF !important; font-weight: 600; }
            .stTextInput input, .stTextArea textarea { background-color: #F3F4F6; color: #000; border-radius: 8px; border: 1px solid white; }
            .section-header { background-color: white; padding: 12px 20px; border-radius: 10px; color: #0E4E5A; font-weight: 700; font-size: 1.1rem; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; align-items: center; gap: 10px; }
            [data-testid="stCameraInput"] { border-radius: 15px; border: 4px solid white; box-shadow: 0 10px 15px rgba(0,0,0,0.3); }
        </style>
    """, unsafe_allow_html=True)


# --- Logic Functions ---
def reset_workflow():
    """Clears session state to start a new patient record."""
    init_session_state() # Re-initialize to defaults

def save_temp_image(camera_img):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.timestamp = timestamp
    image = Image.open(camera_img)
    filename = f"temp_{timestamp}.jpg"
    if not os.path.exists("temp_data"): os.makedirs("temp_data")
    full_path = os.path.join("temp_data", filename)
    image.save(full_path)
    return full_path

def save_record_permanently():
    if not st.session_state.patient_name or not st.session_state.image_path: return None
    clean_name = "".join(x for x in st.session_state.patient_name if x.isalnum() or x in " _-")
    folder_name = f"{clean_name}_{st.session_state.timestamp}"
    save_dir = os.path.join("saved_records", folder_name)
    os.makedirs(save_dir, exist_ok=True)
    
    img_filename = f"Tooth_{st.session_state.tooth_number}.jpg"
    new_img_path = os.path.join(save_dir, img_filename)
    shutil.copy(st.session_state.image_path, new_img_path)
    
    if st.session_state.transcribed_text:
        txt_path = os.path.join(save_dir, "Doctor_Notes.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Patient: {st.session_state.patient_name}\nTooth: {st.session_state.tooth_number}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n--------------------\n{st.session_state.transcribed_text}")
    return save_dir

def transcribe_voice_notes():
    # ... (same function as before)
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            with st.spinner("Listening..."):
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
        text = recognizer.recognize_google(audio)
        st.session_state.transcribed_text += f" {text}" if st.session_state.transcribed_text else text
    except Exception: st.toast("No speech detected", icon="⚠️")
    finally: st.session_state.is_recording = False


# --- Main App ---
load_css()
col_left, col_space, col_right = st.columns([0.35, 0.05, 0.60])

# ================= LEFT COLUMN =================
with col_left:
    st.markdown("<div style='display: flex; align-items: center; gap: 15px; margin-bottom: 25px;'><img src='https://cdn-icons-png.flaticon.com/512/3004/3004458.png' width='45'><h1 style='color: white; margin: 0; font-size: 2.2rem;'>DentalVision AI</h1></div>", unsafe_allow_html=True)

    st.markdown('<div class="section-header">👤 Patient Information</div>', unsafe_allow_html=True)
    st.session_state.patient_name = st.text_input("Full Name", st.session_state.patient_name)
    st.session_state.tooth_number = st.text_input("Tooth Number", st.session_state.tooth_number)

    # --- ENHANCEMENT: Image Thumbnail Preview ---
    if st.session_state.image_path:
        st.markdown("<p style='color:white; margin-top:10px;'><b>✓ Photo Captured</b></p>", unsafe_allow_html=True)
        st.image(st.session_state.image_path, width=150)
    else:
        st.info("Please capture a photo using the camera on the right.", icon="📸")
    
    st.markdown('<div class="section-header" style="margin-top:20px;">📝 Doctor\'s Notes</div>', unsafe_allow_html=True)
    st.session_state.transcribed_text = st.text_area("Notes", st.session_state.transcribed_text, height=120, label_visibility="collapsed")

    c1, c2 = st.columns(2)
    # --- ENHANCEMENT: Disabled Button State ---
    record_disabled = not st.session_state.image_path
    if c1.button("🎙️ Record", disabled=record_disabled): st.session_state.is_recording = True
    if c2.button("🔄 Clear Notes"): st.session_state.transcribed_text = ""
    if record_disabled: st.caption("*(Take a photo to enable recording)*")

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    save_disabled = not (st.session_state.image_path and st.session_state.patient_name)
    if st.button("💾 SAVE RECORD", use_container_width=True, disabled=save_disabled, type="primary"):
        path = save_record_permanently()
        st.success(f"Saved: {os.path.basename(path)}")
    
    # --- ENHANCEMENT: New Patient Button ---
    if st.button("✨ Start New Patient", use_container_width=True):
        reset_workflow()
        st.rerun()

# ================= RIGHT COLUMN =================
with col_right:
    camera_img = st.camera_input("Capture Photo", label_visibility="collapsed")
    if camera_img: st.session_state.image_path = save_temp_image(camera_img)
    if st.session_state.is_recording:
        transcribe_voice_notes()
        st.rerun()