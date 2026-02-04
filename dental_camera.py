import streamlit as st
from PIL import Image
from datetime import datetime
import os
import speech_recognition as sr
import sqlite3
import pandas as pd

# --- Page Configuration ---
st.set_page_config(
    page_title="clarident AI",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded" # Expanded so user sees history
)

# --- Database Setup (SQLite) ---
def init_db():
    conn = sqlite3.connect('dental_records.db')
    c = conn.cursor()
    # Create table if not exists
    c.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT,
            tooth_number TEXT,
            notes TEXT,
            image_path TEXT,
            timestamp TEXT,
            session_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB on load
init_db()

# --- Session State ---
if 'patient_name' not in st.session_state: st.session_state.patient_name = ""
if 'tooth_number' not in st.session_state: st.session_state.tooth_number = ""
if 'image_path' not in st.session_state: st.session_state.image_path = None
if 'transcribed_text' not in st.session_state: st.session_state.transcribed_text = ""
if 'is_recording' not in st.session_state: st.session_state.is_recording = False

# --- CSS Styling (YOUR ORIGINAL STYLES PRESERVED) ---
def load_css():
    st.markdown("""
        <style>
            /* --- 1. Global Background --- */
            .stApp {
                background-color: #0E4E5A; 
            }

            /* --- 2. Adjust Spacing (Modified to keep Sidebar accessible) --- */
            .block-container {
                padding-top: 2rem !important; 
                padding-bottom: 2rem;
                max-width: 95%;
            }

            /* --- 3. Make Labels WHITE and Visible --- */
            .stTextInput label, .stTextArea label, .stSelectbox label {
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
            
            /* --- 5. Section Headers --- */
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
            
            /* Sidebar Styling */
            [data-testid="stSidebar"] {
                background-color: #083D46;
            }
            [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] span {
                color: white;
            }
        </style>
    """, unsafe_allow_html=True)

# --- Logic Functions ---

def save_record_to_db(patient, tooth, notes, camera_img):
    if not patient or not camera_img:
        return False

    # 1. Create Timestamp
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    session_date = now.strftime("%Y-%m-%d")
    
    # 2. Save Image to Local Folder
    save_dir = "saved_images"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    # Filename: PatientName_Tooth_Time.jpg
    clean_name = "".join(x for x in patient if x.isalnum())
    filename = f"{clean_name}_T{tooth}_{now.strftime('%H%M%S')}.jpg"
    full_path = os.path.join(save_dir, filename)
    
    image = Image.open(camera_img)
    image.save(full_path)
    
    # 3. Save to SQLite
    conn = sqlite3.connect('dental_records.db')
    c = conn.cursor()
    c.execute("""
        INSERT INTO records (patient_name, tooth_number, notes, image_path, timestamp, session_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (patient, tooth, notes, full_path, timestamp, session_date))
    conn.commit()
    conn.close()
    return True

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

# --- SIDEBAR HISTORY ---
with st.sidebar:
    st.markdown("### 🗂️ Patient History")
    
    # Refresh button for sidebar
    if st.button("🔄 Refresh List"):
        st.rerun()

    conn = sqlite3.connect('dental_records.db')
    # Fetch last 15 records
    df = pd.read_sql_query("SELECT patient_name, tooth_number, timestamp FROM records ORDER BY id DESC LIMIT 15", conn)
    conn.close()
    
    if not df.empty:
        # Clean up column names for display
        df.columns = ['Patient', 'Tooth', 'Time']
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("No records found.")

col_left, col_space, col_right = st.columns([0.35, 0.05, 0.60])

# ================= LEFT COLUMN =================
with col_left:
    # Header with Logo
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 25px;">
            <img src="https://cdn-icons-png.flaticon.com/512/3004/3004458.png" width="45">
            <h1 style='color: white; margin: 0; font-size: 2.2rem; font-family: sans-serif;'>DentalVision AI</h1>
        </div>
    """, unsafe_allow_html=True)

    # --- SECTION 1: Patient Info ---
    st.markdown('<div class="section-header">👤 Patient Information</div>', unsafe_allow_html=True)
    
    # Patient Name
    st.session_state.patient_name = st.text_input("Full Name", st.session_state.patient_name, placeholder="e.g. Sarah Jones")
    
    # Tooth Number
    st.session_state.tooth_number = st.text_input("Tooth Number", st.session_state.tooth_number, placeholder="e.g. 14")
    
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True) 

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
        if st.button("🔄 Clear Note"):
            st.session_state.transcribed_text = ""
            st.rerun()

    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    
    # Save Button
    if st.button("💾 SAVE RECORD", use_container_width=True):
        # We need to access the camera image from the right column
        # Since st.camera_input provides the buffer immediately, we check if it exists in session logic below
        pass # The logic is handled below after camera renders

# ================= RIGHT COLUMN =================
with col_right:
    # Camera Widget
    camera_img = st.camera_input("Capture Photo", label_visibility="collapsed")
    
    # Save Logic Triggered by Button above
    # Streamlit runs top-to-bottom. We check if button was clicked previously or we use a form. 
    # To keep it simple with your UI, we process save here if both image and name exist.
    
    # NOTE: In Streamlit, buttons reset on rerun. 
    # To make the Save button on the left work with the Camera on the right, 
    # we usually check the button state.
    
    if camera_img:
        st.session_state.image_path = camera_img # Hold in session

    # Re-checking the button from the Left Column context is tricky in standard script flow.
    # A better pattern for Streamlit is placing the logic where the button is, 
    # but the camera input must exist first.
    
    # Let's fix the logic flow:
    # The user clicks SAVE. The app reruns. The camera_img might be None on rerun unless re-captured.
    # To fix this, we allow Saving ONLY if an image is in the buffer.
    
    if st.session_state.image_path is not None:
        st.image(st.session_state.image_path, caption="Captured Image", width=200)

    # Transcription Logic
    if st.session_state.is_recording:
        transcribe_voice_notes()
        st.rerun()

# --- ACTUAL SAVE EXECUTION ---
# We move the save button logic here to ensure it has access to everything
if camera_img and st.session_state.patient_name:
    # We display a "Confirm Save" button under the camera if a photo is taken
    if st.button("✅ CONFIRM SAVE FOR " + st.session_state.patient_name, type="primary", use_container_width=True):
        success = save_record_to_db(
            st.session_state.patient_name,
            st.session_state.tooth_number,
            st.session_state.transcribed_text,
            camera_img
        )
        if success:
            st.toast(f"Saved Tooth {st.session_state.tooth_number} for {st.session_state.patient_name}!", icon="🦷")
            
            # --- MULTIPLE TEETH LOGIC ---
            # We clear the tooth number and notes, but KEEP the Patient Name
            # This allows the doctor to immediately do the next tooth.
            st.session_state.tooth_number = ""
            st.session_state.transcribed_text = ""
            st.session_state.image_path = None
            
            st.rerun()