import streamlit as st
from PIL import Image
from datetime import datetime
import os
import speech_recognition as sr
import shutil

# --- Page Configuration ---
st.set_page_config(
    page_title="clarident AI",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Session State ---
if 'patient_name' not in st.session_state: st.session_state.patient_name = ""
if 'tooth_number' not in st.session_state: st.session_state.tooth_number = ""
if 'image_path' not in st.session_state: st.session_state.image_path = None
if 'transcribed_text' not in st.session_state: st.session_state.transcribed_text = ""
if 'timestamp' not in st.session_state: st.session_state.timestamp = ""
if 'is_recording' not in st.session_state: st.session_state.is_recording = False

# --- CSS Styling ---
def load_css():
    st.markdown("""
        <style>
            /* --- 1. Global Background --- */
            .stApp {
                background-color: #0E4E5A; 
            }

            /* --- 2. Remove Top Bar & Adjust Spacing --- */
            /* Hides the Streamlit hamburger menu and red bar */
            header {visibility: hidden;} 
            
            /* Removes the huge default top padding, but leaves enough space (2rem) so it's not cut off */
            .block-container {
                padding-top: 2rem !important; 
                padding-bottom: 2rem;
                max-width: 95%;
            }

            /* --- 3. Make Labels WHITE and Visible --- */
            .stTextInput label, .stTextArea label {
                color: #FFFFFF !important;
                font-size: 1rem;
                font-weight: 600;
                margin-bottom: 5px;
            }
            
            /* --- 4. Style the Inputs --- */
            .stTextInput input, .stTextArea textarea {
                background-color: #F3F4F6; /* Light grey background */
                color: #000000; /* Black text */
                border-radius: 8px;
                border: 1px solid white;
            }
            
            /* --- 5. Section Headers (White Cards for Titles) --- */
            .section-header {
                background-color: white;
                padding: 12px 20px;
                border-radius: 10px;
                color: #0E4E5A;
                font-weight: 700;
                font-size: 1.1rem;
                margin-bottom: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                gap: 10px;
            }

            /* --- 6. Camera Styling --- */
            [data-testid="stCameraInput"] {
                border-radius: 15px;
                border: 4px solid white;
                box-shadow: 0 10px 15px rgba(0,0,0,0.3);
            }
            
            /* --- 7. Button Styling --- */
            div[data-testid="stButton"] > button {
                border-radius: 8px;
                font-weight: 600;
                border: none;
                transition: all 0.2s;
                height: 45px;
            }
        </style>
    """, unsafe_allow_html=True)

# --- Logic Functions ---
def save_temp_image(patient, tooth, camera_img):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.timestamp = timestamp
    image = Image.open(camera_img)
    filename = f"temp_{timestamp}.jpg"
    if not os.path.exists("temp_data"): os.makedirs("temp_data")
    full_path = os.path.join("temp_data", filename)
    image.save(full_path)
    return full_path

def save_record_permanently():
    if not st.session_state.patient_name or not st.session_state.image_path:
        return None
    
    clean_name = "".join(x for x in st.session_state.patient_name if x.isalnum() or x in " _-")
    folder_name = f"{clean_name}_{st.session_state.timestamp}"
    base_dir = "saved_records"
    save_dir = os.path.join(base_dir, folder_name)
    
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    img_filename = f"Tooth_{st.session_state.tooth_number}.jpg"
    new_img_path = os.path.join(save_dir, img_filename)
    shutil.copy(st.session_state.image_path, new_img_path)
    
    if st.session_state.transcribed_text:
        txt_path = os.path.join(save_dir, "Doctor_Notes.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Patient: {st.session_state.patient_name}\n")
            f.write(f"Tooth: {st.session_state.tooth_number}\n")
            f.write(f"Date: {st.session_state.timestamp}\n")
            f.write("-" * 20 + "\n")
            f.write(st.session_state.transcribed_text)
            
    return save_dir

def transcribe_voice_notes():
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            with st.spinner("Listening..."):
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
        text = recognizer.recognize_google(audio)
        if st.session_state.transcribed_text:
            st.session_state.transcribed_text += f" {text}"
        else:
            st.session_state.transcribed_text = text
    except Exception:
        st.toast("No speech detected", icon="⚠️")
    finally:
        st.session_state.is_recording = False

# --- Main App ---
load_css()

col_left, col_space, col_right = st.columns([0.35, 0.05, 0.60])

# ================= LEFT COLUMN =================
with col_left:
    # Header with Logo
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 25px;">
            <img src="https://cdn-icons-png.flaticon.com/512/3004/3004458.png" width="45">
            <h1 style='color: white; margin: 0; font-size: 2.2rem; font-family: sans-serif;'>ClariDent AI</h1>
        </div>
    """, unsafe_allow_html=True)

    # --- SECTION 1: Patient Info ---
    st.markdown('<div class="section-header">👤 Patient Information</div>', unsafe_allow_html=True)
    
    # Inputs (Labels are now White via CSS)
    st.session_state.patient_name = st.text_input("Full Name", st.session_state.patient_name, placeholder="e.g. Sarah Jones")
    st.session_state.tooth_number = st.text_input("Tooth Number", st.session_state.tooth_number, placeholder="e.g. 14")
    
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True) # Spacing

    # --- SECTION 2: Notes ---
    st.markdown('<div class="section-header">📝 Doctor\'s Notes</div>', unsafe_allow_html=True)
    
    st.session_state.transcribed_text = st.text_area(
        "Voice Notes", 
        st.session_state.transcribed_text, 
        height=120,
        placeholder="Click Record to dictate...",
        label_visibility="collapsed"
    )
    

    # Buttons
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🎙️ Record"):
            st.session_state.is_recording = True
    with c2:
        if st.button("🔄 Clear"):
            st.session_state.transcribed_text = ""
            st.rerun()

    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    
    # Save Button
    if st.button("💾 SAVE TO SYSTEM", use_container_width=True):
        if st.session_state.image_path and st.session_state.patient_name:
            path = save_record_permanently()
            st.success(f"Saved: {os.path.basename(path)}")
        else:
            st.error("Please take a photo and enter Patient Name.")

# ================= RIGHT COLUMN =================
with col_right:
    # Camera Widget
    camera_img = st.camera_input("Capture Photo", label_visibility="collapsed")
    
    if camera_img:
        st.session_state.image_path = save_temp_image(
            st.session_state.patient_name if st.session_state.patient_name else "Guest", 
            st.session_state.tooth_number if st.session_state.tooth_number else "00", 
            camera_img
        )

    # Transcription Logic
    if st.session_state.is_recording:
        transcribe_voice_notes()
        st.rerun()