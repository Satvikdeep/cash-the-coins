import socket
import threading
import time
import uuid
import random
import common
import network

class GameServer:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((common.HOST, common.PORT))
        self.server_socket.listen(2)
        print(f"[STARTING] Server listening on {common.HOST}:{common.PORT}")

        self.players = {} 
        self.coins = []   
        self.clients = [] 
        self.lock = threading.Lock()
        self.last_coin_spawn = time.time()
        
    def start(self):
        threading.Thread(target=self.game_loop, daemon=True).start()
        try:
            while True:
                conn, addr = self.server_socket.accept()
                print(f"[NEW CONNECTION] {addr} connected.")
                laggy_conn = network.LaggySocket(conn)
                player_id = str(uuid.uuid4())
                threading.Thread(target=self.handle_client, args=(laggy_conn, player_id)).start()
        except KeyboardInterrupt:
            print("\n[SHUTTING DOWN] Server stopped.")
        finally:
            self.server_socket.close()

    def handle_client(self, conn, player_id):
        with self.lock:
            self.clients.append(conn)

        # 1. Assign Position & State
        with self.lock:
            shape_id = len(self.players) % 2 
            if shape_id == 0: start_x = 100 
            else: start_x = common.SCREEN_WIDTH - 140

            self.players[player_id] = {
                "x": start_x,
                "y": common.SCREEN_HEIGHT // 2 - 20,
                "score": 0,
                "shape": shape_id,
                "color": common.BLUE if shape_id == 0 else common.WHITE,
                "last_dash": 0,
                "packet_count": 0,
                "last_packet_time": time.time()
            }

        
        try:
            msg = {common.KEY_TYPE: common.MSG_CONNECT, common.KEY_ID: player_id}
            conn.send(common.to_json(msg))
        except: pass

        
        try:
            while True:
                data = conn.recv(common.BUF_SIZE)
                if not data: break
                
                msg = common.from_json(data)
                if msg and msg[common.KEY_TYPE] == common.MSG_INPUT:
                    cmd = msg[common.KEY_DATA]
                    if cmd == common.CMD_RESET:
                        self.reset_game()
                    else:
                        self.process_input(player_id, cmd)
                    
        except Exception as e:
            print(f"[EXCEPTION] {player_id}: {e}")
        finally:
            with self.lock:
                if player_id in self.players: del self.players[player_id]
                if conn in self.clients: self.clients.remove(conn)
            conn.close()

    def reset_game(self):
        with self.lock:
            print("[GAME RESET]")
            self.coins = []
            for pid, p in self.players.items():
                p['score'] = 0
                p['x'] = 100 if p['shape'] == 0 else common.SCREEN_WIDTH - 140
                p['y'] = common.SCREEN_HEIGHT // 2 - 20

    def process_input(self, player_id, direction):
        with self.lock:
            if player_id not in self.players: return
            p = self.players[player_id]
            
            now = time.time()

            if now < p.get('stun_until', 0):
                return 

            if now - p.get('last_packet_time', 0) >= 1.0:
                p['packet_count'] = 0
                p['last_packet_time'] = now
            p['packet_count'] = p.get('packet_count', 0) + 1
            if p['packet_count'] > 70: return

            speed = 4
            new_x, new_y = p['x'], p['y']
            
            if direction == common.CMD_UP: new_y = max(0, p['y'] - speed)
            elif direction == common.CMD_DOWN: new_y = min(common.SCREEN_HEIGHT - common.PLAYER_SIZE, p['y'] + speed)
            elif direction == common.CMD_LEFT: new_x = max(0, p['x'] - speed)
            elif direction == common.CMD_RIGHT: new_x = min(common.SCREEN_WIDTH - common.PLAYER_SIZE, p['x'] + speed)
            
            future_rect = (new_x, new_y, common.PLAYER_SIZE, common.PLAYER_SIZE)
            
            collision = False
            for other_id, other_p in self.players.items():
                if other_id == player_id: continue 
                
                other_rect = (other_p['x'], other_p['y'], common.PLAYER_SIZE, common.PLAYER_SIZE)
                
                if self.check_collision(future_rect, other_rect):
                    collision = True
                    break
            
            if not collision:
                p['x'] = new_x
                p['y'] = new_y
            else:

                bounce_dist = 40
                if direction == common.CMD_UP: p['y'] += bounce_dist
                elif direction == common.CMD_DOWN: p['y'] -= bounce_dist
                elif direction == common.CMD_LEFT: p['x'] += bounce_dist
                elif direction == common.CMD_RIGHT: p['x'] -= bounce_dist
                
                # Clamp to screen (don't bounce out of bounds)
                p['x'] = max(0, min(common.SCREEN_WIDTH - common.PLAYER_SIZE, p['x']))
                p['y'] = max(0, min(common.SCREEN_HEIGHT - common.PLAYER_SIZE, p['y']))

                # Apply STUN: Ignore inputs for 150ms
                p['stun_until'] = now + 0.3

    def game_loop(self):
        while True:
            start_time = time.time()
            
            with self.lock:
                # Only run logic if 2 players connected
                if len(self.clients) >= 2:
                    
                    if len(self.coins) < common.MAX_COINS:
                        if time.time() - self.last_coin_spawn > 3: 
                            coin_type = random.choice([0, 0, 0, 1, 1, 2])
                            self.coins.append({
                                "x": random.randint(0, common.SCREEN_WIDTH - common.COIN_SIZE),
                                "y": random.randint(0, common.SCREEN_HEIGHT - common.COIN_SIZE),
                                "type": coin_type,
                                "id": str(uuid.uuid4())
                            })
                            self.last_coin_spawn = time.time()
                    
                    # Collisions
                    for pid, p in self.players.items():
                        p_rect = (p['x'], p['y'], common.PLAYER_SIZE, common.PLAYER_SIZE)
                        for i in range(len(self.coins) - 1, -1, -1):
                            c = self.coins[i]
                            c_rect = (c['x'], c['y'], common.COIN_SIZE, common.COIN_SIZE)
                            if self.check_collision(p_rect, c_rect):
                                p['score'] += common.COIN_TYPES[c['type']]["val"]
                                del self.coins[i]

                                

                # PREPARE STATE (Happens even if 1 player)
                state_msg = common.to_json({
                    common.KEY_TYPE: common.MSG_STATE,
                    common.KEY_DATA: {
                        "players": self.players,
                        "coins": self.coins,
                        "time": time.time(),
                        "status": "WAITING" if len(self.clients) < 2 else "PLAYING"
                    }
                })
            
            # Broadcast to whoever is connected
            for c in self.clients[:]:
                try:
                    c.send(state_msg)
                except:
                    with self.lock:
                        if c in self.clients: self.clients.remove(c)

            elapsed = time.time() - start_time
            sleep_time = max(0, (1/common.TARGET_FPS) - elapsed)
            time.sleep(sleep_time)

    def check_collision(self, rect1, rect2):
        x1, y1, w1, h1 = rect1
        x2, y2, w2, h2 = rect2
        return (x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2)

if __name__ == "__main__":
    GameServer().start()