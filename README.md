# Video Summarization System

**Author:** Vaishnavi Marihal  
**Institution:** Jain College of Engineering and Technology, Hubballi  
**Year:** 2025  

## Overview
A Flask-based web application that automatically detects human activity 
in uploaded surveillance videos using YOLOv4 and generates concise 
highlight clips of detected activity events. Features real-time 
processing progress updates via Server-Sent Events (SSE).

## Features
- Upload any video file via web interface
- Automatic human activity detection using YOLOv4-tiny
- Real-time processing progress updates (Server-Sent Events)
- GPU-accelerated batch processing support
- Generates highlight clips using FFmpeg (OpenCV fallback)
- Configurable detection confidence thresholds
- Supports MP4, AVI, MOV and other common video formats

## Technologies Used
- Python
- Flask (web framework)
- YOLOv4 / YOLOv4-tiny (human detection)
- cvlib (object detection wrapper)
- OpenCV (video processing)
- FFmpeg (video generation)
- NumPy
- Threading (background processing)

## How It Works
1. User uploads a video via the web interface
2. System processes every nth frame using YOLOv4-tiny
3. Frames containing detected humans are saved
4. FFmpeg compiles saved frames into a highlight video
5. User downloads the summarised output video

## How to Run
```bash
# Clone the repository
git clone https://github.com/Vaishnavi-Marihal/video-summarization-system

# Install dependencies
pip install -r requirements.txt

# Ensure FFmpeg is installed
ffmpeg -version

# Run the application
python app.py

# Open in browser
http://127.0.0.1:5000/
```

## Requirements
- Python 3.8+
- FFmpeg installed and on PATH
- GPU optional (CPU mode supported)

## Applications
- Smart surveillance systems
- Security footage analysis
- Traffic monitoring
- Public safety monitoring

## Author Note
This project was developed as part of B.E. Computer Science coursework 
at Jain College of Engineering and Technology, Hubballi, India.
