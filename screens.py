import os
from string import Template

import pygame

from config import WIDTH, HEIGHT
from event_codes import *
from gui_elements import Button, TextInput

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
        self.background = load_background("gradient2.png")
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
        self.button_exit = Button(size=(WIDTH // 2, HEIGHT // 12),
                                  pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2 + 2 * HEIGHT // 8),
                                  event=pygame.event.Event(EXIT_GAME_EVENT),
                                  text="Quit", font='data/fonts/menu_font.ttf')

    def draw(self, screen: pygame.Surface):
        screen.blit(self.background, (0, 0))
        self.button_connect.draw(screen, 1)
        self.button_start_server.draw(screen, 1)
        self.button_exit.draw(screen, 1)


class ConnectToServerMenu:
    def __init__(self):
        self.background = load_background('gradient1.png')
        self.button_back = Button(size=(WIDTH // 5, 40),
                                  pos=(10, 10),
                                  text="Back",
                                  event=pygame.event.Event(OPEN_MAIN_MENU_EVENT))
        self.text_input_address = TextInput(size=(WIDTH // 1.1, 25),
                                            pos=((WIDTH - WIDTH // 1.1) // 2, HEIGHT // 2),
                                            hint="server address",
                                            text="localhost:5555",
                                            font='data/fonts/menu_font.ttf')

        self.button_start_game = Button(size=(WIDTH // 5, 40),
                                        pos=(WIDTH - WIDTH // 5 - 10, HEIGHT - 40 - 10),
                                        text="Connect",
                                        event=pygame.event.Event(CONNECT_TO_SERVER_EVENT, ))

    def event_handle(self, event):
        self.text_input_address.event_handle(event)
        self.button_start_game.event.dict['input'] = self.text_input_address.text

    def draw(self, screen: pygame.Surface):
        screen.blit(self.background, (0, 0))
        self.text_input_address.draw(screen, 1)
        self.button_back.draw(screen, 1)
        self.button_start_game.draw(screen, 1)


class StartServerMenu:
    def __init__(self):
        self.background = load_background('gradient1.png')
        self.button_back = Button(size=(WIDTH // 5, 40),
                                  pos=(10, 10),
                                  text="Back",
                                  event=pygame.event.Event(OPEN_MAIN_MENU_EVENT))
        self.text_input_address = TextInput(size=(WIDTH // 1.1, 25),
                                            pos=((WIDTH - WIDTH // 1.1) // 2, HEIGHT // 2),
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


class EndScreen:
    TABCOORD = (int(WIDTH * 0.1), int(HEIGHT * 0.1), int(WIDTH * 0.9), int(HEIGHT * 0.9))
    PLAYERCOORD1 = (int(WIDTH * 0.15), int(HEIGHT * 0.15), int(WIDTH * 0.3), int(HEIGHT * 0.4))
    GAMECOORD = (int(WIDTH * 0.45), int(HEIGHT * 0.15), int(WIDTH * 0.55), int(HEIGHT * 0.75))

    def __init__(self, statistics):
        self.n_players = len(statistics.keys())
        self.player_descr = Template('id:$player_id\nwins:$player_wins\nkills:$player_kills\ndeaths:$player_deaths\nplayer_damage:$player_damage')
        self.table = pygame.Rect(EndScreen.TABCOORD)
        self.player_card1 = pygame.Rect(EndScreen.PLAYERCOORD1)
        self.game_card = pygame.Rect(EndScreen.GAMECOORD)

    def draw(self, screen: pygame.Surface):
        pygame.draw.rect(screen, WHITE, self.table)
        pygame.draw.rect(screen, GRAY, self.player_card1)
        pygame.draw.rect(screen, BLACK, self.game_card)
