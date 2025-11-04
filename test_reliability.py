"""
Quick test of reliability features
"""

import sys
import time
import threading
from src.core.game_net_api import GameNetAPI

def receiver_process():
    receiver = GameNetAPI(port=8889, target_port=8888)
    print("[RECEIVER] Started on port 8889")

    for _ in range(10):
        packet = receiver.receive()
        if packet:
            print(f"[RECEIVER] Got: {packet.payload}")
        time.sleep(0.1)

    receiver.close()

def sender_process():
    time.sleep(0.5)  # Let receiver start
    sender = GameNetAPI(port=8888, target_port=8889)
    print("[SENDER] Started on port 8888")

    # Send test packets
    sender.send("Test reliable 1", reliable=True)
    sender.send("Test unreliable 1", reliable=False)
    sender.send("Test reliable 2", reliable=True)

    time.sleep(2)
    sender.close()

if __name__ == "__main__":
    print("Testing reliability features...")

    receiver_thread = threading.Thread(target=receiver_process)
    sender_thread = threading.Thread(target=sender_process)

    receiver_thread.start()
    sender_thread.start()

    receiver_thread.join()
    sender_thread.join()

    print("\nTest complete!")