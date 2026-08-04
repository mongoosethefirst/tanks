import random, time, pygame
from network import discover_host
from paths import resource_path

join_address = None
join_code = ""
join_name = ""
join_color = "red"

pygame.init()

screen = pygame.display.set_mode((0, 0))
running = True
fps = 60
width, height = screen.get_size()
colors = ["red", "orange", "yellow", "green", "blue", "purple", "pink"]
color = 0
font = pygame.font.Font(resource_path("tanks", "fonts", "PressStart2P-Regular.ttf"), 20)
small_font = pygame.font.Font(resource_path("tanks", "fonts", "PressStart2P-Regular.ttf"), 12)
name = "PLAYER" + str(random.randint(1111, 9999))
code = ""
active = "name"
status = ""

while running:
    clicked = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            clicked = True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                active = "code" if active == "name" else "name"
            elif event.key == pygame.K_BACKSPACE:
                if active == "name":
                    name = name[:-1]
                else:
                    code = code[:-1]
            elif event.key != pygame.K_RETURN:
                if active == "name" and len(name) < 20:
                    name += event.unicode
                elif active == "code" and len(code) < 6 and event.unicode.isalnum():
                    code += event.unicode.upper()

    screen.fill((50, 50, 50))
    mouse_x, mouse_y = pygame.mouse.get_pos()

    name_rect = pygame.Rect(width//2 - 205, height//2 - 150, 410, 35)
    code_rect = pygame.Rect(width//2 - 205, height//2 - 70, 410, 35)
    left_rect = pygame.Rect(width//2 - 180, height//2 + 20, 80, 60)
    right_rect = pygame.Rect(width//2 + 100, height//2 + 20, 80, 60)
    join_rect = pygame.Rect(width//2 - 100, height//2 + 150, 200, 55)

    pygame.draw.rect(screen, (255,255,255) if active == "name" else (150,150,150), name_rect, 2)
    pygame.draw.rect(screen, (255,255,255) if active == "code" else (150,150,150), code_rect, 2)
    screen.blit(font.render(name, True, (255,255,255)), (name_rect.x + 5, name_rect.y + 8))
    screen.blit(font.render(code or "------", True, (255,255,255)), (code_rect.x + 5, code_rect.y + 8))
    screen.blit(small_font.render("NICKNAME", True, (255,255,255)), (name_rect.x, name_rect.y - 23))
    screen.blit(small_font.render("JOIN CODE", True, (255,255,255)), (code_rect.x, code_rect.y - 23))

    pygame.draw.rect(screen, (80,80,80), left_rect)
    pygame.draw.rect(screen, (80,80,80), right_rect)
    pygame.draw.rect(screen, (80,80,80), join_rect)
    pygame.draw.rect(screen, (220,220,220), left_rect, 2)
    pygame.draw.rect(screen, (220,220,220), right_rect, 2)
    pygame.draw.rect(screen, (220,220,220), join_rect, 2)
    screen.blit(font.render("<", True, (255,255,255)), font.render("<", True, (255,255,255)).get_rect(center=left_rect.center))
    screen.blit(font.render(">", True, (255,255,255)), font.render(">", True, (255,255,255)).get_rect(center=right_rect.center))
    color_text = font.render(colors[color].upper(), True, (255,255,255))
    screen.blit(color_text, color_text.get_rect(center=(width//2, height//2 + 50)))
    join_text = font.render("JOIN", True, (255,255,255))
    screen.blit(join_text, join_text.get_rect(center=join_rect.center))

    if clicked:
        if name_rect.collidepoint(mouse_x, mouse_y):
            active = "name"
        elif code_rect.collidepoint(mouse_x, mouse_y):
            active = "code"
        elif left_rect.collidepoint(mouse_x, mouse_y):
            color = (color - 1) % len(colors)
        elif right_rect.collidepoint(mouse_x, mouse_y):
            color = (color + 1) % len(colors)
        elif join_rect.collidepoint(mouse_x, mouse_y):
            if len(code) != 6:
                status = "Enter a 6-character code"
            else:
                status = "Searching..."
                pygame.display.flip()
                found = discover_host(code)
                if found:
                    join_address = found
                    join_code = code
                    join_name = name or "PLAYER"
                    join_color = colors[color]
                    running = False
                    import play_client
                else:
                    status = "Game not found"

    status_surface = small_font.render(status, True, (255,180,120))
    screen.blit(status_surface, status_surface.get_rect(center=(width//2, height//2 + 245)))
    pygame.display.flip()
    time.sleep(1/fps)
