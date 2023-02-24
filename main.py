import pygame
import os
from button import Button

pygame.init()
WIDTH, HEIGHT = 1000, 800
MAX_FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))

EXIT_GAME_EVENT = pygame.event.Event(pygame.QUIT)
START_GAME_EVENT = pygame.event.Event(pygame.USEREVENT + 1)
GO_TO_MENU_EVENT = pygame.event.Event(pygame.USEREVENT + 2)


def load_background(image_name: str) -> pygame.Surface:
    path = os.path.join("data", "Background", image_name)
    image = pygame.transform.scale(pygame.image.load(path), (WIDTH, HEIGHT))
    return image


class Menu:
    def __init__(self):
        self.visible = True
        self.background = load_background("gradient2.png")
        self.button_start = Button(size=(WIDTH // 3, WIDTH // 6),
                                   pos=(WIDTH // 2 - WIDTH // 6, HEIGHT // 2),
                                   event=START_GAME_EVENT,
                                   text="Start")
        self.button_exit = Button(size=(WIDTH // 3, WIDTH // 6),
                                  pos=(WIDTH // 2 - WIDTH // 6, HEIGHT // 2 + WIDTH // 6 + 10),
                                  event=EXIT_GAME_EVENT,
                                  text="Quit")

    def draw(self, screen):
        screen.blit(self.background, (0, 0))
        self.button_start.draw(screen)
        self.button_exit.draw(screen)


class Player(pygame.sprite.Sprite):

    def __init__(self, pos, size, *groups):
        super().__init__(*groups)
        self.rect = pygame.rect.Rect(pos, size)
        self.v = 20
        self.vx = 0
        self.vy = 0
        self.counter = 0

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    def move_left(self):
        self.vx = -self.v

    def move_right(self):
        self.vx = self.v

    def jump(self):
        if self.counter == 0:
            self.vy = -self.v

    def loop(self, fps):
        self.vy += min(1, self.counter / fps * 20)
        if self.rect.y + self.rect.height >= HEIGHT and self.vy > 0:
            self.vy = 0
            self.counter = 0
        else:
            self.counter += 1
        self.move(self.vx, self.vy)

    def draw(self, screen):
        pygame.draw.rect(screen, (255, 255, 255), self.rect)


class Game:
    def __init__(self):
        self.visible = True
        self.btn_back = Button((100, 50), (10, 10), "To menu", event=GO_TO_MENU_EVENT)
        self.background = load_background("gradient1.png")
        self.player = Player((WIDTH // 2, HEIGHT // 2), (100, 200))

    def draw(self, screen):
        screen.blit(self.background, (0, 0))
        self.player.draw(screen)
        self.btn_back.draw(screen)

    def input_handle(self):
        keys = pygame.key.get_pressed()

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
    pygame.quit()
    quit(0)


if __name__ == "__main__":
    main(screen)
