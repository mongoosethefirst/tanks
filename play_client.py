import pygame
from game_client_base import GameClient
from join import join_address, join_code, join_name, join_color

client = GameClient(join_address[0], join_address[1], join_code, join_name, join_color)

try:
    client.connect()
    client.run()
finally:
    pygame.quit()
