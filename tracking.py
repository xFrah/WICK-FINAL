import numpy as np

import cv2

# initialize a dictionary that maps strings to their corresponding
# OpenCV object tracker implementations
OPENCV_OBJECT_TRACKERS = {
    "csrt": cv2.TrackerCSRT_create,
    "kcf": cv2.TrackerKCF_create,
    #"boosting": cv2.TrackerBoosting_create,
    #"mil": cv2.TrackerMIL_create,
    #"tld": cv2.TrackerTLD_create,
    #"medianflow": cv2.TrackerMedianFlow_create,
    #"mosse": cv2.TrackerMOSSE_create
}

# grab the appropriate object tracker using our dictionary of
# OpenCV object tracker objects
tracker = OPENCV_OBJECT_TRACKERS["csrt"]()


def track(frames, initBB):
    # start OpenCV object tracker using the supplied bounding box
    # coordinates, then start the FPS throughput estimator as well
    tracker.init(frames[0], initBB)

    # loop over frames from the video stream
    for ind in range(1, len(frames)):
        frame = frames[ind]

        # check to see if we are currently tracking an object
        if initBB is not None:
            # grab the new bounding box coordinates of the object
            (success, box) = tracker.update(frame)

            # check to see if the tracking was a success
            if success:
                (x, y, w, h) = [int(v) for v in box]
                cv2.rectangle(frame, (x, y), (x + w, y + h),
                              (0, 255, 0), 2)

        # show the output frame
        cv2.imshow("Frame", frame)
        key = cv2.waitKey(1) & 0xFF
