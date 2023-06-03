import pygame


class Button:
    def __init__(self, size, pos, text="", border_width=2, event=None):
        self.event = event
        self.border_width = border_width
        self.hover = False
        self.pressed = False

        self.width = size[0]
        self.height = size[1]

        self.x = pos[0]
        self.y = pos[1]

        self.text = text
        self.image_default = self.__get_image((200, 200, 200))
        self.image_hover = self.__get_image((180, 180, 180))
        self.image_pressed = self.__get_image((150, 150, 150))
        self.rect = pygame.Rect(pos, size)

    def __get_image(self, color) -> pygame.Surface:
        frame = pygame.Surface((self.width, self.height))
        frame.fill((50, 50, 50))
        temp = pygame.Surface((self.width - 2 * self.border_width, self.height - 2 * self.border_width))
        temp.fill(color)
        frame.blit(temp, (self.border_width, self.border_width))
        font = pygame.font.Font(None, frame.get_height())
        text_surf = font.render(self.text, True, (0, 0, 0))
        factor = 0.9 / max(text_surf.get_width() / self.width, text_surf.get_height() / self.height)
        text_surf = pygame.transform.scale_by(text_surf, factor)
        frame.blit(text_surf, (self.width // 2 - text_surf.get_width() // 2,
                               self.height // 2 - text_surf.get_height() // 2))
        return frame

    def draw(self, screen: pygame.Surface):
        self.update()
        if self.pressed:
            image = self.image_pressed
        elif self.hover:
            image = self.image_hover
        else:
            image = self.image_default
        screen.blit(image, (self.x, self.y))

    def update(self):
        mouse_pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_pos):
            self.hover = True
            if pygame.mouse.get_pressed()[0]:
                self.pressed = True
            else:
                if self.pressed:
                    if self.event is not None:
                        pygame.event.post(self.event)
                self.pressed = False
        else:
            self.pressed = False
            self.hover = False
