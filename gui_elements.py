import pygame
import pyperclip
import os
from sound import SoundCore


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
                self.text += pyperclip.paste()
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
