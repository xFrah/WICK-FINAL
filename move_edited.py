# function that walks through a directory and its subfolders and returns the list of files with specified prefix
import os


def walk_dir(path, prefix):
    files = []
    for root, dirs, filenames in os.walk(path):
        for f in filenames:
            if f.startswith(prefix):
                files.append(os.path.join(root, f))
    return files


# function that creates a copy of a directory and subdirectories but only with files that have specified prefix
def copy_dir(path, prefix, new_path):
    files = walk_dir(path, prefix)
    for file in files:
        new_file = file.replace(path, new_path)
        os.makedirs(os.path.dirname(new_file), exist_ok=True)
        os.rename(file, new_file)


# copy_dir(r"C:\Users\fdimo\Desktop\image-classification-keras\dataset\paper_new", "[EDITED]", r"C:\Users\fdimo\Desktop"
# r"\image-classification-keras\dataset\paper_new_edited")

# function that walks through a directory and its subfolders and moves the files inside the root directory
def move_dir(path):
    walk_path = os.walk(path)
    for root, dirs, filenames in walk_path:
        print(f"[INFO] Walking through {root}")
        for f in filenames:
            os.rename(os.path.join(root, f), os.path.join(path, f))
            print(f"[INFO] Moved {f} to {path}")
        # os.rmdir(root)


move_dir(r"C:\Users\fdimo\Desktop\image-classification-keras\dataset\plastic_new2")
