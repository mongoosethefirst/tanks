import json, math, socket, threading, time
import pygame
from network import send_json
from paths import resource_path

class GameClient:
    def __init__(self, host, port, code, name, color):
        self.host, self.port, self.code, self.name, self.color = host, port, code.upper(), name, color
        self.sock = None
        self.running = False
        self.player_id = None
        self.state = {}
        self.lock = threading.Lock()
        self.error = ''
        self.last_shot = 0

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        send_json(self.sock, {'type':'join','join_code':self.code,'name':self.name,'color':self.color})
        self.running = True
        threading.Thread(target=self.receive_loop, daemon=True).start()
        end = time.time() + 5
        while time.time() < end and self.player_id is None and not self.error:
            time.sleep(.01)
        if self.error: raise ConnectionError(self.error)
        if self.player_id is None: raise TimeoutError('Server did not respond')

    def receive_loop(self):
        buffer = ''
        try:
            while self.running:
                data = self.sock.recv(65536)
                if not data: raise ConnectionError
                buffer += data.decode()
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if not line.strip(): continue
                    msg = json.loads(line)
                    if msg.get('type') == 'welcome': self.player_id = msg['player_id']
                    elif msg.get('type') == 'state':
                        with self.lock: self.state = msg
                    elif msg.get('type') == 'error': self.error = msg.get('message','Connection error'); self.running = False
        except Exception:
            if self.running: self.error = 'Connection lost'
            self.running = False

    def load(self, name, size):
        return pygame.transform.scale(pygame.image.load(resource_path("tanks", "images", name)).convert_alpha(), size)

    def blit_body(self, screen, image, pos, angle):
        rotated = pygame.transform.rotate(image, angle)
        offset = (pygame.Vector2(image.get_rect().center) - (53,80)).rotate(-angle)
        screen.blit(rotated, rotated.get_rect(center=pygame.Vector2(pos)+offset))

    def txt(self, screen, font, value, pos, color=(240,240,240), anchor='topleft'):
        surf = font.render(str(value), True, color)
        rect = surf.get_rect(); setattr(rect, anchor, pos); screen.blit(surf, rect); return rect

    def run(self):
        pygame.init(); screen = pygame.display.set_mode((0,0)); width,height = screen.get_size(); clock = pygame.time.Clock()
        font = pygame.font.Font(resource_path("tanks", "fonts", "PressStart2P-Regular.ttf"), 16)
        small = pygame.font.Font(resource_path("tanks", "fonts", "PressStart2P-Regular.ttf"), 11)
        title = pygame.font.Font(resource_path("tanks", "fonts", "PressStart2P-Regular.ttf"), 40)
        images = {f'tread{i}':self.load(f'tread{i}.png',(80,80)) for i in range(1,4)}
        for c in ['red','orange','yellow','green','blue','purple','pink']: images[c] = self.load(c+'body.png',(106,160))
        for i in range(1,5): images[f'grass{i}'] = self.load(f'grass{i}.png',(100,100))
        images['edge']=self.load('edge.png',(100,100)); images['corner']=self.load('corner.png',(100,100))
        images['bullet']=self.load('bullet.png',(10,16)); images['ammo']=self.load('ammo_box.png',(60,30))
        overlay = pygame.Surface((width,height), pygame.SRCALPHA)
        field_surface = None; field_text = None; input_timer = 0

        while self.running:
            dt = clock.tick(60)/1000; clicked=False; mouse=pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT: self.running=False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: clicked=True
            with self.lock: state = dict(self.state)
            players = {p['id']:p for p in state.get('players',[])}; you = players.get(self.player_id)
            if not you:
                screen.fill((50,50,50)); self.txt(screen,font,'CONNECTING...', (width//2,height//2), anchor='center'); pygame.display.flip(); continue
            field = state.get('field',[]); key = str(field)
            if field and key != field_text:
                field_surface = pygame.Surface((len(field[0])*100,len(field)*100),pygame.SRCALPHA)
                for r,row in enumerate(field):
                    for c,(name,rot) in enumerate(row): field_surface.blit(pygame.transform.rotate(images[name],-rot*90),(c*100,r*100))
                field_text = key
            cx,cy = you['x'],you['y']; target = pygame.Vector2(0,-1).angle_to((width//2-mouse[0],mouse[1]-height//2)); keys=pygame.key.get_pressed(); over=state.get('match_over',False)
            input_timer += dt
            if input_timer >= 1/30 and not over:
                send_json(self.sock, {'type':'input','left':keys[pygame.K_a],'right':keys[pygame.K_d],'forward':keys[pygame.K_w],'backward':keys[pygame.K_s],'aim':target}); input_timer=0
            if clicked and you['alive'] and not over and time.time()-self.last_shot >= .5:
                send_json(self.sock, {'type':'shoot'}); self.last_shot=time.time()
            screen.fill((50,50,50))
            if field_surface: screen.blit(field_surface,(width//2-150-cx*100,height//2-150-cy*100))
            for a in state.get('ammo_positions',[]): screen.blit(images['ammo'],images['ammo'].get_rect(center=((a[0]-cx)*100+width//2,(a[1]-cy)*100+height//2)))
            for b in state.get('bullets',[]):
                img=pygame.transform.rotate(images['bullet'],b['direction']); screen.blit(img,img.get_rect(center=((b['x']-cx)*100+width//2,(b['y']-cy)*100+height//2)))
            for p in players.values():
                if not p['alive']: continue
                px=(p['x']-cx)*100+width//2; py=(p['y']-cy)*100+height//2
                tread=pygame.transform.rotate(images['tread'+str(int(p.get('tread_frame',0))%3+1)],p['tread_rot']); screen.blit(tread,tread.get_rect(center=(px,py)))
                self.blit_body(screen,images[p['color']],(px,py),p['head_rot'])
                self.txt(screen,small,p['name'],(px,py+58),(100,200,255) if p['team']==you['team'] else (255,120,120),'midtop')
            pygame.draw.rect(screen,(20,20,20),(15,15,310,112)); pygame.draw.rect(screen,(220,220,220),(15,15,310,112),2)
            self.txt(screen,font,'HEALTH: '+str(you['health']),(30,28)); self.txt(screen,font,'YOUR AMMO: '+str(you['ammo']),(30,58)); self.txt(screen,font,'TEAM AMMO: '+str(state.get('team_ammo',0)),(30,88))
            self.txt(screen,small,'JOIN CODE: '+state.get('join_code',''),(width//2,18),anchor='midtop')
            chat=pygame.Rect(width-490,height-190,470,170); pygame.draw.rect(screen,(20,20,20),chat); pygame.draw.rect(screen,(220,220,220),chat,2); self.txt(screen,small,'GAME CHAT',(chat.x+12,chat.y+10))
            for i,m in enumerate(state.get('chat',[])[-7:]): self.txt(screen,small,m,(chat.x+12,chat.y+35+i*18))
            alpha=max(0,min(100,int(100*(1-you['health']/100)))); overlay.fill((255,0,0,alpha)); screen.blit(overlay,(0,0))
            if not you['alive'] and not over:
                self.txt(screen,title,'YOU DIED!',(width//2,height//2-90),anchor='center'); rect=pygame.Rect(width//2-170,height//2+45,340,52)
                pygame.draw.rect(screen,(100,100,100) if rect.collidepoint(mouse) else (70,70,70),rect); pygame.draw.rect(screen,(230,230,230),rect,2); self.txt(screen,font,'RESPAWN',rect.center,anchor='center')
                if clicked and rect.collidepoint(mouse): send_json(self.sock,{'type':'respawn'})
            if over:
                shade=pygame.Surface((width,height),pygame.SRCALPHA); shade.fill((0,0,0,210)); screen.blit(shade,(0,0)); winner=state.get('winner')
                heading='DRAW!' if winner==-1 else ('YOUR TEAM WON!' if winner==you['team'] else 'YOUR TEAM LOST!'); self.txt(screen,title,heading,(width//2,65),anchor='midtop'); self.txt(screen,font,'RANKED BY KILLS - DEATHS',(width//2,130),anchor='midtop')
                rows=state.get('rankings',[]); x=width//2-360; y=175; pygame.draw.rect(screen,(30,30,30),(x,y,720,50+30*max(1,len(rows)))); pygame.draw.rect(screen,(220,220,220),(x,y,720,50+30*max(1,len(rows))),2)
                for label,off in [('RANK',15),('PLAYER',105),('TEAM',390),('KILLS',500),('DEATHS',590),('DIFF',685)]: self.txt(screen,small,label,(x+off,y+15),anchor='midtop')
                for i,row in enumerate(rows):
                    yy=y+50+i*30
                    for val,off in [(i+1,15),(row['name'],105),(row['team']+1,390),(row['kills'],500),(row['deaths'],590),(row['difference'],685)]: self.txt(screen,small,val,(x+off,yy))
                exit_rect=pygame.Rect(width-220,height-80,190,50); pygame.draw.rect(screen,(105,105,105) if exit_rect.collidepoint(mouse) else (70,70,70),exit_rect); pygame.draw.rect(screen,(230,230,230),exit_rect,2); self.txt(screen,font,'EXIT',exit_rect.center,anchor='center')
                if clicked and exit_rect.collidepoint(mouse): self.running=False
            pygame.display.flip()
        try: self.sock.close()
        except OSError: pass
        pygame.quit()
