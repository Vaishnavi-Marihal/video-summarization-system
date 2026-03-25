from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from flask import request, Response, abort
# --- Step 1: Import your processing functions ---
# You will need to modify summerize.py so these functions can be imported.
# I'll explain the changes for that file below.
from summarizer import humanChecker, gen_video
import queue
import threading
import json

app = Flask(__name__)

# Define the base directory where all summary folders will be created.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Define a folder to temporarily store uploads.
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create the upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global queue to manage SSE progress streams
progress_queues = {}  # Maps session IDs to queues


# @app.route('/', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # --- Handle the file upload from the fetch request ---
        if 'video_file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files['video_file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        if file:
            # Save the uploaded file
            input_filename = secure_filename(file.filename)
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
            file.save(input_path)
            
            # Create a unique session ID for this processing job
            time_stamp = datetime.now().strftime('%m%d%Y%H%M%S')
            
            # Return the filename and timestamp to the frontend
            return jsonify({
                "filename": input_filename,
                "input_path": input_path,
                "timestamp": time_stamp
            })
            
    # GET request: Just show the main index.html page
    return render_template('index.html')


@app.route('/process_video', methods=['POST'])
def process_video():
    """Process the video with real-time progress updates via SSE"""
    data = request.json
    input_path = data.get('input_path')
    timestamp = data.get('timestamp')
    filename = data.get('filename')
    
    if not input_path or not timestamp:
        return jsonify({"error": "Missing input_path or timestamp"}), 400
    
    # Create a queue for this session
    session_queue = queue.Queue()
    progress_queues[timestamp] = session_queue
    
    # Start the processing in a separate thread
    processing_thread = threading.Thread(
        target=process_video_worker,
        args=(input_path, timestamp, filename, session_queue)
    )
    processing_thread.daemon = True
    processing_thread.start()
    
    return jsonify({"status": "processing started", "timestamp": timestamp})


@app.route('/progress/<timestamp>')
def progress(timestamp):
    """Server-Sent Events endpoint to stream progress updates"""
    def generate():
        queue_obj = progress_queues.get(timestamp)
        if not queue_obj:
            yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
            return
        
        while True:
            try:
                # Get messages from the queue with a timeout
                message = queue_obj.get(timeout=60)
                if message == "DONE":
                    yield f"data: {json.dumps({'status': 'complete'})}\n\n"
                    break
                else:
                    yield f"data: {json.dumps({'message': message})}\n\n"
            except queue.Empty:
                # Send a heartbeat to keep connection alive
                yield f": heartbeat\n\n"
                continue
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break
        
        # Clean up
        if timestamp in progress_queues:
            del progress_queues[timestamp]
    
    return Response(generate(), mimetype='text/event-stream')


