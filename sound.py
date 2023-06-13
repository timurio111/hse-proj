import os

import pygame

'''Как добавлять новые системные звуки:
  1) Добавляем в список статических констант класса SoundCore название звука.
      (Предварительно убедитесь, что Ваш звук расположен в data/Sounds)
  2) Инициализируем звук в __init__ в классе SoundCore.
      2.1) self.sounds['']
  3) В любом нужном месте используем метод .sound_play()

Как добавлять новую музыку:
  1) Добавляем в список статических констант класса SoundCore название музыки.
      (Предварительно убедитесь, что Ваша музыка расположена в data/Music)
  2) Потом используем в любом нужном месте метод SoundCore.music_play([Ваша константа])

Как добавлять новые звуки для оружия:
    1) Убедитесь, что Ваш звук расположен в data/WeaponSprites/[название оружия]/sound
    2) 
    
  '''

try:
    pygame.mixer.init()
except Exception as e:
    print(e, '<-Sound Error')


def load_weapon_sound(name, new_names_of_sound=[]):  # передаем название папки с оружием, на выходе - три звука: перезарядка, выстрел, холостой выстрел
    path = os.path.join('data', 'WeaponSprites', name, 'sound')
    all_sounds = ['is_empty', 'shot', 'reload'] + new_names_of_sound
    result = {}

    for sound_name in all_sounds:
        try:
            result[sound_name] = Sound(os.path.join(path, sound_name + '.mp3'), is_custom=True)
        except Exception as e:
            print(e, '<- sound path error')
            result[sound_name] = None

    return result


class Sound:
    def __init__(self, name, is_custom=False):
        self.sound = None
        if not pygame.mixer.get_init():
            return
        if is_custom:
            self.sound = pygame.mixer.Sound(name)
        else:
            self.sound = pygame.mixer.Sound(os.path.join('data', 'Sounds', name + '.mp3'))

    def sound_play(self):
        if pygame.mixer.get_init() and SoundCore.is_sound_on:
            self.sound.set_volume(SoundCore.sound_loud)
            self.sound.play()


class Music:
    def __init__(self, name):
        self.path = os.path.join('data', 'Music', name + '.mp3')
        self.name = name

    def music_play(self):
        if pygame.mixer.get_init() and SoundCore.is_music_on:
            SoundCore.current_music = self.name
            pygame.mixer.music.load(self.path)
            pygame.mixer.music.play(-1)


class SoundCore:
    is_sound_on = True if pygame.mixer.get_init() else False
    is_music_on = True if pygame.mixer.get_init() else False
    current_music = ''

    music_loud = 0.3
    sound_loud = 0.75

    # Музыка
    MAIN_MENU_MUSIC = 'menu_theme'
    SERVER_CONNECTION_MUSIC = 'server_connection_menu_theme'
    IN_GAME_MUSIC = 'in_game_theme'

    # Звуки
    MENU_BUTTON_IS_HOVER = 'is_hover'
    MENU_BUTTON_IS_PRESSED = 'is_pressed'

    # инициализированная музыка
    main_menu_music = Music(MAIN_MENU_MUSIC)
    server_connection_music = Music(SERVER_CONNECTION_MUSIC)
    in_game_music = Music(IN_GAME_MUSIC)

    # инициализированные звуки
    menu_button_is_hover = Sound(MENU_BUTTON_IS_HOVER)
    menu_button_is_pressed = Sound(MENU_BUTTON_IS_PRESSED)

    @staticmethod
    def sound_off():
        SoundCore.is_sound_on = False

    @staticmethod
    def sound_on():
        SoundCore.is_sound_on = True

    @staticmethod
    def music_off():
        SoundCore.is_music_on = False
        pygame.mixer.music.pause()

    @staticmethod
    def music_on():
        SoundCore.is_music_on = True

    @staticmethod
    def change_music_loud(value):
        SoundCore.music_loud = value
        pygame.mixer.music.set_volume(SoundCore.music_loud)

    @staticmethod
    def change_sounds_loud(value):
        SoundCore.sound_loud = value
