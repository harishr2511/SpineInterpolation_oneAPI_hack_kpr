import os
from flask import Flask, render_template, request, redirect, url_for, send_file
from werkzeug.utils import secure_filename
import mediapy
import sys
import mediapy
from PIL import Image
from huggingface_hub import snapshot_download
sys.path.append("frame-interpolation")
from eval import interpolator, util

app = Flask(__name__)

# Paths for storing files
INPUT_FOLDER = 'static/images/input'
OUTPUT_FOLDER = 'static/images/output'
VIDEO_FOLDER = 'static/videos'

# Ensure directories exist
os.makedirs(INPUT_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)

app.config['INPUT_FOLDER'] = INPUT_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['VIDEO_FOLDER'] = VIDEO_FOLDER

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        files = request.files.getlist('file')

        # List of existing images in the output folder (for out_2.mp4)
        output_images = [os.path.join(app.config['OUTPUT_FOLDER'], f) for f in os.listdir(app.config['OUTPUT_FOLDER']) if allowed_file(f)]
        
        # Save uploaded images to the input folder (for out_1.mp4)
        new_images = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['INPUT_FOLDER'], filename)
                file.save(filepath)
                new_images.append(filepath)

        # Create videos
        combined_video1 = predict('/Users/harish07/Documents/spine_git/sample_patients/patient1', 0) # Uploaded images (chosen files) -> out_1.mp4
        print("Combined : " ,combined_video1)
        combined_video2 = predict('/Users/harish07/Documents/spine_git/sample_patients/patient1', 2)  # Existing images -> out_2.mp4
        if combined_video1 and combined_video2:
            # Redirect to display the videos once they're created
            return redirect(url_for('display_videos', filename1=os.path.basename(combined_video1), filename2=os.path.basename(combined_video2)))


    return render_template('index.html')

def load_model():
    model = interpolator.Interpolator(snapshot_download(repo_id="akhaliq/frame-interpolation-film-style"), None)
    return model
model = load_model()

def predict(image_dir, times_to_interpolate, desired_duration=3):
    # Get all image paths from the directory and sort them to maintain order
    image_paths = sorted([os.path.join(image_dir, img) for img in os.listdir(image_dir) if img.endswith(('png', 'jpg', 'jpeg'))])
    
    print(f"Number of original frames: {len(image_paths)}")
    print(f"Image paths: {image_paths}")
    
    # Iterate through image pairs and perform interpolation
    interpolated_frames = []
    for i in range(len(image_paths) - 1):
        path1 = image_paths[i]
        path2 = image_paths[i+1]
        
        # Resize second image to match the first image
        #resize_img(path1, path2)
        
        # Interpolation process
        input_frames = [path1, path2]
        frames = list(util.interpolate_recursively_from_files(input_frames, times_to_interpolate, model))
        interpolated_frames.extend(frames)
    
    # Calculate FPS to maintain the desired duration
    total_interpolated_frames = len(interpolated_frames)
    fps = total_interpolated_frames / desired_duration
    
    # Save the video
    print("fps : ", fps)
    mediapy.write_video(f"/Users/harish07/Documents/spine_ui/static/videos/out_{times_to_interpolate}.mp4", interpolated_frames, fps=fps)
    
    return f"/static/videos/out_{times_to_interpolate}.mp4"

@app.route('/display_videos/<filename1>/<filename2>')
def display_videos(filename1,filename2):
    """Renders the video display page with two videos."""
    video_file_path1 = os.path.join(app.config['VIDEO_FOLDER'], filename1)
    video_file_path2 = os.path.join(app.config['VIDEO_FOLDER'], filename2)
    print(video_file_path1)

    if not os.path.exists(video_file_path1) or not os.path.exists(video_file_path2):
        return "One or both videos not found", 404

    # Pass both filenames to the template to render the videos
    return render_template('video.html', filename1=filename1, filename2=filename2)

@app.route('/download/<filename>')
def download_video(filename):
    """Allows downloading the video file."""
    video_path = os.path.join(app.config['VIDEO_FOLDER'], filename)
    if os.path.exists(video_path):
        return send_file(video_path, as_attachment=True)
    return "File not found", 404

if __name__ == "__main__":
    app.run(debug=True)