import streamlit as st
from PIL import Image
from datetime import datetime
import os
import speech_recognition as sr
import shutil
import io
import hashlib
from pydub import AudioSegment

# --- Page Configuration ---
st.set_page_config(
    page_title="ClariDent AI",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Initialize Session State ---
if 'patient_name' not in st.session_state: st.session_state.patient_name = ""
if 'tooth_number' not in st.session_state: st.session_state.tooth_number = ""
if 'image_path' not in st.session_state: st.session_state.image_path = None
if 'transcribed_text' not in st.session_state: st.session_state.transcribed_text = ""
if 'processed_audio_hashes' not in st.session_state: st.session_state.processed_audio_hashes = set()

# --- CSS Styling ---
def load_css():
    st.markdown("""
        <style>
            .stApp { background-color: #0E4E5A; }
            header {visibility: hidden;} 
            .block-container { padding-top: 2rem !important; padding-bottom: 2rem; max-width: 95%; }
            .stTextInput label, .stTextArea label, .stSelectbox label { color: #FFFFFF !important; font-size: 1rem; font-weight: 600; }
            .section-header { background-color: white; padding: 12px 20px; border-radius: 10px; color: #0E4E5A; font-weight: 700; font-size: 1.1rem; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
            .stTextArea textarea { font-size: 1.1rem; }
            /* Stabilize the camera area */
            .camera-container { min-height: 400px; border: 2px dashed rgba(255,255,255,0.2); border-radius: 15px; }
        </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def get_audio_hash(audio_bytes):
    return hashlib.md5(audio_bytes).hexdigest()

def save_temp_image(camera_img):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image = Image.open(camera_img)
    if not os.path.exists("temp_data"): os.makedirs("temp_data")
    full_path = os.path.join("temp_data", f"temp_{timestamp}.jpg")
    image.save(full_path)
    return full_path, timestamp

def save_record_permanently():
    if not st.session_state.patient_name or not st.session_state.image_path:
        return None
    
    clean_name = "".join(x for x in st.session_state.patient_name if x.isalnum() or x in " _-")
    folder_name = f"{clean_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    save_dir = os.path.join("saved_records", folder_name)
    os.makedirs(save_dir, exist_ok=True)
        
    img_filename = f"Tooth_{st.session_state.tooth_number}.jpg"
    shutil.copy(st.session_state.image_path, os.path.join(save_dir, img_filename))
    
    with open(os.path.join(save_dir, "Doctor_Notes.txt"), "w", encoding="utf-8") as f:
        f.write(f"Patient: {st.session_state.patient_name}\nTooth: {st.session_state.tooth_number}\nNotes: {st.session_state.transcribed_text}")
    return save_dir

# --- Main App ---
load_css()

col_left, col_space, col_right = st.columns([0.45, 0.05, 0.50])

# ================= LEFT COLUMN: INFO & VOICE =================
with col_left:
    st.markdown("""<div style="display:flex; align-items:center; gap:15px; margin-bottom:20px;"><img src="https://cdn-icons-png.flaticon.com/512/3004/3004458.png" width="45"><h1 style='color:white; margin:0; font-size:2rem;'>ClariDent AI</h1></div>""", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="section-header">👤 Patient Info</div>', unsafe_allow_html=True)
        st.session_state.patient_name = st.text_input("Full Name", value=st.session_state.patient_name)
        st.session_state.tooth_number = st.text_input("Tooth Number", value=st.session_state.tooth_number)
    
    st.markdown('<div class="section-header">🎙️ Voice Clinical Notes</div>', unsafe_allow_html=True)
    
    # Audio Input Logic
    audio_data = st.audio_input("Record observations")

    if audio_data:
        # Get hash of current audio to see if it's new
        audio_bytes = audio_data.getvalue()
        current_hash = get_audio_hash(audio_bytes)
        
        if current_hash not in st.session_state.processed_audio_hashes:
            with st.spinner("Transcribing segment..."):
                try:
                    # Convert to WAV for speech_recognition
                    audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
                    wav_io = io.BytesIO()
                    audio_segment.export(wav_io, format="wav")
                    wav_io.seek(0)
                    
                    r = sr.Recognizer()
                    with sr.AudioFile(wav_io) as source:
                        recorded_audio = r.record(source)
                        text = r.recognize_google(recorded_audio)
                        
                        # Append with punctuation logic
                        if st.session_state.transcribed_text:
                            st.session_state.transcribed_text += f". {text}"
                        else:
                            st.session_state.transcribed_text = text
                    
                    # Store hash so we don't process this exact clip again
                    st.session_state.processed_audio_hashes.add(current_hash)
                    st.toast("Notes Appended!", icon="✅")
                except Exception as e:
                    st.error("Speech not recognized. Please try speaking clearer.")

    # Live Notes Area (Editable)
    st.session_state.transcribed_text = st.text_area(
        "Clinical Record", 
        value=st.session_state.transcribed_text, 
        height=250,
        help="You can edit the transcribed text manually here."
    )

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("🔄 Reset All Notes", use_container_width=True):
            st.session_state.transcribed_text = ""
            st.session_state.processed_audio_hashes = set()
            st.rerun()
    with btn_col2:
        if st.button("💾 SAVE RECORD", type="primary", use_container_width=True):
            if st.session_state.image_path and st.session_state.patient_name:
                path = save_record_permanently()
                st.success(f"Record Saved Successfully!")
                st.balloons()
            else:
                st.error("Missing Patient Name or Photo")

# ================= RIGHT COLUMN: STABLE CAMERA =================
with col_right:
    st.markdown('<div class="section-header">📸 Intraoral Photo</div>', unsafe_allow_html=True)
    
    camera_placeholder = st.empty()
    
    # Logic to prevent the "vanishing" effect
    if st.session_state.image_path is None:
        with camera_placeholder.container():
            camera_img = st.camera_input("Capture Tooth Image")
            if camera_img:
                img_path, ts = save_temp_image(camera_img)
                st.session_state.image_path = img_path
                st.rerun()
    else:
        with camera_placeholder.container():
            st.image(st.session_state.image_path, use_container_width=True, caption="Captured Image")
            if st.button("🗑️ Retake Photo", use_container_width=True):
                # Clean up old temp file if desired
                st.session_state.image_path = None
                st.rerun()