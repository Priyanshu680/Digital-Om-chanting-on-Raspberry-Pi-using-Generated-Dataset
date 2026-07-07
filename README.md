# 🧘 Digital Om Chanting on Raspberry Pi using Generated Dataset

An AI-powered meditation assistant that uses Computer Vision and Raspberry Pi to monitor a user's meditation state in real time and automatically play **Om chanting** when a calm and focused state is detected.

---

## 📖 Overview

This project combines **Artificial Intelligence, Computer Vision, Embedded Systems, and Raspberry Pi** to create an intelligent meditation assistant. The system continuously analyzes facial landmarks, eye closure, and facial neutrality using a camera. When the user maintains a proper meditative state, the system automatically plays soothing **Om chanting** as real-time feedback.

The project demonstrates how embedded AI can be used to enhance traditional meditation practices through intelligent monitoring and interactive feedback.

---

## ✨ Features

- 👁️ Real-time Face Detection
- 😊 Facial Neutrality Detection
- 👀 Eye Closure Detection using Eye Aspect Ratio (EAR)
- 🔊 Automatic Om Chanting Playback
- 📊 Real-time Meditation Monitoring
- 📈 Session Tracking and Performance Analysis
- 💾 Session Data Storage
- 🌐 Streamlit-based User Interface
- 🍓 Raspberry Pi Compatible
- ⚡ Lightweight Real-Time Processing

---

## 🛠️ Hardware Requirements

- Raspberry Pi 5 Model B (Recommended)
- Raspberry Pi Camera Module / USB Webcam
- Speaker or Headphones
- MicroSD Card (32GB or higher)
- 5V/3A Power Supply

---

## 💻 Software Requirements

- Python 3.x
- Raspberry Pi OS
- OpenCV
- MediaPipe
- NumPy
- Streamlit
- Pygame / Pydub
---

## 📂 Project Structure

```
Digital-Om-Chanting-Raspberry-Pi/
│
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
│
├── src/
│   ├── main.py
│   ├── face_detector.py
│   ├── eye_detection.py
│   ├── emotion_detection.py
│   ├── audio_manager.py
│   └── session_tracker.py
│
├── dataset/
│
├── models/
│
├── audio/
│   └── om_chant.mp3
│
├── images/
│
├── outputs/
│
└── docs/
    └── Project_Report.pdf
```

---

## ⚙️ Installation

Clone the repository

```bash
git clone https://github.com/YourUsername/Digital-Om-Chanting-Raspberry-Pi.git
```

Move into the project folder

```bash
cd Digital-Om-Chanting-Raspberry-Pi
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run the application

```bash
python src/main.py
```

or (for Streamlit)

```bash
streamlit run src/main.py
```

---

## 🧠 Working Principle

1. Capture live video from the camera.
2. Detect the user's face using MediaPipe.
3. Extract facial landmarks.
4. Calculate Eye Aspect Ratio (EAR).
5. Analyze facial neutrality.
6. Determine the meditation state.
7. Play Om chanting when the user maintains a calm and focused state.
8. Stop audio immediately when distraction is detected.
9. Store session data for future analysis.

---

## 🔬 Technologies Used

- Python
- OpenCV
- MediaPipe
- NumPy
- Streamlit
- Raspberry Pi
- Computer Vision
- Embedded Systems
- Artificial Intelligence
- Deep Learning (Optional)

---

## 📈 Applications

- Smart Meditation Assistant
- Yoga Centers
- Wellness Centers
- Mental Health Monitoring
- Educational AI Projects
- Embedded AI Applications

---

## 🚀 Future Improvements

- Mobile Application Integration
- IoT Connectivity
- Cloud Analytics Dashboard
- Multi-user Recognition
- Voice Assistant Integration
- Personalized Meditation Recommendations
- Hardware Acceleration using Coral TPU

---

## 📸 Screenshots

Add screenshots of:

- System Interface
- Face Detection
- Eye Detection
- Om Chanting Trigger
- Raspberry Pi Setup

---

## 📚 Project Report

The complete project report is available in the **docs/** directory.

---

## 👨‍💻 Authors

**Priyanshu**  
B.Tech – Computer Science & Engineering (Data Science)  
B.K. Birla Institute of Engineering & Technology, Pilani

**Lubhawan Verma**  
B.Tech – Computer Science & Engineering  
B.K. Birla Institute of Engineering & Technology, Pilani

---

## 👨‍🏫 Project Guide

**Mr. Gauttam Jangir**  
Assistant Professor  
Department of Computer Science & Engineering  
B.K. Birla Institute of Engineering & Technology, Pilani

---

## 📄 License

This project is developed for academic and educational purposes.

---
