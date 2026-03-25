import cvlib    # high level module, uses YOLO model with the find_common_objects method
import cv2      # image/video manipulation, allows us to pass frames to cvlib
import os
from os import listdir
from os.path import isfile, join
import time
import subprocess

# These will need to be fleshed out to not miss any formats
IMG_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.tiff', '.gif']
VID_EXTENSIONS = ['.mov', '.mp4', '.avi', '.mpg', '.mpeg', '.m4v', '.mkv']

# Global variables to track the status of the analysis
VALID_FILE_ALERT = False
ERROR_ALERT = False
HUMAN_DETECTED_ALERT = False

def humanChecker(video_file_name, save_directory, yolo='yolov4', nth_frame=15, confidence=.65, gpu=False, progress_callback=None):
    """
    Analyzes a video or image file to detect human shapes.
    Saves frames where a person is detected into the specified save_directory.

    Args:
        video_file_name (str): The full path to the video or image file.
        save_directory (str): The path to the directory where frames should be saved.
        yolo (str): The YOLO model to use ('yolov4' or 'yolov4-tiny').
        nth_frame (int): The interval of frames to check (e.g., check every 15th frame).
        confidence (float): The confidence threshold for object detection (0.0 to 1.0).
        gpu (bool): Flag to enable GPU for processing.
        progress_callback (callable): Optional callback function to report progress. Called with messages.

    Returns:
        tuple: A tuple containing (is_human_found, analyze_error).
    """
    person_detection_counter = 0
    global VALID_FILE_ALERT

    is_human_found = False
    analyze_error = False
    is_valid = False
    vid = None # Initialize vid to None
    
    def progress(message):
        """Helper function to emit progress messages"""
        if progress_callback:
            progress_callback(message)

    # Determine if the file is a valid image or video
    file_ext = os.path.splitext(video_file_name)[1].lower()

    if file_ext in IMG_EXTENSIONS:
        frame = cv2.imread(video_file_name)
        if frame is not None:
            # Set a dummy frame_count for images to enter the loop once
            frame_count = nth_frame 
            VALID_FILE_ALERT = True
            is_valid = True
            progress(f'Processing Image: {video_file_name}')
            print(f'Processing Image: {video_file_name}')
        else:
            analyze_error = True
            progress(f'Error: Could not read image file {video_file_name}')
            print(f'Error: Could not read image file {video_file_name}')

    elif file_ext in VID_EXTENSIONS:
        vid = cv2.VideoCapture(video_file_name)
        if not vid.isOpened():
            analyze_error = True
            progress(f"Error: Could not open video file {video_file_name}")
            print(f"Error: Could not open video file {video_file_name}")
        else:
            frame_count = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
            if frame_count > 0:
                VALID_FILE_ALERT = True
                is_valid = True
                progress(f'Processing Video: {video_file_name} ({frame_count} frames)')
                print(f'Processing Video: {video_file_name} ({frame_count} frames)')
            else:
                analyze_error = True
                progress(f'Error: Video file {video_file_name} has no frames.')
                print(f'Error: Video file {video_file_name} has no frames.')
    else:
        progress(f'\nSkipping unsupported file type: {video_file_name}')
        print(f'\nSkipping unsupported file type: {video_file_name}')

    if is_valid:
        # Loop through the video frames at the specified interval
        for frame_number in range(0, frame_count, nth_frame):
            if file_ext in VID_EXTENSIONS:
                vid.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                success, frame = vid.read()
                if not success:
                    progress(f"Warning: Could not read frame {frame_number}. Skipping.")
                    print(f"Warning: Could not read frame {frame_number}. Skipping.")
                    continue

            # Perform object detection on the frame
            try:
                bbox, labels, conf = cvlib.detect_common_objects(frame, model=yolo, confidence=confidence, enable_gpu=gpu)
            except Exception as e:
                error_msg = f"An error occurred during object detection: {e}"
                progress(error_msg)
                print(error_msg)
                analyze_error = True
                break

            # If a 'person' is detected, save the surrounding frames
            if 'person' in labels:
                is_human_found = True
                msg = f"Person detected at frame {frame_number}. Saving frames..."
                progress(msg)
                print(msg)
                # Save the block of frames around the detection
                for i in range(nth_frame):
                    current_frame_pos = frame_number + i
                    if current_frame_pos >= frame_count:
                        break
                    
                    if file_ext in VID_EXTENSIONS:
                        vid.set(cv2.CAP_PROP_POS_FRAMES, current_frame_pos)
                        _, frame_to_save = vid.read()
                        if frame_to_save is not None:
                            person_detection_counter += 1
                            # Use a consistent and sortable naming convention
                            save_file_name = f'frame_{person_detection_counter:06d}.jpg'
                            cv2.imwrite(os.path.join(save_directory, save_file_name), frame_to_save)
                
    # Release the video capture object if it was used
    if vid:
        vid.release()

    return is_human_found, analyze_error

