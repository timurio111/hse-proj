import pygame
import pyperclip
from sound import SoundCore
from weapon import Weapon
from config import WIDTH, HEIGHT

RED = (255, 0, 0)
GRAY = (125, 125, 125)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)


class TextInput:
    def __init__(self, size, pos, text="", hint="", font=None):
        self.width = size[0]
        self.height = size[1]
        self.font = pygame.font.Font(font, self.height)
        self.active = False

        self.x = pos[0]
        self.y = pos[1]

        self.text = text
        self.text_surf = self.font.render(self.text, True, (255, 255, 255))
        self.hint = hint
        self.hint_surf = self.font.render(self.hint, True, (100, 100, 100))
        self.image_active = pygame.Surface(size)
        self.image_active.fill((0, 0, 0))
        self.image_inactive = pygame.Surface(size)
        self.image_inactive.fill((50, 50, 50))

        self.rect = pygame.Rect(pos, size)

    def event_handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
            else:
                self.active = False
        if not self.active:
            return
        if event.type == pygame.KEYDOWN:
            if (event.key == pygame.K_v) and ((event.mod & pygame.KMOD_META) or (event.mod & pygame.KMOD_CTRL)):
                clipboard = pyperclip.paste()
                if clipboard:
                    self.text += clipboard
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
        self.text_surf = self.font.render(self.text, True, (255, 255, 255))

    def draw(self, screen: pygame.Surface, scale):
        if self.active:
            screen.blit(self.image_active, (self.x, self.y))
        else:
            screen.blit(self.image_inactive, (self.x, self.y))
        if not self.text:
            screen.blit(self.hint_surf, (self.x, self.y))
        else:
            screen.blit(self.text_surf, (self.x, self.y))


