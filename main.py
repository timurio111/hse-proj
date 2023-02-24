import pygame
import os
from button import Button

pygame.init()
monitor = pygame.display.get_desktop_sizes()[0]

WIDTH, HEIGHT = monitor
MAX_FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)

EXIT_GAME_EVENT = pygame.event.Event(pygame.QUIT)
START_GAME_EVENT = pygame.event.Event(pygame.USEREVENT + 1)
GO_TO_MENU_EVENT = pygame.event.Event(pygame.USEREVENT + 2)


def load_background(image_name: str) -> pygame.Surface:
    path = os.path.join("data", "Background", image_name)
    image = pygame.transform.scale(pygame.image.load(path), (WIDTH, HEIGHT))
    return image.convert()


def load_image(image_name: str, height_to_monitor_size: float) -> pygame.Surface:  # height_to_monitor_size обозначает, какая высота дожлна быть у элемента относительно высоты окна игры

    image_raw = pygame.image.load(image_name).convert_alpha()
    Koeff = (HEIGHT * height_to_monitor_size * (1 / image_raw.get_height()))
    width = image_raw.get_width() * Koeff // 1
    height = image_raw.get_height() * Koeff // 1

    return pygame.transform.scale(image_raw, [width, height])


class Menu:
    def __init__(self):

        self.visible = True
        self.background = load_background("gradient2.png")
        self.button_start = Button(size=(WIDTH // 4, HEIGHT // 12), pos=(WIDTH // 2 - WIDTH // 8, HEIGHT // 2), event=START_GAME_EVENT, text="Play", font='data/fonts/menu_font.ttf')
        self.button_exit = Button(size=(WIDTH // 4, HEIGHT // 12), pos=(WIDTH // 2 - WIDTH // 8, HEIGHT // 2 + HEIGHT // 6), event=EXIT_GAME_EVENT, text="Quit", font='data/fonts/menu_font.ttf')

    def draw(self, screen):
        screen.blit(self.background, (0, 0))
        self.button_start.draw(screen)
        self.button_exit.draw(screen)


class Player(pygame.sprite.Sprite):

    def __init__(self, pos, size, scale ,dir_for_sprites, *groups):
        super().__init__(*groups)
        self.v = 20
        self.vx = 0
        self.vy = 0
        self.counter = 0

        self.animations = dict()      # Словарь c анимациями
        self.animations_counter = 0   # Анимационный счетчик кадра
        self.frame_number = 0         # Связанный с animations.counter счетчик. Говорит, какой кадр нужно показывать
        self.all_frames = 4           # Сколько кадров для текущего статуса
        self.frames_change_rate = 10  # Через сколько итераций менять кадр
        self.status = 'Idle'          # Текущий статус. Должен совпадать с названием папки с анимацией!!!
        self.direction = 'right'
        self.scale = scale

        for i in os.listdir(dir_for_sprites):     # Подгружаем все анимации и заодно отзеркаливаем их
            self.animations[i + 'right'] = dict()
            self.animations[i + 'left'] = dict()
            for j in os.listdir(dir_for_sprites + '/' + i):
                self.animations[i + 'right'][int(j.split('.')[0]) - 1] = load_image(dir_for_sprites + '/' + i + '/' + j, self.scale)
                self.animations[i + 'left'] [int(j.split('.')[0]) - 1] = pygame.transform.flip(load_image(dir_for_sprites + '/' + i + '/' + j, self.scale), flip_x=True, flip_y=False)

        self.rect = self.animations['Idle' + 'right'][0].get_rect()  #Заполнили словарь с анимациями и взяли примерный прямоугольник персонажа по первому фрейму из Idle

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    def status_to_run(self):
        if self.status != 'Run':
            self.status = 'Run'
            self.frame_number = 1
            self.frames_change_rate = 6
            self.all_frames = 8
            self.animations_counter = 0

    def status_to_jump(self):
        if self.status != 'jump':
            self.status = 'jump'
            self.frame_number = 3
            self.frames_change_rate = 4
            self.all_frames = 11
            self.animations_counter = 0

    def status_to_idle(self):
        if self.status != 'Idle':
            self.status = 'Idle'
            self.frames_change_rate = 12
            self.all_frames = 4
            self.animations_counter = 0
            self.frame_number = 0

    def move_left(self):
        self.direction = 'left'
        self.vx = -self.v
        self.status_to_run()

    def move_right(self):
        self.direction = 'right'
        self.vx = self.v
        self.status_to_run()

    def jump(self):
        if self.counter == 0:
            self.vy = -self.v
            self.status_to_jump()

    def loop(self, fps):
        self.vy += min(3, self.counter / fps * 10)
        if self.rect.y + self.rect.height > HEIGHT and self.vy > 0:
            self.vy = 0
            self.rect.y = HEIGHT - self.rect.height
            self.counter = 0
        else:
            self.counter += 1
        self.move(self.vx, self.vy)

    def draw(self, screen):
        self.animations_counter += 1

        if self.animations_counter == self.frames_change_rate:
            self.frame_number = (self.frame_number + 1) % self.all_frames
            self.animations_counter = 0

        screen.blit(self.animations[self.status + self.direction][self.frame_number], self.rect)


class Game:
    def __init__(self):
        self.visible = True
        self.btn_back = Button((100, 50), (10, 10), "To menu", event=GO_TO_MENU_EVENT, font='data/fonts/menu_font.ttf')
        self.background = load_background("gradient1.png")
        self.player = Player((WIDTH // 2, HEIGHT // 2), (100, 200), 0.1 , 'data/Player_sprites' )

    def draw(self, screen):
        screen.blit(self.background, (0, 0))
        self.player.draw(screen)
        self.btn_back.draw(screen)

    def input_handle(self):
        keys = pygame.key.get_pressed()
        if self.player.vx == 0 and self.player.vy == 0:
            self.player.status_to_idle()
        self.player.vx = 0
        if keys[pygame.K_a]:
            self.player.move_left()
        if keys[pygame.K_d]:
            self.player.move_right()
        if keys[pygame.K_SPACE]:
            self.player.jump()


def main(screen):
    clock = pygame.time.Clock()

    menu = Menu()
    game = Game()

    run = True

    while run:
        clock.tick(MAX_FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                break
            if event == START_GAME_EVENT:
                menu.visible = False
                game.visible = True
            if event == GO_TO_MENU_EVENT:
                menu.visible = True
                game.visible = False
        if menu.visible:
            menu.draw(screen)
        elif game.visible:
            game.player.loop(clock.get_fps())
            game.input_handle()
            game.draw(screen)
        pygame.display.update()
        print(game.player.direction)

    pygame.quit()
    quit(0)


if __name__ == "__main__":
    main(screen)
