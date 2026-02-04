import streamlit as st
from PIL import Image
from datetime import datetime
import os
import speech_recognition as sr
import shutil
import io
from pydub import AudioSegment

# --- Page Configuration ---
st.set_page_config(
    page_title="clarident AI",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Initialize Session State ---
if 'patient_name' not in st.session_state: st.session_state.patient_name = ""
if 'tooth_number' not in st.session_state: st.session_state.tooth_number = ""
if 'image_path' not in st.session_state: st.session_state.image_path = None
if 'transcribed_text' not in st.session_state: st.session_state.transcribed_text = ""
if 'timestamp' not in st.session_state: st.session_state.timestamp = ""
if 'last_processed_audio' not in st.session_state: st.session_state.last_processed_audio = None

# --- CSS Styling ---
def load_css():
    st.markdown("""
        <style>
            .stApp { background-color: #0E4E5A; }
            header {visibility: hidden;} 
            .block-container { padding-top: 2rem !important; padding-bottom: 2rem; max-width: 95%; }
            .stTextInput label, .stTextArea label { color: #FFFFFF !important; font-size: 1rem; font-weight: 600; margin-bottom: 5px; }
            .stTextInput input, .stTextArea textarea { background-color: #F3F4F6; color: #000000; border-radius: 8px; border: 1px solid white; }
            .section-header { background-color: white; padding: 12px 20px; border-radius: 10px; color: #0E4E5A; font-weight: 700; font-size: 1.1rem; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; align-items: center; gap: 10px; }
            [data-testid="stCameraInput"] { border-radius: 15px; border: 4px solid white; }
            div[data-testid="stButton"] > button { border-radius: 8px; font-weight: 600; height: 45px; }
            .stAudioInput { background-color: white; border-radius: 10px; padding: 5px; }
        </style>
    """, unsafe_allow_html=True)

# --- Logic Functions ---
def save_temp_image(camera_img):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.timestamp = timestamp
    image = Image.open(camera_img)
    if not os.path.exists("temp_data"): os.makedirs("temp_data")
    full_path = os.path.join("temp_data", f"temp_{timestamp}.jpg")
    image.save(full_path)
    return full_path

def save_record_permanently():
    if not st.session_state.patient_name or not st.session_state.image_path:
        return None
    
    clean_name = "".join(x for x in st.session_state.patient_name if x.isalnum() or x in " _-")
    folder_name = f"{clean_name}_{st.session_state.timestamp}"
    save_dir = os.path.join("saved_records", folder_name)
    
    if not os.path.exists(save_dir): os.makedirs(save_dir)
        
    img_filename = f"Tooth_{st.session_state.tooth_number}.jpg"
    shutil.copy(st.session_state.image_path, os.path.join(save_dir, img_filename))
    
    if st.session_state.transcribed_text:
        with open(os.path.join(save_dir, "Doctor_Notes.txt"), "w", encoding="utf-8") as f:
            f.write(f"Patient: {st.session_state.patient_name}\nTooth: {st.session_state.tooth_number}\nNotes: {st.session_state.transcribed_text}")
    return save_dir

# --- Main App ---
load_css()

col_left, col_space, col_right = st.columns([0.40, 0.05, 0.55])

# ================= LEFT COLUMN =================
with col_left:
    st.markdown("""<div style="display:flex; align-items:center; gap:15px; margin-bottom:20px;"><img src="https://cdn-icons-png.flaticon.com/512/3004/3004458.png" width="45"><h1 style='color:white; margin:0; font-size:2rem;'>ClariDent AI</h1></div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-header">👤 Patient Info</div>', unsafe_allow_html=True)
    st.session_state.patient_name = st.text_input("Full Name", st.session_state.patient_name)
    st.session_state.tooth_number = st.text_input("Tooth Number", st.session_state.tooth_number)
    
    st.markdown('<div class="section-header">🎙️ Voice Notes</div>', unsafe_allow_html=True)
    
    # 1. Capture Audio
    audio_file = st.audio_input("Record Notes", label_visibility="collapsed")

    # 2. Transcription Logic (Appends only when a NEW file is recorded)
    if audio_file is not None and audio_file != st.session_state.last_processed_audio:
        with st.spinner("Transcribing..."):
            try:
                audio = AudioSegment.from_file(audio_file)
                wav_io = io.BytesIO()
                audio.export(wav_io, format="wav")
                wav_io.seek(0)
                
                r = sr.Recognizer()
                with sr.AudioFile(wav_io) as source:
                    recorded_audio = r.record(source)
                    text = r.recognize_google(recorded_audio)
                    
                    # APPEND new text to existing text
                    if st.session_state.transcribed_text:
                        st.session_state.transcribed_text += f" {text}"
                    else:
                        st.session_state.transcribed_text = text
                
                # Mark this specific audio file as processed
                st.session_state.last_processed_audio = audio_file
                st.toast("Notes Appended!", icon="✅")
            except Exception as e:
                st.error("Could not transcribe. Check internet/background noise.")

    st.session_state.transcribed_text = st.text_area("Live Notes", st.session_state.transcribed_text, height=150)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Clear All Notes", use_container_width=True):
            st.session_state.transcribed_text = ""
            st.session_state.last_processed_audio = None # Reset so next recording works
            st.rerun()
    with c2:
        if st.button("💾 SAVE RECORD", use_container_width=True):
            if st.session_state.image_path and st.session_state.patient_name:
                path = save_record_permanently()
                st.success(f"Saved to: {os.path.basename(path)}")
            else:
                st.error("Need Photo & Name")

# ================= RIGHT COLUMN =================
with col_right:
    st.markdown('<div class="section-header">📸 Dental Photo</div>', unsafe_allow_html=True)
    
    # If no image is saved yet, show camera
    if st.session_state.image_path is None:
        camera_img = st.camera_input("Take Photo", label_visibility="collapsed")
        if camera_img:
            st.session_state.image_path = save_temp_image(camera_img)
            st.rerun()
    else:
        # If image exists, show the preview and a Retake button
        st.image(st.session_state.image_path, use_container_width=True)
        if st.button("🗑️ Retake Photo", use_container_width=True):
            st.session_state.image_path = None
            st.rerun()