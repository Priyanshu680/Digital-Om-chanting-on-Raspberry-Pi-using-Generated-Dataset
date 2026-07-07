import platform
import streamlit as st
import cv2
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import uuid

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))


def is_raspberry_pi():
    if platform.system() != "Linux":
        return False
    try:
        with open("/proc/device-tree/model", "r") as f:
            return "Raspberry Pi" in f.read()
    except Exception:
        return platform.machine().startswith(("arm", "aarch"))


def create_video_capture(index=0):
    if is_raspberry_pi():
        return cv2.VideoCapture(index, cv2.CAP_V4L2)
    return cv2.VideoCapture(index)

from modules.face_detector import FaceDetector
from modules.audio_manager import AudioManager
from modules.session_tracker import SessionTracker
from modules.face_database import FaceDatabase
import time

st.set_page_config(
    page_title="Digital \"Om\" Chanting triggered by facial recognition",
    page_icon="🧘",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    :root {
        --primary: #0d7377;
        --dark-bg: #0a0e27;
        --card-bg: #1a1f3a;
        --text-primary: #e8f1f5;
        --accent: #00d4d4;
        --success: #00ff41;
        --danger: #ff006e;
    }
    
    body {
        background-color: var(--dark-bg);
        color: var(--text-primary);
    }
    
    .metric-card {
        background-color: var(--card-bg);
        border: 1px solid var(--accent);
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    
    .status-active {
        color: var(--danger);
        font-weight: bold;
    }
    
    .status-ready {
        color: var(--success);
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

if 'session_active' not in st.session_state:
    st.session_state.session_active = False
if 'detector' not in st.session_state:
    st.session_state.detector = FaceDetector()
    # expose deepface toggle on detector instance
    st.session_state.detector.use_deepface = False
if 'audio_manager' not in st.session_state:
    st.session_state.audio_manager = AudioManager()
if 'tracker' not in st.session_state:
    st.session_state.tracker = SessionTracker()
if 'db' not in st.session_state:
    st.session_state.db = FaceDatabase()
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'audio_should_be_playing' not in st.session_state:
    st.session_state.audio_should_be_playing = False
if 'last_eyes_state' not in st.session_state:
    st.session_state.last_eyes_state = None
if 'last_expression' not in st.session_state:
    st.session_state.last_expression = None
if 'last_neutrality' not in st.session_state:
    st.session_state.last_neutrality = None
if 'detector_failures' not in st.session_state:
    st.session_state.detector_failures = 0

with st.sidebar:
    st.markdown("### 🧘   Digital \"Om\" Chanting triggered by facial recognition")
    st.markdown("---")
    
    # Session controls
    st.markdown("#### Session Control")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ Start", use_container_width=True, key="start_btn"):
            st.session_state.session_active = True
            st.session_state.tracker.start_session()
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.last_eyes_state = None
            st.success("Session started!")
    with col2:
        if st.button("⏹ Stop", use_container_width=True, key="stop_btn"):
            st.session_state.session_active = False
            st.session_state.audio_manager.stop_om()
            st.session_state.tracker.end_session()
            st.info("Session saved!")
    
    st.markdown("---")
    
    # Audio settings
    st.markdown("#### Audio Settings")
    om_volume = st.slider("Volume", 0, 100, 50, key="volume_slider")
    st.session_state.audio_manager.set_volume(om_volume / 100)
    
    st.markdown("##### Audio Files Status")
    om_file = st.session_state.audio_manager.om_path
    eyes_closed_file = st.session_state.audio_manager.eyes_closed_path
    eyes_open_file = st.session_state.audio_manager.eyes_open_path
    
    if om_file and om_file.exists():
        st.success(f"✓ Om: {om_file.name}")
    else:
        st.warning("⚠ Om audio missing")
    
    if eyes_closed_file and eyes_closed_file.exists():
        st.success(f"✓ Eyes Closed Alert: {eyes_closed_file.name}")
    else:
        st.warning("⚠ Eyes Closed Alert (auto-created)")
    
    if eyes_open_file and eyes_open_file.exists():
        st.success(f"✓ Eyes Open Alert: {eyes_open_file.name}")
    else:
        st.warning("⚠ Eyes Open Alert (auto-created)")
    
    st.info("Place .mp3 or .wav files in assets/audio/ folder to override defaults")

    # Detection settings
    st.markdown("#### Detection Settings")
    eye_closure_threshold = st.slider("Eye Closure Threshold", 0.05, 0.3, 0.15, step=0.01, key="eye_threshold")
    calm_threshold = st.slider("Calm Threshold", 0.3, 1.0, 0.65, step=0.05, key="calm_threshold")
    use_deepface = st.checkbox("Use DeepFace for emotion detection (slower, more accurate)", value=False, key="use_deepface")
    if use_deepface and not st.session_state.detector.deepface_available:
        st.warning("DeepFace is not installed in this environment. Using heuristic emotion detection instead.")
        st.session_state.detector.use_deepface = False
    else:
        st.session_state.detector.use_deepface = use_deepface

    # Neutrality / sensitivity controls
    st.markdown("---")
    st.markdown("**Neutrality / Sensitivity Settings**")
    strict_neutral = st.checkbox("Require strict neutral to play Om (stop on any deviation)", value=False, key="strict_neutral")
    neutral_threshold = st.slider("Neutrality Threshold", 0.0, 1.0, 0.6, step=0.05, key="neutral_threshold")
    expression_delta = st.slider("Expression change delta (stop if neutral drops by >)", 0.0, 0.5, 0.1, step=0.05, key="expression_delta")

    st.markdown("---")

    # Database stats
    st.markdown("#### Database Info")
    stats = st.session_state.db.get_expression_stats()
    total_saved = sum(stats.get('expression_counts', {}).values())
    st.write(f"Sessions Tracked: {total_saved}")

st.title("🧘   Digital \"Om\" Chanting triggered by facial recognition")

if st.session_state.session_active:
    st.markdown("### <span class='status-active'>🔴 Session Active</span>", unsafe_allow_html=True)
    st.markdown("**📢 Audio Features:**")
    st.markdown("- Alert plays when eyes close")
    st.markdown("- Alert plays when eyes open")
    st.markdown("- Om meditation sound plays only when eyes are closed and calm")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### Live Camera Feed")
        video_placeholder = st.empty()
        metrics_placeholder = st.empty()
        
        cap = create_video_capture(0)
        frame_count = 0
        max_frames = 2000
        
        while st.session_state.session_active and frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                st.error("Cannot access camera. Please check permissions.")
                break
            
            frame_count += 1
            # Keep `frame` as BGR for OpenCV/MediaPipe processing. Convert to
            # RGB only when displaying in Streamlit (which expects RGB).
            results = st.session_state.detector.detect(frame)
            eye_data = st.session_state.detector.detect_eye_closure(frame)
            
            face_detected = results is not None
            # Ensure face_data exists to avoid attribute errors later
            face_data = {}
            neutrality = 0.0
            dominant_emotion = "neutral"
            eyes_closed = False
            
            if face_detected:
                # Use BGR frame for extraction/drawing
                raw_face_data = st.session_state.detector.extract_facial_features(
                    frame, results, eye_data, eye_closure_threshold
                )
                # Guard: ensure face_data is a dict even if detector failed
                detector_error = not isinstance(raw_face_data, dict)
                if detector_error:
                    st.session_state.detector_failures += 1
                    face_data = {}
                else:
                    face_data = raw_face_data
                neutrality = face_data.get('neutrality', 0.0)
                # use dominant_emotion if available
                dominant_emotion = face_data.get('dominant_emotion', face_data.get('expression', st.session_state.get('last_expression', 'neutral')))
                eyes_closed = face_data.get('eyes_closed', False)

                # Draw landmarks on BGR frame
                frame = st.session_state.detector.draw_landmarks(frame, results)
            
            if face_detected and st.session_state.last_eyes_state is not None:
                if eyes_closed and not st.session_state.last_eyes_state:
                    st.session_state.audio_manager.play_eyes_closed_alert()
                    print(" Eyes closed - playing alert")
                elif not eyes_closed and st.session_state.last_eyes_state:
                    st.session_state.audio_manager.play_eyes_open_alert()
                    print(" Eyes open - playing alert")
            
            if face_detected:
                # If expression changed since last frame, stop Om audio
                prev_expr = st.session_state.get('last_expression')
                prev_neu = st.session_state.get('last_neutrality')

                # Stop if discrete expression changed (any change)
                stop_due_expr = False
                if prev_expr is not None and prev_expr != dominant_emotion:
                    stop_due_expr = True

                # Stop if neutrality drops below threshold when strict mode enabled
                stop_due_neutrality = False
                try:
                    current_neu = float(neutrality)
                except Exception:
                    current_neu = 0.0

                if strict_neutral and current_neu < neutral_threshold:
                    stop_due_neutrality = True

                # Stop if neutrality drops sharply compared to previous frame
                stop_due_delta = False
                if prev_neu is not None:
                    try:
                        if (prev_neu - current_neu) > expression_delta:
                            stop_due_delta = True
                    except Exception:
                        stop_due_delta = False

                if (stop_due_expr or stop_due_neutrality or stop_due_delta) and st.session_state.audio_should_be_playing and not eyes_closed:
                    st.session_state.audio_manager.stop_om()
                    st.session_state.audio_should_be_playing = False
                    print(f" Stopping audio due to expression/neutrality change while eyes open: prev_expr={prev_expr} cur_expr={dominant_emotion} prev_neu={prev_neu} cur_neu={current_neu}")

                st.session_state.last_eyes_state = eyes_closed
                st.session_state.last_expression = dominant_emotion
                st.session_state.last_neutrality = current_neu
            
            # Play Om only when eyes are closed
            should_play_om = eyes_closed
            
            if should_play_om and not st.session_state.audio_should_be_playing:
                if not st.session_state.audio_manager.is_playing:
                    st.session_state.audio_manager.play_om()
                st.session_state.audio_should_be_playing = True
            elif not should_play_om and st.session_state.audio_should_be_playing:
                st.session_state.audio_manager.stop_om()
                st.session_state.audio_should_be_playing = False
            
            if face_detected:
                eyes_text = "Eyes Closed" if eyes_closed else "Eyes Open"
                eye_color = (255, 0, 0) if eyes_closed else (0, 255, 100)
                cv2.putText(frame, eyes_text, 
                           (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.3, eye_color, 3)
                cv2.putText(frame, f"Neutrality: {neutrality:.2f}", 
                           (30, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
                cv2.putText(frame, f"Expression: {dominant_emotion.upper()}", 
                           (30, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)

                # Debug overlay if available
                # Debug overlay if available
                if 'smoothed_mouth_ratio' in face_data:
                    cv2.putText(frame, f"mouth={face_data.get('smoothed_mouth_ratio',0):.2f}", (30, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200,200,0), 2)
                if 'smoothed_ear' in face_data:
                    cv2.putText(frame, f"ear={face_data.get('smoothed_ear',0):.2f}", (30, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200,200,0), 2)

                # Show top emotions
                emotions = face_data.get('emotions', {})
                if emotions:
                    # show top-2 on overlay
                    sorted_em = sorted(emotions.items(), key=lambda x: x[1], reverse=True)
                    y = 240
                    for name, val in sorted_em[:2]:
                        cv2.putText(frame, f"{name}:{val:.2f}", (30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180,180,255), 2)
                        y += 20

                # If detector returned an error, show a visible debug badge
                if 'detector_error' in locals() and detector_error:
                    cv2.putText(frame, "DETECTOR ERROR", (30, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,0,255), 3)
                    cv2.putText(frame, f"failures:{st.session_state.detector_failures}", (30, 310), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
            else:
                cv2.putText(frame, "NO FACE DETECTED", (30, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 2)
            
            audio_text = "OM PLAYING" if st.session_state.audio_should_be_playing else "OM STOPPED"
            audio_color = (0, 255, 0) if st.session_state.audio_should_be_playing else (255, 0, 0)
            cv2.putText(frame, audio_text, (30, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, audio_color, 3)

            # Convert BGR -> RGB for Streamlit display
            display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(display_frame, channels="RGB", use_column_width=True)
            
            with metrics_placeholder.container():
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a:
                    st.metric("Eyes Status", "Close" if eyes_closed else "Open")
                with col_b:
                    st.metric("Neutrality", f"{neutrality:.2f}")
                with col_c:
                    st.metric("Expression", dominant_emotion.upper())
                    # show small emotion breakdown
                    em = face_data.get('emotions', {})
                    if em:
                        # list top-3
                        top3 = sorted(em.items(), key=lambda x: x[1], reverse=True)[:3]
                        st.write(', '.join([f"{k}:{v:.2f}" for k, v in top3]))
                with col_d:
                    st.metric("Om Sound", "Playing" if st.session_state.audio_should_be_playing else "Stopped")
            
            st.session_state.tracker.add_frame(neutrality, eyes_closed, st.session_state.audio_should_be_playing, dominant_emotion)
        
        cap.release()
    
    with col2:
        st.markdown("#### Session Statistics")
        metrics = st.session_state.tracker.get_session_metrics()
        st.metric("Total Frames", metrics.get('total_frames', 0))
        st.metric("Eyes Closed Count", metrics.get('eyes_closed_count', 0))
        st.metric("Om Playing Time", f"{metrics.get('audio_playing_time', 0)} frames")
        st.metric("Avg Neutrality", f"{metrics.get('avg_neutrality', 0):.2f}")

else:
    st.markdown("""
    ### Welcome to Digital "Om" Chanting triggered by facial recognition
    
    This application monitors your meditation using:
    
    **🎯 Features:**
    - **Eye Detection:** Detects when eyes are open or closed
    - **Neutrality Tracking:** Measures facial calmness
    - **Audio Alerts:** 
        - Beep alert when eyes close
        - Beep alert when eyes open
        - Continuous Om meditation sound
    
    **📊 Session Tracking:**
    - Real-time frame analysis
    - Neutrality scoring
    - Session history saved to database
    
    **🚀 Getting Started:**
    1. Click **▶ Start** button in sidebar
    2. Allow camera access
    3. Meditate while the app tracks your state
    4. Click **⏹ Stop** to end session
    
    **🎵 Audio Setup:**
    - Place custom .mp3 files in `assets/audio/` folder
    - File names: `om.mp3`, `eyes_closed.mp3`, `eyes_open.mp3`
    - App auto-generates beep sounds if files not found
    """)

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    status_text = "<span class='status-active'>🔴 Active</span>" if st.session_state.session_active else "<span class='status-ready'>🟢 Ready</span>"
    st.markdown(f"**Status:** {status_text}", unsafe_allow_html=True)
with col2:
    st.markdown(f"**Session ID:** `{st.session_state.session_id[:8]}...`")
with col3:
    st.markdown("**Database:** `data/faces.db`")
