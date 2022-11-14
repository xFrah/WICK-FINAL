# USAGE
# python webstreaming.py --ip 0.0.0.0 --port 8000

# import the necessary packages
from flask import Response
from flask import Flask
from flask import render_template
import threading
import time
import cv2

# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful for multiple browsers/tabs
# are viewing tthe stream)
outputFrame = None
lock = threading.Lock()

# initialize a flask object
app = Flask(__name__)


def change_frame(frame):
    global outputFrame
    with lock:
        outputFrame = frame.copy()


@app.route("/")
def index():
    # return the rendered template
    return render_template("index.html")


def generate():
    # grab global references to the output frame and lock variables
    global outputFrame, lock

    # loop over frames from the output stream
    while True:
        time.sleep(0.014)
        # wait until the lock is acquired
        with lock:
            if outputFrame is None:
                continue

            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

            # ensure the frame was successfully encoded
            if not flag:
                continue

        # yield the output frame in the byte format
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
               bytearray(encodedImage) + b'\r\n')


@app.route("/video_feed")
def video_feed():
    # return the response generated along with the specific media
    # type (mime type)
    return Response(generate(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


def start_thread(ip, port):
    app.run(host=ip, port=port, debug=True,
            threaded=True, use_reloader=False)