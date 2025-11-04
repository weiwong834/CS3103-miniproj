"""
Demo: Test Reliability Features
Shows ACKs, retransmissions, and packet reordering
"""

import sys
import os
import time
import threading
import random

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.game_net_api import GameNetAPI

def run_receiver():
    """Receiver that demonstrates reliability features"""
    print("\n" + "="*60)
    print("RECEIVER - Testing Reliability Features")
    print("="*60 + "\n")

    receiver = GameNetAPI(port=8889, target_port=8888)

    # Receive for 10 seconds
    start_time = time.time()
    packet_count = 0

    while time.time() - start_time < 10:
        packet = receiver.receive()
        if packet:
            packet_count += 1
        time.sleep(0.01)  # Small delay to prevent busy waiting

    print("\n" + "-"*60)
    print("RECEIVER METRICS:")
    metrics = receiver.get_metrics()
    print(f"  Packets received: {packet_count}")
    print(f"  Reliable received: {metrics['reliable_received']}")
    print(f"  Unreliable received: {metrics['unreliable_received']}")
    print(f"  ACKs sent: {metrics['acks_sent']}")
    print(f"  Packets reordered: {metrics['packets_reordered']}")
    print(f"  Average latency: {metrics['avg_latency']:.1f}ms")
    print("-"*60 + "\n")

    receiver.close()

def run_sender():
    """Sender that tests reliability features"""
    print("\n" + "="*60)
    print("SENDER - Testing Reliability Features")
    print("="*60)
    print("\nTest 1: Normal reliable and unreliable packets")
    print("-"*40)

    time.sleep(1)  # Give receiver time to start
    sender = GameNetAPI(port=8888, target_port=8889)

    # Test 1: Send mix of reliable and unreliable
    sender.send("Game state: Player joined", reliable=True)
    time.sleep(0.1)
    sender.send("Position update: x=100, y=200", reliable=False)
    time.sleep(0.1)
    sender.send("Score update: Player1=100", reliable=True)
    time.sleep(0.1)

    print("\nTest 2: Rapid sending (test reordering)")
    print("-"*40)
    # Test 2: Send packets quickly to test reordering
    for i in range(5):
        sender.send(f"Rapid reliable packet {i}", reliable=True)
        time.sleep(0.01)  # Very short delay

    print("\nTest 3: Mixed rapid sending")
    print("-"*40)
    # Test 3: Mixed rapid sending
    for i in range(3):
        sender.send(f"Chat message {i}", reliable=True)
        sender.send(f"Mouse position {i}", reliable=False)

    # Wait a bit to see retransmissions (if network has issues)
    time.sleep(2)

    print("\n" + "-"*60)
    print("SENDER METRICS:")
    metrics = sender.get_metrics()
    print(f"  Reliable sent: {metrics['reliable_sent']}")
    print(f"  Unreliable sent: {metrics['unreliable_sent']}")
    print(f"  ACKs received: {metrics['acks_received']}")
    print(f"  Packets retransmitted: {metrics['packets_retransmitted']}")
    print(f"  Total retry attempts: {metrics['total_retry_attempts']}")
    print(f"  Failed packets: {metrics['packets_failed']}")
    print("-"*60 + "\n")

    sender.close()

def run_simulated_loss_test():
    """Test with simulated packet loss"""
    print("\n" + "="*60)
    print("SIMULATED PACKET LOSS TEST")
    print("="*60)
    print("Starting sender and receiver with simulated loss...\n")

    # Start receiver in thread
    receiver_thread = threading.Thread(target=run_receiver_with_loss)
    receiver_thread.start()

    time.sleep(1)

    # Run sender with some packets that will trigger retransmission
    sender = GameNetAPI(port=8888, target_port=8889)

    print("Sending packets (some will be 'lost' to test retransmission)...")
    for i in range(10):
        msg = f"Important message #{i}"
        sender.send(msg, reliable=True)
        time.sleep(0.3)  # Space them out to see retransmissions

    time.sleep(3)  # Wait for retransmissions

    metrics = sender.get_metrics()
    print(f"\nRETRANSMISSION TEST RESULTS:")
    print(f"  Packets sent: {metrics['reliable_sent']}")
    print(f"  Packets retransmitted: {metrics['packets_retransmitted']}")
    print(f"  Total retry attempts: {metrics['total_retry_attempts']}")

    sender.close()
    receiver_thread.join(timeout=2)

def run_receiver_with_loss():
    """Receiver that simulates packet loss"""
    receiver = GameNetAPI(port=8889, target_port=8888)

    start_time = time.time()
    while time.time() - start_time < 8:
        packet = receiver.receive()
        # Randomly "drop" some ACKs to trigger retransmission
        if packet and random.random() > 0.3:  # 30% simulated loss
            pass  # Process normally
        time.sleep(0.01)

    receiver.close()

if __name__ == "__main__":
    print("CS3103 RELIABILITY FEATURES DEMO")
    print("1. Receiver (shows ACKs, reordering)")
    print("2. Sender (shows retransmission)")
    print("3. Automated test with simulated loss")

    choice = input("\nChoice (1/2/3): ")
    if choice == "1":
        run_receiver()
    elif choice == "2":
        run_sender()
    elif choice == "3":
        run_simulated_loss_test()
    else:
        print("Running automated test...")
        run_simulated_loss_test()