def process_video_worker(input_path, timestamp, filename, queue_obj):
    """Background worker to process video with progress updates"""
    try:
        # Create save directory
        save_dir = os.path.join(BASE_DIR, timestamp)
        os.makedirs(save_dir, exist_ok=True)
        queue_obj.put(f"Save directory: {save_dir}")
        
        def progress_callback(message):
            """Callback to send progress updates to the queue"""
            queue_obj.put(message)
        
        # Run the human checker with progress callback
        queue_obj.put(f"Starting summarization for {filename}...")
        is_human_found, analyze_error = humanChecker(video_file_name=input_path, save_directory=save_dir, yolo='yolov4-tiny', progress_callback=progress_callback)
        
        if analyze_error:
            queue_obj.put("Error occurred during human detection!")
        
        # Check frames
        frames = [f for f in os.listdir(save_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        queue_obj.put(f"Total frames saved: {len(frames)}")
        
        if len(frames) == 0:
            queue_obj.put("Warning: No frames were saved! Humans may not have been detected.")
        
        # Generate the output video
        queue_obj.put("Generating output video...")
        gen_video(dir_path=save_dir, progress_callback=progress_callback)
        
        # Verify output file exists
        output_file = os.path.join(save_dir, "output.mp4")
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            queue_obj.put(f"Output video created successfully! Size: {file_size} bytes")
        else:
            queue_obj.put(f"ERROR: Output video file not created at {output_file}")
        
        queue_obj.put("Processing complete!")
        queue_obj.put("DONE")
        
    except Exception as e:
        queue_obj.put(f"Error during processing: {str(e)}")
        import traceback
        queue_obj.put(f"Traceback: {traceback.format_exc()}")
        queue_obj.put("DONE")
# def index():
#     if request.method == 'POST':
#         # --- Step 2: Handle the file upload securely ---
#         if 'video_file' not in request.files:
#             return "No file part", 400
#         file = request.files['video_file']
#         if file.filename == '':
#             return "No selected file", 400

#         if file:
#             # Save the uploaded file to the 'uploads' folder
#             input_filename = secure_filename(file.filename)
#             input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
#             file.save(input_path)

#             # --- Step 3: Control the summarization process from Flask ---
            
#             # Create the unique timestamped directory for the results
#             time_stamp = datetime.now().strftime('%m%d%Y%H%M%S')
#             save_dir = os.path.join(BASE_DIR, time_stamp)
#             os.makedirs(save_dir, exist_ok=True)
            
#             print(f"Starting summarization for {input_path}...")
#             print(f"Frames will be saved in: {save_dir}")

#             # Call your imported functions directly
#             humanChecker(video_file_name=input_path, save_directory=save_dir, yolo='yolov4-tiny')
#             gen_video(dir_path=save_dir)
            
#             print("Summarization complete.")

#             # --- Step 4: Redirect to a display page that knows the correct path ---
#             # We pass the 'time_stamp' folder name to the next route.
#             return redirect(url_for('display', timestamp_folder=time_stamp))
            
#     return render_template('index.html')


@app.route('/display/<timestamp_folder>')
def display(timestamp_folder):
    # The output filename is always 'output.mp4'
    output_filename = 'output.mp4'
    # Pass both the folder and filename to the template
    return render_template('display.html', folder=timestamp_folder, filename=output_filename)

@app.route('/check_video/<timestamp>/<filename>')
def check_video(timestamp, filename):
    """Check if a video file exists and return its size"""
    file_path = os.path.join(BASE_DIR, timestamp, filename)
    
    # Try MP4 first, then AVI
    if not os.path.exists(file_path):
        alt_file_path = file_path.replace('.mp4', '.avi')
        if os.path.exists(alt_file_path):
            file_path = alt_file_path
    
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        return jsonify({
            "exists": True,
            "size": file_size,
            "path": file_path,
            "filename": os.path.basename(file_path),
            "url": f"/download/{timestamp}/{os.path.basename(file_path)}"
        })
    else:
        available_files = []
        dir_path = os.path.join(BASE_DIR, timestamp)
        if os.path.exists(dir_path):
            available_files = [f for f in os.listdir(dir_path) if f.endswith(('.mp4', '.avi'))]
        return jsonify({
            "exists": False,
            "path": file_path,
            "available_files": available_files
        })


@app.route('/download/<timestamp_folder>/<filename>')
def download_file(timestamp_folder, filename):
    directory_path = os.path.join(BASE_DIR, timestamp_folder)
    file_path = os.path.join(directory_path, filename)
    
    # Try requested file first, then fallback to AVI if MP4 not found
    if not os.path.exists(file_path):
        alt_file_path = file_path.replace('.mp4', '.avi')
        if os.path.exists(alt_file_path):
            file_path = alt_file_path
            filename = os.path.basename(alt_file_path)

    if not os.path.exists(file_path):
        return jsonify({"error": f"File not found: {file_path}"}), 404

    force_download = request.args.get('action') == 'download'
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get('Range', None)
    
    # Determine MIME type
    mime_type = "video/mp4" if filename.endswith('.mp4') else "video/x-msvideo"

    if range_header and not force_download:
        # --- Handle partial requests (streaming) ---
        byte1, byte2 = 0, None
        m = range_header.replace("bytes=", "").split("-")
        if m[0]:
            byte1 = int(m[0])
        if len(m) > 1 and m[1]:
            byte2 = int(m[1])

        length = (byte2 + 1 if byte2 else file_size) - byte1

        with open(file_path, 'rb') as f:
            f.seek(byte1)
            data = f.read(length)

        rv = Response(data, 206, mimetype=mime_type, direct_passthrough=True)
        rv.headers.add("Content-Range", f"bytes {byte1}-{byte1 + length - 1}/{file_size}")
        rv.headers.add("Accept-Ranges", "bytes")
        rv.headers.add("Content-Length", str(length))
        rv.headers.add("Cache-Control", "public, max-age=3600")
        return rv

    # --- Full file download or inline playback ---
    try:
        with open(file_path, "rb") as f:
            data = f.read()
    except IOError as e:
        return jsonify({"error": f"Could not read file: {str(e)}"}), 500

    disposition = "attachment" if force_download else "inline"
    
    response = Response(data, 200, mimetype=mime_type)
    response.headers["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    response.headers["Content-Type"] = mime_type
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Content-Length"] = str(file_size)
    response.headers["Cache-Control"] = "public, max-age=3600"
    
    return response


@app.route('/about/')
def about():
    return render_template('about.html')


@app.route('/know/')
def know():
    return render_template('know.html')


if __name__ == "__main__":
    app.run(debug=True)