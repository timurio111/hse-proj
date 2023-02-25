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


def load_character_sprites(name: str, scale: int, size: (int, int)) -> dict[str, list[pygame.surface.Surface]]:
    path = os.path.join("data", "PlayerSprites", name)
    sprites_dict: dict[str, list[pygame.surface.Surface]] = dict()

    for filename in os.listdir(path):
        state = filename.replace('.png', '')
        sprites_dict[state + "_right"] = []
        sprites_dict[state + "_left"] = []

        sprite_sheet = pygame.image.load(os.path.join(path, filename))

        sprites_count = sprite_sheet.get_width() // size[0]
        for i in range(sprites_count):
            sprite = sprite_sheet.subsurface((size[0] * i, 0), size)
            sprite = pygame.transform.scale(sprite, (size[0] * scale, size[1] * scale))

            sprites_dict[state + "_right"].append(sprite)
            sprites_dict[state + "_left"].append(pygame.transform.flip(sprite, True, False))

    return sprites_dict


def load_background(image_name: str) -> pygame.Surface:
    path = os.path.join("data", "Background", image_name)
    image = pygame.transform.scale(pygame.image.load(path), (WIDTH, HEIGHT))
    return image.convert()


class Menu:
    def __init__(self):
        self.visible = True
        self.background = load_background("gradient2.png")
        self.button_start = Button(size=(WIDTH // 4, HEIGHT // 12), pos=(WIDTH // 2 - WIDTH // 8, HEIGHT // 2),
                                   event=START_GAME_EVENT, text="Play", font='data/fonts/menu_font.ttf')
        self.button_exit = Button(size=(WIDTH // 4, HEIGHT // 12),
                                  pos=(WIDTH // 2 - WIDTH // 8, HEIGHT // 2 + HEIGHT // 6), event=EXIT_GAME_EVENT,
                                  text="Quit", font='data/fonts/menu_font.ttf')

    def draw(self, screen):
        screen.blit(self.background, (0, 0))
        self.button_start.draw(screen)
        self.button_exit.draw(screen)


class Player(pygame.sprite.Sprite):

    def __init__(self, pos, size, scale):
        super().__init__()
        self.sprite: pygame.Surface = None
        self.mask: pygame.Mask = None
        self.rect: pygame.Rect = pygame.rect.Rect(pos, (size[0] * scale, size[1] * scale))
        self.v = 5
        self.vx = 0
        self.vy = 0
        self.off_ground_counter = 0
        self.animations = load_character_sprites("Character", scale, size)
        self.animations_counter = 0
        self.frames_change_rate = 3
        self.status = 'idle'
        self.direction = 'right'
        self.sprite_animation_counter = 0

    def move(self, dx, dy):
        self.rect.x += dx
        self.rect.y += dy

    def update_sprite(self):
        status = 'idle'

        if self.vy < 0:
            status = 'jump'
        elif self.vy > 2:
            status = 'fall'
        elif self.vx != 0:
            status = 'run'
        sprite_name = status + '_' + self.direction
        sprite_index = (self.sprite_animation_counter // self.frames_change_rate) % len(self.animations[sprite_name])
        self.sprite = self.animations[sprite_name][sprite_index]
        self.mask = pygame.mask.from_surface(self.sprite)
        self.sprite_animation_counter += 1
        self.move(self.vx, self.vy)

    def move_left(self):
        self.direction = 'left'
        self.vx = -self.v

    def move_right(self):
        self.direction = 'right'
        self.vx = self.v

    def jump(self):
        if self.off_ground_counter < 2:
            self.vy = -self.v * 2

    def touch_down(self):
        self.off_ground_counter = 0
        self.vy = 0

    def loop(self, fps):
        self.move(self.vx, self.vy)
        self.vy += min(1, self.off_ground_counter / fps * 10)
        self.off_ground_counter += 1
        self.update_sprite()

    def draw(self, screen):
        screen.blit(self.sprite, self.rect)


class Obstacle(pygame.sprite.Sprite):
    def __init__(self, pos: (int, int), size: (int, int)):
        super().__init__()
        self.rect = pygame.Rect(*pos, *size)
        self.image = pygame.Surface(size)
        self.image.fill((50, 50, 100))
        self.mask = pygame.mask.from_surface(self.image)

    def draw(self, screen):
        screen.blit(self.image, self.rect)

lJ
class Game:
    def __init__(self):
        self.visible = True
        self.btn_back = Button((100, 50), (10, 10), "To menu", event=GO_TO_MENU_EVENT, font='data/fonts/menu_font.ttf')
        self.background = load_background("gradient1.png")
        self.player = Player((WIDTH // 2, HEIGHT // 2), (120, 80), 4)
        self.obstacles = [Obstacle((0, HEIGHT - 100), (WIDTH, 100)),
                          Obstacle((100, HEIGHT - 150), (WIDTH // 2, 300)),
                          Obstacle((100, HEIGHT - 200), (WIDTH // 3, 100))]

    def draw(self, screen):
        screen.blit(self.background, (0, 0))
        for obstacle in self.obstacles:
            obstacle.draw(screen)
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

        self.collision_y()

    def collision_x(self):
        pass

    def collision_y(self):
        for obstacle in self.obstacles:
            if pygame.sprite.collide_mask(self.player, obstacle):
                if self.player.vy >= 0:
                    self.player.rect.bottom = obstacle.rect.top
                    self.player.touch_down()


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
