import os

import pygame.event

from config import WIDTH, HEIGHT
from event_codes import *
from gui_elements import Button, TextInput, Slider, TextBox
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

        self.button_start_server = Button(size=(WIDTH // 5, 40),
                                          pos=(WIDTH - WIDTH // 5 - 10, HEIGHT - 40 - 10),
                                          text="Start server",
                                          event=pygame.event.Event(START_SERVER_AT_ADDRESS, ))

        self.button_kill_server = Button(size=(WIDTH // 5, 40),
                                         pos=(WIDTH - WIDTH // 5 - self.button_start_server.width - 10, HEIGHT - 40 - 10),
                                         text="Kill server",
                                         event=pygame.event.Event(KILL_SERVER))

    def event_handle(self, event):
        self.text_input_address.event_handle(event)
        self.button_start_server.event.dict['input'] = self.text_input_address.text

    def draw(self, screen: pygame.Surface):
        screen.blit(self.background, (0, 0))
        self.text_input_address.draw(screen, 1)
        self.button_back.draw(screen, 1)
        self.button_start_server.draw(screen, 1)
        self.button_kill_server.draw(screen, 1)


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

        self.return_back = Button(size=(WIDTH // 4.2, HEIGHT // 12),
                                  pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2 + 2 * HEIGHT // 8),
                                  event=pygame.event.Event(OPEN_MAIN_MENU_EVENT),
                                  text="To Menu",
                                  font='data/fonts/menu_font.ttf')
        self.music_textbox = TextBox(size=(WIDTH // 4, HEIGHT // 15),
                                     pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2 - HEIGHT // 8), text='Music volume',
                                     font='data/fonts/menu_font.ttf')
        self.music_slider = Slider(size=(WIDTH // 2.3, HEIGHT // 12),
                                   pos=(WIDTH // 2 - WIDTH // 4.6, HEIGHT // 2 - HEIGHT // 20),
                                   slider_color=(200, 200, 200), bar_color=(50, 50, 100),
                                   event=pygame.event.Event(CHANGE_MUSIC_SLIDER))

        self.sound_textbox = TextBox(size=(WIDTH // 4, HEIGHT // 15),
                                     pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2 + HEIGHT // 18), text='Sound volume',
                                     font='data/fonts/menu_font.ttf')

        self.sound_slider = Slider(size=(WIDTH // 2.3, HEIGHT // 12),
                                   pos=(WIDTH // 2 - WIDTH // 4.6, HEIGHT // 2 + HEIGHT // 8),
                                   slider_color=(200, 200, 200), bar_color=(50, 50, 100),
                                   event=pygame.event.Event(CHANGE_SOUNDS_SLIDER))

        self.music_slider.slider_pos = SoundCore.music_loud
        self.sound_slider.slider_pos = SoundCore.sound_loud

    def buttons_update(self):
        pass

    def draw(self, screen: pygame.Surface):
        screen.blit(self.background, (0, 0))
        self.change_window_mode.draw(screen, 1)
        self.return_back.draw(screen, 1)
        self.music_slider.draw(screen)
        self.music_textbox.draw(screen)
        self.sound_slider.draw(screen)
        self.sound_textbox.draw(screen)

    def event_handle(self, event):
        self.music_slider.event_handle(event)
        self.sound_slider.event_handle(event)


class PauseMenu:
    def __init__(self):
        self.visible = True
        self.background = load_background("settings_menu.png")

        self.label = TextBox(size=(WIDTH // 2, HEIGHT // 8),
                             pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 15),
                             text='Settings',
                             font='data/fonts/menu_font.ttf')

        self.music_off = Button(size=(WIDTH // 2, HEIGHT // 12),
                                pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2 + HEIGHT // 8),
                                event=pygame.event.Event(CHANGE_MUSIC_MODE),
                                text='Music off' if SoundCore.is_music_on else 'Music on',
                                font='data/fonts/menu_font.ttf')


        self.return_back = Button(size=(WIDTH // 4.2, HEIGHT // 12),
                                  pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2 + 2 * HEIGHT // 8),
                                  event=pygame.event.Event(EXIT_GAME_TO_MENU),
                                 text="Leave game",
                                  font='data/fonts/menu_font.ttf')
        self.music_textbox = TextBox(size=(WIDTH // 4, HEIGHT // 15),
                                     pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2 - HEIGHT // 8), text='Music volume',
                                     font='data/fonts/menu_font.ttf')
        self.music_slider = Slider(size=(WIDTH // 2.3, HEIGHT // 12),
                                   pos=(WIDTH // 2 - WIDTH // 4.6, HEIGHT // 2 - HEIGHT // 20),
                                   slider_color=(200, 200, 200), bar_color=(50, 50, 100),
                                   event=pygame.event.Event(CHANGE_MUSIC_SLIDER))

        self.sound_textbox = TextBox(size=(WIDTH // 4, HEIGHT // 15),
                                     pos=(WIDTH // 2 - WIDTH // 4, HEIGHT // 2 + HEIGHT // 18), text='Sound volume',
                                     font='data/fonts/menu_font.ttf')

        self.sound_slider = Slider(size=(WIDTH // 2.3, HEIGHT // 12),
                                   pos=(WIDTH // 2 - WIDTH // 4.6, HEIGHT // 2 + HEIGHT // 8),
                                   slider_color=(200, 200, 200), bar_color=(50, 50, 100),
                                   event=pygame.event.Event(CHANGE_SOUNDS_SLIDER))

        self.music_slider.slider_pos = SoundCore.music_loud
        self.sound_slider.slider_pos = SoundCore.sound_loud

    def buttons_update(self):
        pass

    def draw(self, screen: pygame.Surface):
        background = pygame.Surface((WIDTH // 1.8, HEIGHT), pygame.SRCALPHA)
        background.fill((50, 55, 60, 240))
        screen.blit(background, (WIDTH // 2 - WIDTH // 3.6, 0))
        self.label.draw(screen)
        self.return_back.draw(screen, 1)
        self.music_slider.draw(screen)
        self.music_textbox.draw(screen)
        self.sound_slider.draw(screen)
        self.sound_textbox.draw(screen)

    def event_handle(self, event):
        self.music_slider.event_handle(event)
        self.sound_slider.event_handle(event)



LISTOFCOORDS = ((WIDTH * 0.07, HEIGHT * 0.07), (WIDTH * 0.53, HEIGHT * 0.07), (WIDTH * 0.07, HEIGHT * 0.51), (WIDTH * 0.53, HEIGHT * 0.51))


class TextBlock:
    STEP = HEIGHT // 12

    def __init__(self, statistics, color, text='win:\nkill:\ndeath:\ndamage'):
        self.text = text.split(':\n')
        self.game_data = statistics
        self.color = color
        self.text_block = []
        self.font = pygame.font.Font('data/fonts/menu_font.ttf', TextBlock.STEP)

    def get_text_player(self, player_id):
        for i in range(len(self.text)):
            if self.text[i] != 'damage':
                self.text[i] += 's : ' + str(self.game_data[player_id][self.text[i]])
            else:
                self.text[i] += ' : ' + str(self.game_data[player_id][self.text[i]])
            param = self.font.render(self.text[i], False, tuple([int(i * 0.6) for i in self.color]))
            self.text_block.append(param)
        return self.text_block

    def draw(self, screen, player_id, coords):
        block = self.get_text_player(player_id)
        for i in range(len(block)):
            line = block[i]
            screen.blit(line, (coords[0] + 10, coords[1] + i * TextBlock.STEP))


class PlayerCard:
    CARDSIZE = (0.4 * WIDTH, 0.35 * HEIGHT)

    def __init__(self, coords, statistics, player_id, winner_id, color):
        self.coords = coords
        self.player_card = pygame.Rect(coords + PlayerCard.CARDSIZE)
        self.player_id = player_id
        self.text = TextBlock(statistics, color)
        self.color = color
        self.b_winner = (winner_id == int(player_id))

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.player_card)
        if self.b_winner:
            pygame.draw.rect(screen, YELLOW, self.player_card, 10)
        self.text.draw(screen, self.player_id, self.coords)


class EndScreen:
    TABCOORD = (WIDTH * 0.05, HEIGHT * 0.05, WIDTH * 0.90, HEIGHT * 0.90)
    GAMECOORD = (WIDTH * 0.37, HEIGHT * 0.07, WIDTH * 0.26, HEIGHT * 0.80)

    def __init__(self, statistics):
        self.background = load_background('settings_menu.png')
        self.n_players = len(statistics.keys())
        self.statistics = statistics['statistics']
        self.colors = statistics['colors']
        self.winner_id = statistics['winner']
        self.table = pygame.Rect(EndScreen.TABCOORD)
        self.game_card = pygame.Rect(EndScreen.GAMECOORD)
        self.button_back = Button(size=(WIDTH // 5, 30),
                                  pos=(WIDTH - WIDTH // 5 - 10, HEIGHT - 40),
                                  text="Menu",
                                  event=pygame.event.Event(OPEN_MAIN_MENU_EVENT))

    def draw(self, screen: pygame.Surface):
        screen.blit(self.background, (0, 0))
        for coord, player_id in enumerate(self.statistics.keys()):
            player_card = PlayerCard(LISTOFCOORDS[coord], self.statistics, player_id, self.winner_id, self.colors[player_id])
            player_card.draw(screen)
        self.button_back.draw(screen, 1)
