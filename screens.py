import os
from string import Template

import pygame.event

from config import WIDTH, HEIGHT
from event_codes import *
from gui_elements import Button, TextInput
from sound import SoundCore

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (125, 125, 125)
LIGHT_BLUE = (64, 128, 255)
GREEN = (0, 200, 64)
YELLOW = (225, 225, 0)
PINK = (230, 50, 230)

def load_background(image_name: str) -> pygame.Surface:
    path = os.path.join("data", "Background", image_name)
    image = pygame.transform.scale(pygame.image.load(path), (WIDTH, HEIGHT))
    return image.convert()


class Menu:
    def __init__(self):
        self.visible = True
        self.background = load_background("menu.png")
        self.button_start_server = Button(size=(WIDTH // 2, HEIGHT // 12),
                                          pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2),
                                          event=pygame.event.Event(START_SERVER_MENU_EVENT),
                                          text="Start server",
                                          font='data/fonts/menu_font.ttf')
        self.button_connect = Button(size=(WIDTH // 2, HEIGHT // 12),
                                     pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2 + HEIGHT // 8),
                                     event=pygame.event.Event(OPEN_CONNECTION_MENU_EVENT),
                                     text="Connect to server",
                                     font='data/fonts/menu_font.ttf')
        self.button_exit = Button(size=(WIDTH // 4.2, HEIGHT // 12),
                                  pos=(3 * WIDTH // 4 - WIDTH // 4.2, HEIGHT // 2 + 2 * HEIGHT // 8),
                                  event=pygame.event.Event(EXIT_GAME_EVENT),
                                  text="Quit", font='data/fonts/menu_font.ttf')
        self.button_settings = Button(size=(WIDTH // 4.2, HEIGHT // 12),
                                      pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2 + 2 * HEIGHT // 8),
                                      event=pygame.event.Event(OPEN_SETTINGS_MENU_EVENT),
                                      text="Settings",
                                      font='data/fonts/menu_font.ttf')

    def draw(self, screen: pygame.Surface):
        screen.blit(self.background, (0, 0))
        self.button_connect.draw(screen, 1)
        self.button_start_server.draw(screen, 1)
        self.button_settings.draw(screen, 1)
        self.button_exit.draw(screen, 1)


class ConnectToServerMenu:
    def __init__(self):
        self.background = load_background('connect_menu.png')
        self.button_back = Button(size=(WIDTH // 5, 40),
                                  pos=(10, 10),
                                  text="Back",
                                  event=pygame.event.Event(OPEN_MAIN_MENU_EVENT))
        self.text_input_address = TextInput(size=(WIDTH // 2, 25),
                                            pos=((WIDTH - WIDTH // 2) // 2, HEIGHT // 2),
                                            hint="server address",
                                            text="",
                                            font='data/fonts/menu_font.ttf')

        self.button_start_game = Button(size=(WIDTH // 5, 40),
                                        pos=(WIDTH - WIDTH // 5 - 10, HEIGHT - 40 - 10),
                                        text="Connect",
                                        event=pygame.event.Event(CONNECT_TO_SERVER_EVENT, ))

    def event_handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            connect_event = pygame.event.Event(CONNECT_TO_SERVER_EVENT)
            connect_event.dict['input'] = self.text_input_address.text
            pygame.event.post(connect_event)

            return
        self.text_input_address.event_handle(event)
        self.button_start_game.event.dict['input'] = self.text_input_address.text

    def draw(self, screen: pygame.Surface):
        screen.blit(self.background, (0, 0))
        self.text_input_address.draw(screen, 1)
        self.button_back.draw(screen, 1)
        self.button_start_game.draw(screen, 1)


class StartServerMenu:
    def __init__(self):
        self.background = load_background('connect_menu.png')
        self.button_back = Button(size=(WIDTH // 5, 40),
                                  pos=(10, 10),
                                  text="Back",
                                  event=pygame.event.Event(OPEN_MAIN_MENU_EVENT))
        self.text_input_address = TextInput(size=(WIDTH // 2, 25),
                                            pos=((WIDTH - WIDTH // 2) // 2, HEIGHT // 2),
                                            hint="server address",
                                            text="",
                                            font='data/fonts/menu_font.ttf')

        self.button_start_game = Button(size=(WIDTH // 5, 40),
                                        pos=(WIDTH - WIDTH // 5 - 10, HEIGHT - 40 - 10),
                                        text="Start server",
                                        event=pygame.event.Event(CONNECT_TO_SERVER_EVENT, ))

    def event_handle(self, event):
        self.text_input_address.event_handle(event)
        self.button_start_game.event.dict['input'] = self.text_input_address.text

    def draw(self, screen: pygame.Surface):
        screen.blit(self.background, (0, 0))
        self.text_input_address.draw(screen, 1)
        self.button_back.draw(screen, 1)
        self.button_start_game.draw(screen, 1)


class MessageScreen:
    def __init__(self, message, event):
        self.set_text(message)
        self.button_ok = Button(size=(WIDTH // 5, 40),
                                pos=(WIDTH - WIDTH // 5 - 10, HEIGHT - 40 - 10),
                                text="Ok",
                                event=event)

    def set_text(self, text):
        self.text = text
        font = pygame.font.Font(None, 100)
        self.image = pygame.Surface((WIDTH, HEIGHT))
        self.image.fill((0, 0, 0))
        text_image = font.render(self.text, True, (255, 255, 255))

        text_image = pygame.transform.scale_by(text_image, WIDTH / text_image.get_width())
        self.image.blit(text_image, (WIDTH // 2 - text_image.get_width() // 2,
                                     HEIGHT // 2 - text_image.get_height() // 2))

    def draw(self, screen):
        screen.blit(self.image, (0, 0))
        self.button_ok.draw(screen, 1)


class LoadingScreen:
    def __init__(self, text='Waiting...'):
        self.set_text(text)
        self.visible = False

    def set_text(self, text):
        self.text = text
        font = pygame.font.Font(None, 100)
        self.image = pygame.Surface((WIDTH, HEIGHT))
        self.image.fill((0, 0, 0))
        text_image = font.render(self.text, True, (255, 255, 255))
        self.image.blit(text_image, (WIDTH // 2 - text_image.get_width() // 2,
                                     HEIGHT // 2 - text_image.get_height() // 2))

    def draw(self, screen):
        screen.blit(self.image, (0, 0))


class SettingsMenu:
    def __init__(self):
        self.visible = True
        self.background = load_background("settings_menu.png")
        self.change_window_mode = Button(size=(WIDTH // 4.2, HEIGHT // 12),
                                         pos=(3 * WIDTH // 4 - WIDTH // 4.2, HEIGHT // 2 + 2 * HEIGHT // 8),
                                         event=pygame.event.Event(START_SERVER_MENU_EVENT),
                                         text="Change Window Mode",
                                         font='data/fonts/menu_font.ttf')
        self.music_off = Button(size=(WIDTH // 2, HEIGHT // 12),
                                pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2 + HEIGHT // 8),
                                event=pygame.event.Event(CHANGE_MUSIC_MODE),
                                text='Music off' if SoundCore.is_music_on else 'Music on',
                                font='data/fonts/menu_font.ttf')
        self.sounds_off = Button(size=(WIDTH // 2, HEIGHT // 12),
                                 pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2),

                                 event=pygame.event.Event(CHANGE_SOUND_MODE),
                                 text='Sound off' if SoundCore.is_sound_on else 'Sound on', font='data/fonts/menu_font.ttf')
        self.return_back = Button(size=(WIDTH // 4.2, HEIGHT // 12),
                                  pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2 + 2 * HEIGHT // 8),
                                  event=pygame.event.Event(OPEN_MAIN_MENU_EVENT),
                                  text="To Menu",
                                  font='data/fonts/menu_font.ttf')

    def buttons_update(self):
        self.sounds_off = Button(size=(WIDTH // 2, HEIGHT // 12),
                                 pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2),
                                 event=pygame.event.Event(CHANGE_SOUND_MODE),
                                 text='Sound off' if SoundCore.is_sound_on else 'Sound on', font='data/fonts/menu_font.ttf')
        self.music_off = Button(size=(WIDTH // 2, HEIGHT // 12),
                                pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2 + HEIGHT // 8),
                                event=pygame.event.Event(CHANGE_MUSIC_MODE),
                                text='Music off' if SoundCore.is_music_on else 'Music on',
                                font='data/fonts/menu_font.ttf')
    def draw(self, screen: pygame.Surface):
        screen.blit(self.background, (0, 0))
        self.change_window_mode.draw(screen, 1)
        self.music_off.draw(screen, 1)
        self.sounds_off.draw(screen, 1)
        self.return_back.draw(screen, 1)

class EndScreen:
    # это потом переделаю, пока искал константы
    TABCOORD = (WIDTH * 0.01, HEIGHT * 0.05, WIDTH * 0.98, HEIGHT * 0.87)
    PLAYERCOORD1 = (WIDTH * 0.02, HEIGHT * 0.07, WIDTH * 0.22, HEIGHT * 0.35)
    PLAYERCOORD2 = (WIDTH * 0.77, HEIGHT * 0.07, WIDTH * 0.97, HEIGHT * 0.35)
    PLAYERCOORD3 = (WIDTH * 0.02, HEIGHT * 0.07, WIDTH * 0.22, HEIGHT * 0.35)
    PLAYERCOORD4 = (WIDTH * 0.02, HEIGHT * 0.07, WIDTH * 0.22, HEIGHT * 0.35)
    GAMECOORD = (WIDTH * 0.25, HEIGHT * 0.1, WIDTH * 0.45, HEIGHT * 0.75)

    def __init__(self, statistics):
        self.background = load_background('settings_menu.png')
        self.n_players = len(statistics.keys())
        self.table = pygame.Rect(EndScreen.TABCOORD)
        self.player_card1 = pygame.Rect(EndScreen.PLAYERCOORD1)
        self.player_card2 = pygame.Rect(EndScreen.PLAYERCOORD2)
        self.game_card = pygame.Rect(EndScreen.GAMECOORD)
        self.button_back = Button(size=(WIDTH // 5, 30),
                                  pos=(WIDTH - WIDTH // 5 - 10, HEIGHT - 40),
                                  text="Menu",
                                  event=pygame.event.Event(OPEN_MAIN_MENU_EVENT))

    def draw(self, screen: pygame.Surface):
        screen.blit(self.background, (0, 0))
        pygame.draw.rect(screen, WHITE, self.table)
        pygame.draw.rect(screen, GRAY, self.player_card1)
        pygame.draw.rect(screen, GRAY, self.player_card2)
        pygame.draw.rect(screen, BLACK, self.game_card)
        self.button_back.draw(screen, 1)
