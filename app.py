import streamlit as st
from PIL import Image
from datetime import datetime
import os
import speech_recognition as sr
import io
from audiorecorder import audiorecorder

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

# --- CSS Styling (Your Original Design) ---
def load_css():
    st.markdown("""
        <style>
            .stApp { background-color: #0E4E5A; }
            header {visibility: hidden;} 
            .block-container { padding-top: 2rem !important; padding-bottom: 2rem; max-width: 95%; }
            .stTextInput label, .stTextArea label { color: #FFFFFF !important; font-size: 1rem; font-weight: 600; margin-bottom: 5px; }
            .stTextInput input, .stTextArea textarea { background-color: #F3F4F6; color: #000000; border-radius: 8px; border: 1px solid white; }
            .section-header { background-color: white; padding: 12px 20px; border-radius: 10px; color: #0E4E5A; font-weight: 700; font-size: 1.1rem; margin-bottom: 10px; display: flex; align-items: center; gap: 10px; }
            [data-testid="stCameraInput"] { border-radius: 15px; border: 4px solid white; }
            div[data-testid="stButton"] > button { border-radius: 8px; font-weight: 600; border: none; transition: all 0.2s; height: 45px; }
        </style>
    """, unsafe_allow_html=True)

# --- Cloud-Compatible Voice Logic ---
def process_audio(audio_bytes):
    r = sr.Recognizer()
    audio_file = io.BytesIO(audio_bytes)
    with sr.AudioFile(audio_file) as source:
        audio = r.record(source)
    try:
        text = r.recognize_google(audio)
        st.session_state.transcribed_text += f" {text}"
        st.success("Transcribed!")
    except:
        st.error("Could not understand audio.")

# --- Main App ---
load_css()
col_left, col_space, col_right = st.columns([0.35, 0.05, 0.60])

with col_left:
    st.markdown("""<div style="display: flex; align-items: center; gap: 15px; margin-bottom: 25px;"><img src="https://cdn-icons-png.flaticon.com/512/3004/3004458.png" width="45"><h1 style='color: white; margin: 0; font-size: 2.2rem; font-family: sans-serif;'>ClariDent AI</h1></div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-header">👤 Patient Information</div>', unsafe_allow_html=True)
    st.session_state.patient_name = st.text_input("Full Name", st.session_state.patient_name)
    st.session_state.tooth_number = st.text_input("Tooth Number", st.session_state.tooth_number)
    
    st.markdown('<div class="section-header">📝 Doctor\'s Notes</div>', unsafe_allow_html=True)
    
    # NEW: Browser-based recorder for the cloud
    audio = audiorecorder("🎙️ Click to Record", "🛑 Stop Recording")
    
    if len(audio) > 0:
        # Process the recording
        process_audio(audio.tobytes())

    st.session_state.transcribed_text = st.text_area("Notes", st.session_state.transcribed_text, height=120)

    if st.button("🔄 Clear Notes"):
        st.session_state.transcribed_text = ""
        st.rerun()

    if st.button("💾 SAVE RECORD (TEST)", use_container_width=True):
        st.info("Note: Cloud saving is temporary. For permanent storage, connect Google Drive next.")

with col_right:
    camera_img = st.camera_input("Capture Photo", label_visibility="collapsed")
    if camera_img:
        st.image(camera_img, caption="Preview")