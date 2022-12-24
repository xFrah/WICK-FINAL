import threading

import pygame
from PIL import ImageOps


class Page:
    def __init__(self, name, background_color=(0, 0, 0)):
        """
        Collection of objects at certain coordinates.
        :param name: Name of the page
        :param name:
        """
        self.name = name
        self.objects = dict()
        self.background_color = background_color

    def add_object(self, name, obj):
        self.objects[name] = obj

    def draw(self, screen):
        for obj in self.objects.values():
            obj.draw(screen)


class GUI:
    def __init__(self, width, height, default_page=Page("default")):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()
        self.pages = {default_page.name: default_page}
        self.current_page = default_page

    def update(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.display.quit()
                pygame.quit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                print(event.pos)
                self.get_correct_touch_callback(event.pos)()
        self.current_page.draw(self.screen)
        self.clock.tick(10)
        pygame.display.update()

    def get_correct_touch_callback(self, event):
        for obj in self.current_page.objects.values():
            if check_if_touch_is_in_object(event, obj):
                return obj.on_touch
        return lambda: None

    def add_page(self, page):
        self.pages[page.name] = page

    def set_page(self, page_name):
        self.current_page = self.pages[page_name]


class Object:
    def __init__(self, x, y, width, height, color, text=None, image=None, on_touch=lambda: None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.image = image
        self.image_y_offset = 0
        self.image_x_offset = 0
        self.text = text
        self.font = pygame.font.SysFont("Arial", 30)
        if self.image is not None:
            self.set_image(self.image)
        self.on_touch = on_touch

    def set_image(self, image):
        # resize image to fit object
        self.image = ImageOps.contain(image, (self.width, self.height))
        # center image
        self.image_x_offset = (self.width - self.image.width) / 2
        self.image_y_offset = (self.height - self.image.height) / 2
        self.image = pygame.image.fromstring(self.image.tobytes(), self.image.size, self.image.mode)

    def draw(self, screen):
        if self.image is None:
            pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
        else:
            screen.blit(self.image, (self.x + self.image_x_offset, self.y + self.image_y_offset))
        if self.text is not None:
            text = self.font.render(self.text, True, (0, 0, 0))
            text_x = self.x + (self.width - text.get_width()) / 2
            text_y = self.y + (self.height - text.get_height()) / 2
            screen.blit(text, (text_x, text_y))


def check_if_touch_is_in_object(touch, obj):
    return obj.x <= touch[0] <= obj.x + obj.width and obj.y <= touch[1] <= obj.y + obj.height
