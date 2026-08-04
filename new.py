import random, time, pygame
from server import GameServer
from paths import resource_path

players = {}
field = []
ammo_positions = []
server = None
host_name = ""
host_color = "red"
host_join_code = ""

pygame.init()

screen = pygame.display.set_mode((0, 0))

running = True
fps = 60
width, height = screen.get_size()
frames = 0
color = 0
colors = ["red", "orange", "yellow", "green", "blue", "purple", "pink"]

font = pygame.font.Font(resource_path("tanks", "fonts", "PressStart2P-Regular.ttf"), 20)

images = {}
for number in range(1, 4):
    image = pygame.image.load(resource_path("tanks", "images", "tread" + str(number) + ".png")).convert_alpha()
    images["tread" + str(number)] = pygame.transform.scale(image, (80, 80))

for color_name in colors:
    image = pygame.image.load(resource_path("tanks", "images", color_name + "body.png")).convert_alpha()
    images[color_name] = pygame.transform.scale(image, (106, 160))

left = pygame.image.load(resource_path("tanks", "images", "left.png")).convert_alpha()
left = pygame.transform.scale(left, (80, 80))
right = pygame.image.load(resource_path("tanks", "images", "right.png")).convert_alpha()
right = pygame.transform.scale(right, (80, 80))
play = pygame.image.load(resource_path("tanks", "images", "play.png")).convert_alpha()
play = pygame.transform.scale(play, (90, 80))

username_rect = pygame.Rect((width//2) - 205, (height//2) + 200, 410, 30)
text = "PLAYER" + str(random.randint(1111, 9999))
active = False
mousedown = False

while running:
    clicked = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked = True
            active = username_rect.collidepoint(event.pos)

        if event.type == pygame.KEYDOWN and active:
            if event.key == pygame.K_BACKSPACE:
                text = text[:-1]
            elif event.key != pygame.K_RETURN and len(text) < 20:
                text += event.unicode

    screen.fill((50, 50, 50))

    input_color = (255, 255, 255) if active else (150, 150, 150)
    pygame.draw.rect(screen, input_color, username_rect, 2)
    text_surface = font.render(text, True, (255, 255, 255))
    screen.blit(text_surface, (username_rect.x + 5, username_rect.y + 5))
    text_surface = font.render("Enter Nickname", True, (255, 255, 255))
    screen.blit(text_surface, (username_rect.x + 60, username_rect.y - 50))

    x, y = pygame.mouse.get_pos()

    tread_name = "tread" + str(round(frames/20) % 3 + 1)
    screen.blit(images[tread_name], ((width//2) - 40, (height//2) - 40))

    left_rect = pygame.Rect((width//2) - 180, (height//2) - 40, 80, 80)
    right_rect = pygame.Rect((width//2) + 100, (height//2) - 40, 80, 80)
    play_rect = pygame.Rect((width//2) - 45, (height//2) + 300, 90, 80)

    screen.blit(left, left_rect)
    screen.blit(right, right_rect)
    screen.blit(play, play_rect)

    if clicked:
        if left_rect.collidepoint(x, y):
            color = (color - 1) % 7
        if right_rect.collidepoint(x, y):
            color = (color + 1) % 7
        if play_rect.collidepoint(x, y):
            server = GameServer()
            server.start()
            time.sleep(0.2)
            host_name = text or "PLAYER"
            host_color = colors[color]
            host_join_code = server.join_code
            field = server.field
            ammo_positions = server.ammo_positions
            running = False
            import play_host

    body = images[colors[color]]
    body_rect = body.get_rect(center=(width // 2, height // 2))
    screen.blit(body, body_rect)

    pygame.display.flip()
    frames += 1
    time.sleep(1/fps)
