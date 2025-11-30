import socket
import threading
import pygame
import time
import os
import common
import network 

class GameClient:
    def __init__(self):
        real_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        real_socket.connect((common.HOST, common.PORT))
        self.client_socket = network.LaggySocket(real_socket)
        
        pygame.init()
        self.screen = pygame.display.set_mode((common.SCREEN_WIDTH, common.SCREEN_HEIGHT))
        pygame.display.set_caption("Cash the Coins - Krafton Test")
        self.font = pygame.font.SysFont("Arial", 18)
        self.running = True
        
        
        self.bg_image = None
        base_folder = os.path.dirname(os.path.abspath(__file__))
        bg_path = os.path.join(base_folder, "background.png")
        bg_path = "background.png" 
        if os.path.exists(bg_path):
            img = pygame.image.load(bg_path)
            self.bg_image = pygame.transform.scale(img, (common.SCREEN_WIDTH, common.SCREEN_HEIGHT))
        else:
            print("[INFO] No 'background.jpg' found. Using dark color.")
        
        self.my_id = None
        self.lock = threading.Lock()
        
        self.state_buffer = [] 
        self.INTERP_DELAY = 0.25
        self.status_msg = "Connecting..."

    def listen_from_server(self):
        while self.running:
            try:
                data = self.client_socket.recv(common.BUF_SIZE)
                if not data: break
                
                try:
                    msg = common.from_json(data)
                    if not msg: continue

                    if msg[common.KEY_TYPE] == common.MSG_CONNECT:
                        self.my_id = msg[common.KEY_ID]
                        print(f"Connected! ID: {self.my_id}")
                    
                    elif msg[common.KEY_TYPE] == common.MSG_STATE:
                        with self.lock:
                            server_state = msg[common.KEY_DATA]
                            msg_time = server_state.get("time", time.time())
                            self.state_buffer.append((msg_time, server_state))
                            
                            
                            self.status_msg = server_state.get("status", "PLAYING")

                            if len(self.state_buffer) > 20:
                                self.state_buffer.pop(0)

                except ValueError: pass
            except Exception as e:
                print(f"Disconnected: {e}")
                self.running = False
                break

    def send_input(self, cmd):
        msg = {common.KEY_TYPE: common.MSG_INPUT, common.KEY_DATA: cmd}
        try:
            self.client_socket.send(common.to_json(msg))
        except: pass

    def get_interpolated_state(self):
        render_time = time.time() - self.INTERP_DELAY
        with self.lock:
            if len(self.state_buffer) < 2:
                if len(self.state_buffer) == 1: return self.state_buffer[0][1]
                return None

            idx = -1
            for i in range(len(self.state_buffer) - 1):
                if self.state_buffer[i][0] <= render_time <= self.state_buffer[i+1][0]:
                    idx = i
                    break
            
            if idx == -1: return self.state_buffer[-1][1]

            t_start, state_start = self.state_buffer[idx]
            t_end, state_end = self.state_buffer[idx+1]
            fraction = (render_time - t_start) / (t_end - t_start)
            
            interp_state = {"coins": state_end["coins"], "players": {}}
            players_start = state_start.get("players", {})
            players_end = state_end.get("players", {})
            
            for pid, p_end in players_end.items():
                if pid in players_start:
                    p_start = players_start[pid]
                    new_x = p_start['x'] + (p_end['x'] - p_start['x']) * fraction
                    new_y = p_start['y'] + (p_end['y'] - p_start['y']) * fraction
                    interp_state["players"][pid] = {
                        "x": new_x, "y": new_y,
                        "score": p_end['score'], "shape": p_end['shape'], "color": p_end['color']
                    }
                else:
                    interp_state["players"][pid] = p_end
            return interp_state

    def draw_triangle(self, surface, color, x, y, size, width=0):
        points = [(x + size // 2, y), (x, y + size), (x + size, y + size)]
        pygame.draw.polygon(surface, color, points, width)

    def run(self):
        threading.Thread(target=self.listen_from_server, daemon=True).start()
        clock = pygame.time.Clock()
        
        try:
            while self.running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT: self.running = False
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_r: self.send_input(common.CMD_RESET)
                        if event.key == pygame.K_SPACE: self.send_input(common.CMD_DASH) 

                keys = pygame.key.get_pressed()
                if keys[pygame.K_UP]: self.send_input(common.CMD_UP)
                if keys[pygame.K_DOWN]: self.send_input(common.CMD_DOWN)
                if keys[pygame.K_LEFT]: self.send_input(common.CMD_LEFT)
                if keys[pygame.K_RIGHT]: self.send_input(common.CMD_RIGHT)

                # Draw Background
                if self.bg_image:
                    self.screen.blit(self.bg_image, (0, 0))
                else:
                    self.screen.fill((30, 30, 30))
                
                state = self.get_interpolated_state()
                if state:
                    # Draw Coins
                    for c in state.get("coins", []):
                        c_type = int(c['type']) 
                        color = tuple(common.COIN_TYPES[c_type]['color'])
                        center = (c['x'] + common.COIN_SIZE // 2, c['y'] + common.COIN_SIZE // 2)
                        pygame.draw.circle(self.screen, color, center, common.COIN_RADIUS)

                    # Draw Players
                    players = state.get("players", {})
                    for pid, p in players.items():
                        color = tuple(p['color'])
                        draw_x, draw_y = int(p['x']), int(p['y'])
                        
                        if p['shape'] == 0:
                            pygame.draw.rect(self.screen, color, (draw_x, draw_y, common.PLAYER_SIZE, common.PLAYER_SIZE))
                        else:
                            self.draw_triangle(self.screen, color, draw_x, draw_y, common.PLAYER_SIZE)

                        
                        if pid == self.my_id:
                            if p['shape'] == 0:
                                pygame.draw.rect(self.screen, common.WHITE, (draw_x, draw_y, common.PLAYER_SIZE, common.PLAYER_SIZE), 2)
                            else:
                                self.draw_triangle(self.screen, common.WHITE, draw_x, draw_y, common.PLAYER_SIZE, 2)
                            
                        score_text = self.font.render(f"{p['score']}", True, common.WHITE)
                        self.screen.blit(score_text, (draw_x, draw_y - 20))

               
                if self.status_msg == "WAITING":
                    text_surf = self.font.render("WAITING FOR PLAYER 2...", True, common.WHITE)
                    
                    bg_w = text_surf.get_width() + 40
                    bg_h = text_surf.get_height() + 20
                    bg_surf = pygame.Surface((bg_w, bg_h))
                    
                   
                    bg_surf.set_alpha(150) 
                    bg_surf.fill(common.BLACK)
                    
                   
                    center_x = common.SCREEN_WIDTH // 2
                    center_y = common.SCREEN_HEIGHT // 2
                    
                    
                    self.screen.blit(bg_surf, (center_x - bg_w // 2, center_y - bg_h // 2))
                    self.screen.blit(text_surf, (center_x - text_surf.get_width() // 2, center_y - text_surf.get_height() // 2))

                pygame.display.flip()
                clock.tick(60)

        except KeyboardInterrupt:
            print("\n[EXIT] Game closed.")
        finally:
            pygame.quit()
            self.client_socket.close()

if __name__ == "__main__":
    GameClient().run()