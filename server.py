import json
import math
import random
import socket
import string
import threading
import time

from network import TCP_PORT, DISCOVERY_PORT, MAX_PLAYERS, MAX_TEAM_PLAYERS, TICK_RATE, STATE_RATE, send_json

class GameServer:
    def __init__(self, host="0.0.0.0", port=TCP_PORT):
        self.host = host
        self.port = port
        self.join_code = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        self.players = {}
        self.clients = {}
        self.inputs = {}
        self.bullets = []
        self.field = []
        self.ammo_positions = []
        self.chat = []
        self.next_player_id = 0
        self.next_bullet_id = 0
        self.running = False
        self.match_over = False
        self.winner = None
        self.lock = threading.RLock()
        self.server_socket = None
        self.create_field()

    def create_field(self):
        self.field = []
        self.ammo_positions = []
        line = [["corner", 0]] + [["edge", 1] for _ in range(20)] + [["corner", 1]]
        self.field.append(line)

        for y in range(20):
            line = [["edge", 0]]

            for x in range(20):
                line.append(["grass" + str(random.randint(1, 4)), random.randint(0, 3)])

                if random.randint(1, 45) == 1:
                    self.ammo_positions.append([x, y, 10])

            line.append(["edge", 2])
            self.field.append(line)

        self.field.append([["corner", 3]] + [["edge", 3] for _ in range(20)] + [["corner", 2]])

    def add_chat(self, message):
        self.chat.append(message)
        self.chat = self.chat[-8:]

    def choose_team(self):
        counts = [sum(1 for p in self.players.values() if p["team"] == team) for team in (0, 1)]

        if counts[0] >= MAX_TEAM_PLAYERS and counts[1] >= MAX_TEAM_PLAYERS:
            return None
        if counts[0] >= MAX_TEAM_PLAYERS:
            return 1
        if counts[1] >= MAX_TEAM_PLAYERS:
            return 0
        return 0 if counts[0] <= counts[1] else 1

    def spawn_for(self, player_id, team):
        slot = sum(1 for p in self.players.values() if p["team"] == team and p["id"] < player_id)
        return 6.0 + slot, 0.8 if team == 0 else 18.2, 180 if team == 0 else 0

    def add_player(self, name, color):
        with self.lock:
            if len(self.players) >= MAX_PLAYERS or self.match_over:
                return None

            team = self.choose_team()

            if team is None:
                return None

            player_id = self.next_player_id
            self.next_player_id += 1
            x, y, rot = self.spawn_for(player_id, team)
            self.players[player_id] = {
                "id": player_id,
                "name": (name.strip() or "PLAYER")[:20],
                "color": color,
                "team": team,
                "x": x,
                "y": y,
                "tread_rot": rot,
                "head_rot": rot,
                "health": 100,
                "ammo": 10,
                "alive": True,
                "tread_frame": 0.0,
                "kills": 0,
                "deaths": 0
            }
            self.inputs[player_id] = {"left": False, "right": False, "forward": False, "backward": False, "aim": rot}
            self.add_chat(self.players[player_id]["name"] + " joined!")
            return player_id

    def remove_player(self, player_id):
        with self.lock:
            player = self.players.pop(player_id, None)
            self.inputs.pop(player_id, None)
            client = self.clients.pop(player_id, None)

            if client:
                try:
                    client.close()
                except OSError:
                    pass

            if player and not self.match_over:
                self.add_chat(player["name"] + " left!")

    def blocked_tile(self, x, y):
        item = math.floor(x + 1.5)
        row = math.floor(y + 1.5)

        if row < 0 or row >= len(self.field) or item < 0 or item >= len(self.field[row]):
            return True

        return self.field[row][item][0] in ("edge", "corner")

    def tank_blocked(self, x, y, rot):
        half = 0.4
        radians = math.radians(-rot)
        cosine = math.cos(radians)
        sine = math.sin(radians)
        points = [(-half, -half), (half, -half), (-half, half), (half, half), (0, -half), (0, half), (-half, 0), (half, 0)]

        for ox, oy in points:
            rx = ox * cosine - oy * sine
            ry = ox * sine + oy * cosine

            if self.blocked_tile(x + rx, y + ry):
                return True

        return False

    def turn_toward(self, current, target, amount):
        difference = (target - current + 180) % 360 - 180
        return (current + max(-amount, min(amount, difference))) % 360

    def shoot(self, player_id):
        player = self.players.get(player_id)

        if self.match_over or not player or not player["alive"] or player["ammo"] <= 0:
            return

        direction = player["head_rot"]
        self.bullets.append({
            "id": self.next_bullet_id,
            "owner": player_id,
            "team": player["team"],
            "x": player["x"] - math.sin(math.radians(direction)) * 0.65,
            "y": player["y"] - math.cos(math.radians(direction)) * 0.65,
            "direction": direction,
            "distance": 0.0
        })
        self.next_bullet_id += 1
        player["ammo"] -= 1

    def respawn(self, player_id):
        player = self.players.get(player_id)

        if self.match_over or not player or player["alive"]:
            return

        x, y, rot = self.spawn_for(player_id, player["team"])
        player.update({"x": x, "y": y, "tread_rot": rot, "head_rot": rot, "health": 100, "ammo": 0, "alive": True})

        teammates = [
            teammate
            for teammate in self.players.values()
            if teammate["team"] == player["team"]
            and teammate["id"] != player_id
            and teammate["ammo"] > 0
        ]
        teammates.sort(key=lambda teammate: teammate["ammo"], reverse=True)

        for teammate in teammates[:5]:
            teammate["ammo"] -= 1
            player["ammo"] += 1

    def update_players(self, dt):
        for player_id, player in self.players.items():
            if not player["alive"]:
                continue

            controls = self.inputs.get(player_id, {})
            new_rot = player["tread_rot"]

            if controls.get("left"):
                new_rot += 120 * dt
            if controls.get("right"):
                new_rot -= 120 * dt

            new_rot %= 360

            if not self.tank_blocked(player["x"], player["y"], new_rot):
                player["tread_rot"] = new_rot

            player["head_rot"] = self.turn_toward(player["head_rot"], controls.get("aim", player["head_rot"]), 240 * dt)
            direction = int(bool(controls.get("forward"))) - int(bool(controls.get("backward")))

            if direction:
                new_x = player["x"] - math.sin(math.radians(player["tread_rot"])) * 1.2 * dt * direction
                new_y = player["y"] - math.cos(math.radians(player["tread_rot"])) * 1.2 * dt * direction

                if not self.tank_blocked(new_x, new_y, player["tread_rot"]):
                    player["x"] = new_x
                    player["y"] = new_y
                    player["tread_frame"] -= 18 * dt * direction

            for ammo in self.ammo_positions[:]:
                if math.hypot(ammo[0] - player["x"], ammo[1] - player["y"]) < 0.8:
                    player["ammo"] += ammo[2]
                    self.ammo_positions.remove(ammo)

    def update_bullets(self, dt):
        remaining = []

        for bullet in self.bullets:
            bullet["x"] -= math.sin(math.radians(bullet["direction"])) * 6 * dt
            bullet["y"] -= math.cos(math.radians(bullet["direction"])) * 6 * dt
            bullet["distance"] += 6 * dt

            if bullet["distance"] >= 6 or self.blocked_tile(bullet["x"], bullet["y"]):
                continue

            hit = None

            for player in self.players.values():
                if player["alive"] and player["team"] != bullet["team"] and math.hypot(player["x"] - bullet["x"], player["y"] - bullet["y"]) < 0.48:
                    hit = player
                    break

            if hit:
                shooter = self.players.get(bullet["owner"])
                hit["health"] = max(0, hit["health"] - 10)

                if shooter:
                    self.add_chat(shooter["name"] + " shot " + hit["name"] + "!")

                if hit["health"] == 0:
                    hit["alive"] = False
                    hit["deaths"] += 1

                    if shooter:
                        shooter["kills"] += 1

                    if hit["ammo"] > 0:
                        self.ammo_positions.append([hit["x"], hit["y"], hit["ammo"]])
                        hit["ammo"] = 0

                continue

            remaining.append(bullet)

        self.bullets = remaining

    def team_ammo_totals(self):
        totals = [0, 0]

        for player in self.players.values():
            totals[player["team"]] += player["ammo"]

        for bullet in self.bullets:
            totals[bullet["team"]] += 1

        return totals

    def check_match_end(self):
        if self.match_over or len(self.players) < 2:
            return

        team_counts = [sum(1 for p in self.players.values() if p["team"] == team) for team in (0, 1)]

        if 0 in team_counts:
            return

        totals = self.team_ammo_totals()

        if totals[0] > 0 and totals[1] > 0:
            return

        if self.ammo_positions:
            return

        self.match_over = True

        if totals[0] == 0 and totals[1] == 0:
            self.winner = -1
            self.add_chat("Match ended in a draw!")
        elif totals[0] == 0:
            self.winner = 1
            self.add_chat("Team 2 wins!")
        else:
            self.winner = 0
            self.add_chat("Team 1 wins!")

    def state_for(self, player_id):
        player = self.players.get(player_id)

        if not player:
            return {}

        totals = self.team_ammo_totals()
        rankings = sorted([
            {"id": p["id"], "name": p["name"], "team": p["team"], "kills": p["kills"], "deaths": p["deaths"], "difference": p["kills"] - p["deaths"]}
            for p in self.players.values()
        ], key=lambda row: (row["difference"], row["kills"], -row["deaths"]), reverse=True)

        return {
            "type": "state",
            "you": player_id,
            "join_code": self.join_code,
            "field": self.field,
            "players": list(self.players.values()),
            "bullets": self.bullets,
            "ammo_positions": self.ammo_positions,
            "chat": self.chat,
            "team_ammo": totals[player["team"]],
            "team_ammo_totals": totals,
            "match_over": self.match_over,
            "winner": self.winner,
            "rankings": rankings
        }

    def broadcast_states(self):
        dead = []

        with self.lock:
            clients = list(self.clients.items())

        for player_id, client in clients:
            try:
                send_json(client, self.state_for(player_id))
            except OSError:
                dead.append(player_id)

        for player_id in dead:
            self.remove_player(player_id)

    def game_loop(self):
        last_time = time.perf_counter()
        state_timer = 0.0

        while self.running:
            now = time.perf_counter()
            dt = min(now - last_time, 0.05)
            last_time = now

            with self.lock:
                if not self.match_over:
                    self.update_players(dt)
                    self.update_bullets(dt)
                    self.check_match_end()

            state_timer += dt

            if state_timer >= 1 / STATE_RATE:
                self.broadcast_states()
                state_timer = 0.0

            wait = 1 / TICK_RATE - (time.perf_counter() - now)

            if wait > 0:
                time.sleep(wait)

    def discovery_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", DISCOVERY_PORT))
            sock.settimeout(0.5)

            while self.running:
                try:
                    data, address = sock.recvfrom(4096)

                    if data.decode("utf-8", errors="ignore").strip() == "DISCOVER " + self.join_code:
                        sock.sendto(json.dumps({"join_code": self.join_code, "port": self.port}).encode("utf-8"), address)
                except socket.timeout:
                    pass
                except OSError:
                    break

    def handle_client(self, client, address):
        player_id = None
        buffer = ""

        try:
            client.settimeout(10)

            while "\n" not in buffer:
                data = client.recv(65536)

                if not data:
                    return

                buffer += data.decode("utf-8")

            line, buffer = buffer.split("\n", 1)
            hello = json.loads(line)

            if hello.get("type") != "join" or hello.get("join_code", "").upper() != self.join_code:
                send_json(client, {"type": "error", "message": "Invalid join code"})
                return

            player_id = self.add_player(hello.get("name", "PLAYER"), hello.get("color", "red"))

            if player_id is None:
                send_json(client, {"type": "error", "message": "Game is full or already ended"})
                return

            with self.lock:
                self.clients[player_id] = client

            client.settimeout(None)
            send_json(client, {"type": "welcome", "player_id": player_id, "join_code": self.join_code})

            while self.running:
                data = client.recv(65536)

                if not data:
                    break

                buffer += data.decode("utf-8")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)

                    if not line.strip():
                        continue

                    message = json.loads(line)

                    with self.lock:
                        if message.get("type") == "input" and player_id in self.inputs:
                            self.inputs[player_id] = {
                                "left": bool(message.get("left")),
                                "right": bool(message.get("right")),
                                "forward": bool(message.get("forward")),
                                "backward": bool(message.get("backward")),
                                "aim": float(message.get("aim", 0)) % 360
                            }
                        elif message.get("type") == "shoot":
                            self.shoot(player_id)
                        elif message.get("type") == "respawn":
                            self.respawn(player_id)
        except (OSError, ConnectionError, json.JSONDecodeError, ValueError):
            pass
        finally:
            if player_id is not None:
                self.remove_player(player_id)
            else:
                try:
                    client.close()
                except OSError:
                    pass

    def accept_loop(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(MAX_PLAYERS)
        self.server_socket.settimeout(0.5)

        while self.running:
            try:
                client, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client, address), daemon=True).start()
            except socket.timeout:
                pass
            except OSError:
                break

    def start(self):
        if self.running:
            return

        self.running = True
        threading.Thread(target=self.accept_loop, daemon=True).start()
        threading.Thread(target=self.discovery_loop, daemon=True).start()
        threading.Thread(target=self.game_loop, daemon=True).start()

    def stop(self):
        self.running = False

        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass

        with self.lock:
            for client in list(self.clients.values()):
                try:
                    client.close()
                except OSError:
                    pass
            self.clients.clear()