def gen_video(dir_path, progress_callback=None):
    """
    Generates a video from a directory of sorted image frames.
    Uses FFmpeg if available (recommended), falls back to OpenCV.

    Args:
        dir_path (str): The path to the directory containing the image frames.
        progress_callback (callable): Optional callback function to report progress. Called with messages.
    """
    ext = ('.jpg', '.jpeg', '.png')
    images = sorted([f for f in os.listdir(dir_path) if f.lower().endswith(ext)])

    def progress(message):
        """Helper function to emit progress messages"""
        if progress_callback:
            progress_callback(message)

    if not images:
        msg = f"No frames found in {dir_path}, skipping video generation."
        progress(msg)
        print(msg)
        return

    output_path = os.path.join(dir_path, "output.mp4")
    
    # Try FFmpeg first (most reliable for creating MP4s)
    if try_ffmpeg_from_images(dir_path, images, output_path, progress):
        return
    
    # Fallback to OpenCV if FFmpeg not available
    use_opencv_video(dir_path, images, output_path, progress)


def try_ffmpeg_from_images(dir_path, images, output_path, progress_callback=None):
    """Create video directly from image sequence using FFmpeg"""
    def progress(message):
        if progress_callback:
            progress_callback(message)
    
    try:
        # Check if ffmpeg is available
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        if result.returncode != 0:
            return False
        
        progress(f"Creating MP4 video from {len(images)} frames using FFmpeg...")
        print(f"Creating MP4 video from {len(images)} frames using FFmpeg...")
        
        # Use ffmpeg to create video from image sequence
        # %06d will match frame_000001.jpg, frame_000002.jpg, etc.
        input_pattern = os.path.join(dir_path, 'frame_%06d.jpg')
        
        cmd = [
            'ffmpeg',
            '-framerate', '24',
            '-i', input_pattern,
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-y',  # Overwrite output file
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=600)
        
        if result.returncode == 0 and os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            progress(f"✓ MP4 video created successfully! Size: {file_size} bytes")
            print(f"✓ MP4 video created successfully! Size: {file_size} bytes")
            return True
        else:
            error_msg = result.stderr.decode() if result.stderr else "Unknown error"
            progress(f"FFmpeg conversion failed: {error_msg}")
            print(f"FFmpeg conversion failed: {error_msg}")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        progress(f"FFmpeg not available: {str(e)}")
        print(f"FFmpeg not available: {str(e)}")
        return False


def use_opencv_video(dir_path, images, output_path, progress_callback=None):
    """Fallback video creation using OpenCV"""
    def progress(message):
        if progress_callback:
            progress_callback(message)
    
    # Read first image to get dimensions
    first_image_path = os.path.join(dir_path, images[0])
    frame = cv2.imread(first_image_path)
    if frame is None:
        msg = f"Error: Could not read the first frame: {first_image_path}"
        progress(msg)
        print(msg)
        return
    
    height, width, _ = frame.shape
    
    # Try to create AVI with MJPEG codec (most compatible with OpenCV)
    avi_path = os.path.join(dir_path, "output.avi")
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    out = cv2.VideoWriter(avi_path, fourcc, 24.0, (width, height))
    
    if not out.isOpened():
        msg = f"Error: Could not create VideoWriter"
        progress(msg)
        print(msg)
        return
    
    msg = f"Creating AVI video from {len(images)} frames (Resolution: {width}x{height})..."
    progress(msg)
    print(msg)
    
    frames_written = 0
    for image_name in images:
        image_path = os.path.join(dir_path, image_name)
        frame = cv2.imread(image_path)
        if frame is not None:
            out.write(frame)
            frames_written += 1
        else:
            msg = f"Warning: Skipping missing or corrupt frame: {image_name}"
            progress(msg)
            print(msg)

    out.release()
    time.sleep(0.5)
    
    if os.path.exists(avi_path):
        file_size = os.path.getsize(avi_path)
        msg = f"✓ AVI video created! ({frames_written} frames, {file_size} bytes)"
        progress(msg)
        print(msg)
    else:
        msg = f"Error: AVI file was not created"
        progress(msg)
        print(msg)