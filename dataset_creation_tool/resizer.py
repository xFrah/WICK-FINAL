import os
from natsort import natsorted
import cv2 as cv

x_init, y_init, x_final, y_final, drag, first_frame, frame, frame_copy = None, None, None, None, False, None, None, None


# function to add 20 pixels bottom of the image
def add_bottom_padding(frame):
    return cv.copyMakeBorder(frame, 0, 20, 0, 0, cv.BORDER_CONSTANT, None, value=0)


# function to show progress bar on cv2 image window at the bottom of the image
def show_progress_bar(frame, progress, total):
    cv.rectangle(frame, (0, frame.shape[0] - 20), (frame.shape[1], frame.shape[0]), (0, 0, 0), -1)
    cv.rectangle(frame, (0, frame.shape[0] - 20), (int(frame.shape[1] * progress / total), frame.shape[0]), (0, 255, 0),
                 -1)
    cv.putText(frame, f"{progress}/{total}", (frame.shape[1] - 55, frame.shape[0] - 5), cv.FONT_HERSHEY_SIMPLEX, 0.5,
               (255, 255, 255), 1)


def normalize_coords(shape, x_init, y_init, x_final, y_final):
    if x_final < x_init:
        x_final = x_init
    elif x_final > shape[1] - 1:
        x_final = shape[1] - 1
    if y_final < y_init:
        y_final = y_init
    elif y_final > shape[0] - 21:
        y_final = shape[0] - 21
    return x_init, y_init, x_final, y_final


# function that can detect a mouse drag and drop on cv2 window
def mouse_callback(event, x, y, flags, param):
    global x_init, y_init, x_final, y_final, drag, first_frame, frame, frame_copy
    if event == cv.EVENT_LBUTTONDOWN:
        # print("[INFO] Mouse down")
        drag = True
        x_init, y_init = x, y
        first_frame = frame_copy.copy()
    elif event == cv.EVENT_MOUSEMOVE:
        if drag:
            x_final, y_final = x, y
            x_init, y_init, x_final, y_final = normalize_coords(frame.shape, x_init, y_init, x_final, y_final)
            frame_copy = first_frame.copy()
            cv.rectangle(frame_copy, (x_init, y_init), (x_final, y_final), (0, 255, 0), 2)
    elif event == cv.EVENT_LBUTTONUP:
        # print("[INFO] Mouse released")
        drag = False
        x_final, y_final = x, y
        x_init, y_init, x_final, y_final = normalize_coords(frame.shape, x_init, y_init, x_final, y_final)
        frame_copy = first_frame.copy()
        cv.rectangle(frame_copy, (x_init, y_init), (x_final, y_final), (0, 255, 0), 2)


# function that walks through directories and shows images with opencv windows that has callback
def walk_through_images(path):
    global x_init, y_init, x_final, y_final, drag, first_frame, frame, frame_copy
    for root, dirs, files in os.walk(path):
        print(f"[INFO] Walking through {root} !!!!!!!!!!")
        edited_images = {file for file in files if file.startswith("[EDITED]")}
        skipped_images = {file for file in files if file.startswith("[SKIPPED]")}
        done_already = {i.replace("[EDITED]", "") for i in edited_images}
        print(f"[INFO] Skipping {len(done_already) + len(skipped_images) + len(done_already)} files")
        print(f"[INFO] Already done: {len(done_already)}")
        print(f"[INFO] Post-edit: {len(edited_images)}")
        print(f"[INFO] Skipped: {len(skipped_images)}")
        progress_offset = len(done_already) + len(edited_images) + len(skipped_images)
        for i, file in enumerate(natsorted(set(files) - edited_images - done_already - skipped_images)):
            if file.endswith(".jpg") or file.endswith(".png"):
                frame = add_bottom_padding(cv.imread(os.path.join(root, file)))
                print(f"[INFO] Showing {file} from {root}")
                try:
                    frame_copy = frame.copy()
                except AttributeError:
                    print(f"[ERROR] {file} is not a valid image")
                    continue
                cv.namedWindow('image')
                cv.setMouseCallback('image', mouse_callback)
                while True:
                    show_progress_bar(frame_copy, i + progress_offset, len(files))
                    cv.imshow('image', frame_copy)
                    k = cv.waitKey(1) & 0xFF
                    if k == ord('w'):
                        edited_path = os.path.join(root, "[EDITED]" + file)
                        print(f"[INFO] Saved image of size ({y_final - y_init}, {x_final - x_init}) to {edited_path}")
                        cv.imwrite(edited_path, frame[y_init:y_final, x_init:x_final])
                        break
                    elif k == ord('e'):
                        print("[INFO] Skipping image...")
                        edited_path = os.path.join(root, "[SKIPPED]" + file)
                        os.rename(os.path.join(root, file), edited_path)
                        break
                    elif k == ord('q'):
                        print("[INFO] Retrying...")
                        x_init, y_init, x_final, y_final = None, None, None, None
                        frame_copy = frame.copy()
                # cv.destroyAllWindows()
                # print(x_init, y_init, x_final, y_final)
                x_init, y_init, x_final, y_final = 0, 0, 0, 0


walk_through_images(r"C:\Users\fdimo\Desktop\Nuova cartella")
