import streamlit as st
from PIL import Image
from datetime import datetime
import os
import speech_recognition as sr
import shutil
import io # Added for audio handling
from pydub import AudioSegment # Added for cloud audio processing

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

# --- CSS Styling --- (Kept your original style)
def load_css():
    st.markdown("""
        <style>
            .stApp { background-color: #0E4E5A; }
            header {visibility: hidden;} 
            .block-container { padding-top: 2rem !important; padding-bottom: 2rem; max-width: 95%; }
            .stTextInput label, .stTextArea label { color: #FFFFFF !important; font-size: 1rem; font-weight: 600; margin-bottom: 5px; }
            .stTextInput input, .stTextArea textarea { background-color: #F3F4F6; color: #000000; border-radius: 8px; border: 1px solid white; }
            .section-header { background-color: white; padding: 12px 20px; border-radius: 10px; color: #0E4E5A; font-weight: 700; font-size: 1.1rem; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; align-items: center; gap: 10px; }
            [data-testid="stCameraInput"] { border-radius: 15px; border: 4px solid white; box-shadow: 0 10px 15px rgba(0,0,0,0.3); }
            div[data-testid="stButton"] > button { border-radius: 8px; font-weight: 600; border: none; transition: all 0.2s; height: 45px; }
            /* Styling the audio input to match */
            [data-testid="stAudioInput"] { background-color: white; border-radius: 10px; padding: 5px; }
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
    # IMPORTANT: On Cloud, files saved like this will disappear when the app restarts.
    # Later, we will replace this with Google Drive saving.
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

# --- Main App ---
load_css()

col_left, col_space, col_right = st.columns([0.35, 0.05, 0.60])

# ================= LEFT COLUMN =================
with col_left:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 25px;">
            <img src="https://cdn-icons-png.flaticon.com/512/3004/3004458.png" width="45">
            <h1 style='color: white; margin: 0; font-size: 2.2rem; font-family: sans-serif;'>ClariDent AI</h1>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">👤 Patient Information</div>', unsafe_allow_html=True)
    st.session_state.patient_name = st.text_input("Full Name", st.session_state.patient_name, placeholder="e.g. Sarah Jones")
    st.session_state.tooth_number = st.text_input("Tooth Number", st.session_state.tooth_number, placeholder="e.g. 14")
    
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)

    st.markdown('<div class="section-header">📝 Doctor\'s Notes</div>', unsafe_allow_html=True)
    
    # --- CHANGE 1: Use st.audio_input instead of Record Button ---
    # This works in browsers on the cloud!
    audio_file = st.audio_input("Record Voice Note", label_visibility="collapsed")

    if audio_file:
        with st.spinner("Transcribing..."):
            try:
                # Convert the audio blob to a format SpeechRecognition can read
                audio = AudioSegment.from_file(audio_file)
                wav_io = io.BytesIO()
                audio.export(wav_io, format="wav")
                wav_io.seek(0)
                
                r = sr.Recognizer()
                with sr.AudioFile(wav_io) as source:
                    recorded_audio = r.record(source)
                    text = r.recognize_google(recorded_audio)
                    # Append new text to the text area
                    st.session_state.transcribed_text += f" {text}"
            except Exception as e:
                st.error("Audio error. Please try again.")

    st.session_state.transcribed_text = st.text_area(
        "Voice Notes Preview", 
        st.session_state.transcribed_text, 
        height=150,
        label_visibility="collapsed"
    )

    if st.button("🔄 Clear Notes", use_container_width=True):
        st.session_state.transcribed_text = ""
        st.rerun()

    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
    
    if st.button("💾 SAVE TO SYSTEM", use_container_width=True):
        if st.session_state.image_path and st.session_state.patient_name:
            path = save_record_permanently()
            st.success(f"Saved: {os.path.basename(path)}")
        else:
            st.error("Please take a photo and enter Patient Name.")

# ================= RIGHT COLUMN =================
with col_right:
    camera_img = st.camera_input("Capture Photo", label_visibility="collapsed")
    
    if camera_img:
        st.session_state.image_path = save_temp_image(
            st.session_state.patient_name if st.session_state.patient_name else "Guest", 
            st.session_state.tooth_number if st.session_state.tooth_number else "00", 
            camera_img
        )