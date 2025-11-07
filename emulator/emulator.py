import socket
import random
import time
import threading

class Emulator:
    def __init__(self, listen_port, forward_host, forward_port,
                 loss_rate=0.05, base_delay=0.05, jitter=0.01):
        self.listen_port = listen_port
        self.forward_host = forward_host
        self.forward_port = forward_port
        self.loss_rate = loss_rate
        self.base_delay = base_delay
        self.jitter = jitter

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("localhost", listen_port))
        self.running = True

        self.sendsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def start(self):
        print(f"[Emulator] Listening on port {self.listen_port}, forwarding to {self.forward_port}")
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        while self.running:
            data, addr = self.sock.recvfrom(65535)
            if random.random() < self.loss_rate:
                print("[Emulator] Dropped packet")
                continue

            delay = max(0, random.uniform(self.base_delay - self.jitter, self.base_delay + self.jitter))
            self.delayed_send(data, delay)

    def delayed_send(self, data, delay):
        time.sleep(delay)
        self.sendsock.sendto(data, (self.forward_host, self.forward_port))
        #print(f"[Emulator] Sent packet after {delay*1000:.1f} ms")

    def stop(self):
        self.running = False
        self.sock.close()
        self.sendsock.close()

# Example usage:
# Emulate network between sender (8888) and receiver (8889)
if __name__ == "__main__":
    emulator = Emulator(listen_port=9999, forward_host="localhost", forward_port=8889,
                               loss_rate=0, base_delay=0.01, jitter=0.005)
    emulator.start()
    while (True):
        pass
    # Sender should send to port 9999 instead of 8889 now.
