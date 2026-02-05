import streamlit as st
import assemblyai as aai
from PIL import Image
from datetime import datetime
import os
import shutil
import hashlib
import tempfile

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
if 'audio_key' not in st.session_state: st.session_state.audio_key = 0

# --- CSS Styling ---
st.markdown("""
    <style>
        .stApp { background-color: #0E4E5A; }
        header {visibility: hidden;} 
        .block-container { padding-top: 1.5rem !important; max-width: 98%; }
        .stTextInput label, .stTextArea label { color: #FFFFFF !important; font-weight: 600; font-size: 0.9rem; }
        .section-header { 
            background-color: white; padding: 8px 15px; border-radius: 8px; 
            color: #0E4E5A; font-weight: 700; font-size: 0.95rem; 
            margin-bottom: 12px; display: flex; align-items: center; gap: 10px; 
        }
        .stTextArea textarea { font-size: 1rem; border-radius: 10px; background-color: #f9f9f9; }
        [data-testid="stCameraInput"] { border: 2px solid white; border-radius: 12px; margin-bottom: 10px; }
        .preview-label { color: white; font-weight: bold; font-size: 0.85rem; margin-top: 15px; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- Logic: AssemblyAI ---
def transcribe_dental_audio(audio_data):
    try:
        aai.settings.api_key = st.secrets["ASSEMBLY_AI_KEY"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_data.getvalue())
            tmp_path = tmp_file.name
        
        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(
            speech_model=aai.SpeechModel.best,
            punctuate=True,
            format_text=True
        )
        transcript = transcriber.transcribe(tmp_path, config=config)
        
        # Ensure we return a string, never None
        if transcript.status == aai.TranscriptStatus.error:
            return ""
        return transcript.text if transcript.text else ""
    except Exception as e:
        return ""
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path): 
            os.remove(tmp_path)

# --- Logic: Saving ---
def save_record_permanently():
    # Double check validation here for safety
    if not st.session_state.patient_name or not st.session_state.image_path:
        return False
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_name = "".join(x for x in st.session_state.patient_name if x.isalnum() or x in " _-")
    save_dir = os.path.join("saved_records", f"{clean_name}_{timestamp}")
    os.makedirs(save_dir, exist_ok=True)
    shutil.copy(st.session_state.image_path, os.path.join(save_dir, "tooth_image.jpg"))
    with open(os.path.join(save_dir, "Notes.txt"), "w") as f:
        f.write(f"Patient: {st.session_state.patient_name}\nTooth: {st.session_state.tooth_number}\nNotes: {st.session_state.transcribed_text}")
    return True

# --- Isolated UI Fragments ---

@st.fragment
def audio_section():
    st.markdown('<div class="section-header">🎙️ Clinical Recorder</div>', unsafe_allow_html=True)
    audio_data = st.audio_input("Record", key=f"audio_{st.session_state.audio_key}", label_visibility="collapsed")
    
    if audio_data:
        h = hashlib.md5(audio_data.getvalue()).hexdigest()
        if h not in st.session_state.processed_audio_hashes:
            with st.spinner("Transcribing..."):
                txt = transcribe_dental_audio(audio_data)
                
                # FIX: Only append if txt is a valid, non-empty string
                if txt and isinstance(txt, str):
                    if st.session_state.transcribed_text:
                        st.session_state.transcribed_text += f" {txt}"
                    else:
                        st.session_state.transcribed_text = txt
                
                st.session_state.processed_audio_hashes.add(h)
                st.rerun()
    
    # Text area for manual edits
    st.session_state.transcribed_text = st.text_area(
        "Observations", 
        value=st.session_state.transcribed_text, 
        height=180
    )

@st.fragment
def camera_section():
    st.markdown('<div class="section-header">📸 Intraoral Photo</div>', unsafe_allow_html=True)
    
    # Static Camera Input (no key reset = no flicker)
    cam_img = st.camera_input("Capture", label_visibility="collapsed")
    
    if cam_img:
        # Save to temp location for preview and final saving
        if not os.path.exists("temp_data"): os.makedirs("temp_data")
        temp_path = os.path.join("temp_data", "latest_capture.jpg")
        Image.open(cam_img).save(temp_path)
        st.session_state.image_path = temp_path
        
        # Display Preview
        st.markdown('<div class="preview-label">LATEST CAPTURE:</div>', unsafe_allow_html=True)
        st.image(st.session_state.image_path, width=400)
    else:
        # If user clicks the built-in "Clear" button, cam_img becomes None
        st.session_state.image_path = None
        st.info("Live feed active. Capture a photo to preview.")

# --- Main Page Layout ---
col_left, col_right = st.columns([0.45, 0.55], gap="medium")

with col_left:
    st.markdown('<h2 style="color:white; margin-top:0; font-size:1.8rem;">🦷 ClariDent AI</h2>', unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown('<div class="section-header">👤 Patient Details</div>', unsafe_allow_html=True)
        i1, i2 = st.columns(2)
        with i1: st.session_state.patient_name = st.text_input("Full Name", value=st.session_state.patient_name)
        with i2: st.session_state.tooth_number = st.text_input("Tooth #", value=st.session_state.tooth_number)

    audio_section()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Clear All Notes", use_container_width=True):
            st.session_state.transcribed_text = ""
            st.session_state.processed_audio_hashes = set()
            st.session_state.audio_key += 1
            st.rerun()
    with c2:
        if st.button("💾 SAVE RECORD", type="primary", use_container_width=True):
            # 1. Identify what is missing
            missing_fields = []
            if not st.session_state.patient_name:
                missing_fields.append("Patient Name")
            if not st.session_state.image_path:
                missing_fields.append("Intraoral Photo")
            
            # 2. Logic to handle missing fields or successful save
            if missing_fields:
                st.error(f"Missing: {', '.join(missing_fields)}")
            elif save_record_permanently():
                st.toast("Record Saved Successfully!", icon="✅")

with col_right:
    camera_section()