class Button:
    def __init__(self, size, pos, text="", border_width=2, font=None, event=None):
        self.event = event

        self.border_width = border_width
        self.hover = False
        self.pressed = False

        self.width = size[0]
        self.height = size[1]
        self.font = pygame.font.Font(font, self.height)

        self.x = pos[0]
        self.y = pos[1]

        self.text = text
        self.image_default = self.__get_image((200, 200, 200))
        self.image_hover = self.__get_image((180, 180, 180))
        self.image_pressed = self.__get_image((150, 150, 150))
        self.rect = pygame.Rect(pos, size)
        self.is_hover_sound_played = False

    def __get_image(self, color) -> pygame.Surface:
        frame = pygame.Surface((self.width, self.height))
        frame.fill((50, 50, 50))
        temp = pygame.Surface((self.width - 2 * self.border_width, self.height - 2 * self.border_width))
        temp.fill(color)
        frame.blit(temp, (self.border_width, self.border_width))

        text_surf = self.font.render(self.text, True, (0, 0, 0))
        factor = 0.9 / max(text_surf.get_width() / self.width, text_surf.get_height() / self.height)
        text_surf = pygame.transform.scale_by(text_surf, factor)
        frame.blit(text_surf, (self.width // 2 - text_surf.get_width() // 2,
                               self.height // 2 - text_surf.get_height() // 2))
        return frame

    def draw(self, screen: pygame.Surface, scale):
        self.update(scale)
        if self.pressed:
            image = self.image_pressed
        elif self.hover:
            image = self.image_hover
        else:
            image = self.image_default
        screen.blit(image, (self.x, self.y))

    def update(self, scale):
        mouse_pos = pygame.mouse.get_pos()
        mouse_pos = (mouse_pos[0] // scale, mouse_pos[1] // scale)
        if self.rect.collidepoint(mouse_pos):
            self.hover = True
            if not self.is_hover_sound_played:
                SoundCore.menu_button_is_hover.sound_play()
                self.is_hover_sound_played = True
            if pygame.mouse.get_pressed()[0]:
                self.pressed = True
            else:
                if self.pressed:
                    if self.event is not None:
                        SoundCore.menu_button_is_pressed.sound_play()
                        pygame.event.post(self.event)
                self.pressed = False
        else:
            self.pressed = False
            self.hover = False
            self.is_hover_sound_played = False


class Slider:
    def __init__(self, size, pos, slider_color=(255, 255, 255), bar_color=(0, 0, 0), event=None):
        self.width, self.height = size
        self.x, self.y = pos
        self.slider_color = slider_color
        self.bar_color = bar_color
        self.event = event

        self.pressed = False

        self.slider_pos = 0
        self.slider_radius = self.height // 2
        self.image = self.__get_image()

    def __get_image(self):
        frame = pygame.Surface((self.width + self.slider_radius * 2, self.height), pygame.SRCALPHA)
        line = pygame.Surface((self.width + self.slider_radius * 2, 4))
        line.fill(self.bar_color)
        frame.blit(line, (0, self.height // 2))
        return frame

    def draw(self, screen: pygame.Surface):
        screen.blit(self.image, (self.x - self.slider_radius, self.y))
        pygame.draw.circle(screen, self.slider_color, (self.x + self.width * self.slider_pos, self.y + self.height // 2), self.slider_radius)

    def get_value(self):
        return self.slider_pos

    def event_handle(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEMOTION:
            if not self.pressed:
                return
            x, y = event.pos
            dx = min(max(0, x - self.x), self.width)
            self.slider_pos = dx / self.width
            if self.event is not None:
                self.event.dict['value'] = self.slider_pos
                pygame.event.post(self.event)

        if event.type == pygame.MOUSEBUTTONDOWN:
            point = self.x + self.width * self.slider_pos, self.y + self.height // 2
            dist = pygame.math.Vector2(point).distance_to(event.pos)
            if dist < self.slider_radius:
                self.pressed = True

        if event.type == pygame.MOUSEBUTTONUP:
            self.pressed = False


class TextBox:
    def __init__(self, size, pos, text="", font=None, text_color=(200, 200, 200)):
        self.x, self.y = pos
        self.width, self.height = size
        self.font = pygame.font.Font(font, self.height)
        self.text = text
        self.text_color = text_color
        self.image = self.__get_image()

    def __get_image(self) -> pygame.Surface:
        frame = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        text_surf = self.font.render(self.text, True, self.text_color)
        factor = 1 / max(text_surf.get_width() / self.width, text_surf.get_height() / self.height)
        text_surf = pygame.transform.scale_by(text_surf, factor)
        frame.blit(text_surf, (self.width // 2 - text_surf.get_width() // 2,
                               self.height // 2 - text_surf.get_height() // 2))
        return frame

    def draw(self, screen: pygame.Surface):
        screen.blit(self.image, (self.x, self.y))


class Bar:
    BAR_SIZE = (WIDTH // 10, HEIGHT // 80)
    BAR_THICKNESS = 2

    def __init__(self, x, y, cur_value, max_value, color):
        self.x = x
        self.y = y
        self.max_value = max_value
        self.bar_background = pygame.rect.Rect((x, y, Bar.BAR_SIZE[0], Bar.BAR_SIZE[1]))
        self.bar = pygame.rect.Rect((x, y, Bar.BAR_SIZE[0] * cur_value / max_value, Bar.BAR_SIZE[1]))
        self.color = color
        self.current_value = cur_value

    def update(self, change):
        self.current_value = change['value']
        self.bar = pygame.rect.Rect((self.x, self.y, Bar.BAR_SIZE[0] * self.current_value // self.max_value, Bar.BAR_SIZE[1]))

    def draw(self, screen: pygame.Surface, change):
        self.update(change)
        pygame.draw.rect(screen, self.color, self.bar)
        pygame.draw.rect(screen, self.color, self.bar_background, Bar.BAR_THICKNESS)


class HpBar(Bar):
    MAX_HP = 100
    HP_BAR_COORD = (1, 1)
    YELLOW_MARK = 60
    RED_MARK = 30

    def __init__(self, cur_hp):
        Bar.__init__(self, HpBar.HP_BAR_COORD[0], HpBar.HP_BAR_COORD[1], cur_hp, HpBar.MAX_HP, GREEN)

    def update(self, change):
        super().update(change)
        if HpBar.RED_MARK < self.current_value <= HpBar.YELLOW_MARK:
            self.color = YELLOW
        elif self.current_value < HpBar.RED_MARK:
            self.color = RED
        else:
            self.color = GREEN


