# Video Summarization System

**Author:** Vaishnavi Marihal  
**Institution:** Jain College of Engineering and Technology, Hubballi  
**Year:** 2025  

## Overview
An automated human activity detection and video summarisation system 
using YOLOv4 and OpenCV. The system processes long-duration surveillance 
footage and automatically generates concise highlight clips of detected 
human activity events using GPU-accelerated batch processing.

## Features
- Automated human activity detection in long video footage
- Generates concise highlight clips of detected activity events
- GPU-accelerated batch processing for faster inference
- Configurable detection thresholds for different environments
- Applicable to smart surveillance and public safety scenarios

## Technologies Used
- Python
- YOLOv4
- OpenCV
- NumPy
- GPU acceleration (CUDA)

## How to Run
```bash
pip install -r requirements.txt
python main.py --input video.mp4 --output highlights/
```

## Project Structure
├── main.py
├── detector.py
├── summarizer.py
├── requirements.txt
└── README.md
## Applications
- Smart surveillance systems
- Traffic monitoring
- Public safety monitoring
- Security footage analysis

## Author Note
This project was developed as part of B.E. Computer Science coursework 
at Jain College of Engineering and Technology, Hubballi, India.
