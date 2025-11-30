import threading
import time
import socket

# This implements the required ~200ms latency.
LATENCY_DELAY = 0.2 

class LaggySocket:
    """
    Wraps a standard socket to introduce artificial latency.
    """
    def __init__(self, real_socket):
        self.sock = real_socket
        self.send_queue = []
        self.running = True
        
        threading.Thread(target=self._sender_loop, daemon=True).start()

    def send(self, data):
        """Schedule the send for 200ms in the future."""
        send_time = time.time() + LATENCY_DELAY
        self.send_queue.append((send_time, data))

    def recv(self, bufsize):
        """Standard receive (latency is handled by the sender's delay)."""
        return self.sock.recv(bufsize)

    def _sender_loop(self):
        while self.running:
            now = time.time()
            if self.send_queue:
                send_time, data = self.send_queue[0]
                if now >= send_time:
                    try:
                        self.sock.sendall(data)
                        self.send_queue.pop(0)
                    except OSError:
                        self.running = False
                        break
            time.sleep(0.001)

    def close(self):
        self.running = False
        self.sock.close()