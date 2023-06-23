from flask import Flask, render_template, Response
import torch
import cv2
from PIL import Image

app = Flask(__name__)

@app.route('/realtime')
def index():
    return render_template('video.html')

def detect_objects():
    # Load the YOLOv5 model with .pt weights
    model = torch.hub.load('ultralytics/yolov5', 'custom', path='model/menyontek.pt', force_reload=True)

    # Open camera
    cap = cv2.VideoCapture(0)

    while True:
        # Read frame from the camera
        ret, frame = cap.read()

        if ret:
            frame = cv2.flip(frame, 1)

            # Convert frame to PIL Image
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            # Perform inference on the image
            results = model(image)

            # Get detection results
            pred_boxes = results.xyxy[0]

            # Draw bounding boxes and labels on the frame
            for *xyxy, conf, cls in pred_boxes:
                x1, y1, x2, y2 = map(int, xyxy)
                label = f'{model.names[int(cls)]} {conf:.2f}'
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)

            # Convert the frame back to BGR format
            frame = cv2.cvtColor(frame, cv2.WINDOW_NORMAL)

            # Encode the frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)

            if not ret:
                continue

            # Yield the frame as a byte array
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'

        else:
            break

    # Release the camera and clean up
    cap.release()

@app.route('/video_feed')
def video_feed():
    return Response(detect_objects(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # app.run(debug=True)
    app.run(host='192.168.43.170', port='5000', debug=True)
