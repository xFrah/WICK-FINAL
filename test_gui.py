import random

from PIL import Image

from interface_module import *

screen_width, screen_height = 800, 600

gui = GUI(screen_width, screen_height)

default_page = gui.pages["default"]

# button = Object(0, 0, 400, 600, (255, 0, 0), image=Image.open(r"C:\Users\fdimo\Desktop\minion.png"),  on_touch=lambda: print("button pressed"))
# button2 = Object(400, 0, 400, 300, (0, 255, 0), image=Image.open(r"C:\Users\fdimo\Desktop\Immagine 2022-12-23 234245.png"), on_touch=lambda: print("button pressed"))
# button3 = Object(400, 300, 400, 300, (0, 0, 255), on_touch=lambda: print("button pressed"))
#
# default_page.add_object("test", button)
# default_page.add_object("test2", button2)
# default_page.add_object("test3", button3)
#
# menu_page = Page("menu")
f = lambda: print("button pressed")
buttons = [
    [("1", f), ("2", f), ("3", f)],
    [("4", f), ("5", f), ("6", f)],
    [("7", f), ("8", f)]
]
button_width, button_height, space_between_buttons = 0.25, 0.15, 10
padding_y = (screen_height - (len(buttons) * ((button_height * screen_width) + space_between_buttons))) // 2
rand = random.Random()
count = 0
for j, row in enumerate(buttons):
    padding_x = (screen_width - (len(row) * ((button_width * screen_width) + space_between_buttons))) // 2
    y = padding_y + (j * ((button_height * screen_width) + space_between_buttons))
    for i, (text, func) in enumerate(row):
        count += 1
        x = (i * ((button_width * screen_width) + space_between_buttons)) + padding_x
        default_page.add_object(f"button{count}",
                                Object(x, y, button_width * screen_width, button_height * screen_width, (rand.randint(100, 255), rand.randint(100, 255), rand.randint(100, 255)), text=text,
                                       on_touch=func))

while True:
    gui.update()
