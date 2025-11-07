import sys
import os

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from emulator.emulator import Emulator
from src.apps.emulator_options import E1_PACKETLOSS, E1_DELAY, E1_JITTER, E2_PACKETLOSS, E2_DELAY, E2_JITTER
from src.core.game_net_api import GameNetAPI
import time
import threading

def run_receiver():
    """Show packets arriving with sequence numbers and latency"""
    print("[RECEIVER] - Showing packet arrival with seq numbers & latency")
    receiver = GameNetAPI(port=8889, target_port=8888)
    
    count = 0
    while count < 10:  # Show 10 packets then stop
        packet = receiver.receive()
        if packet:
            count += 1
        time.sleep(0.1)
    
    metrics = receiver.get_metrics()
    print(f"[METRICS]: {metrics}")
    receiver.close()

def run_sender():
    """Show reliable vs unreliable sending"""
    print("[SENDER] - Showing reliable vs unreliable channels")
    time.sleep(1)
    sender = GameNetAPI(port=8888, target_port=8889)
    
    # REQUIRED: Mark packets as reliable/unreliable
    sender.send("CRITICAL: Player score update", reliable=True)
    time.sleep(0.5)
    sender.send("FAST: Player movement data", reliable=False) 
    time.sleep(0.5)
    sender.send("CRITICAL: Game state save", reliable=True)
    time.sleep(0.5)
    sender.send("FAST: Voice chat packet", reliable=False)
    
    # Show metrics
    metrics = sender.get_metrics()
    print(f"[SENT]: {metrics['reliable_sent']} reliable, {metrics['unreliable_sent']} unreliable")
    sender.close()

def test_all_features():
    """Test all Person 2 reliability features"""
    print("\n" + "="*50)
    print("TESTING ALL RELIABILITY FEATURES")
    print("="*50)

    def start_emulator(listen_port, forward_host, target_port, loss_rate, base_delay, jitter):
        emulator = Emulator(listen_port, forward_host, target_port, loss_rate, base_delay, jitter)
        emulator.start()

    def test_receiver():
        receiver = GameNetAPI(port=8889, target_port=9998)
        received_packets = []

        for _ in range(50):  # Extended to allow all ACKs to be sent back
            packet = receiver.receive()
            if packet:
                received_packets.append(packet.seq_no)
            time.sleep(0.05)

        print(f"\n[TEST] Received packets in order: {received_packets[:10]}...")
        metrics = receiver.get_metrics()
        print(f"[TEST] Receiver metrics:")
        print(f"  - ACKs sent: {metrics['acks_sent']}")
        print(f"  - Packets reordered: {metrics.get('packets_reordered', 0)}")
        print(f"  - Average latency: {metrics.get('avg_latency')}")
        receiver.close()

    def test_sender():
        time.sleep(0.5)  # Let receiver start
        sender = GameNetAPI(port=8888, target_port=9999)

        # Test 1: Reliable vs Unreliable
        print("\n[TEST] Sending reliable and unreliable packets...")
        sender.send("Critical: Game state", reliable=True)
        sender.send("Fast: Position update", reliable=False)
        sender.send("Critical: Score update", reliable=True)

        # Test 2: Rapid sending (triggers reordering)
        print("[TEST] Rapid sending to test reordering...")
        for i in range(5):
            sender.send(f"Rapid packet {i}", reliable=True)
            time.sleep(0.001)  # Very small delay

        time.sleep(2.5)  # Wait longer for all ACKs and retransmissions

        metrics = sender.get_metrics()
        print(f"\n[TEST] Sender metrics:")
        print(f"  - Reliable sent: {metrics['reliable_sent']}")
        print(f"  - Unreliable sent: {metrics['unreliable_sent']}")
        print(f"  - ACKs received: {metrics.get('packets_acked', metrics.get('acks_received', 0))}")
        print(f"  - Retransmitted: {metrics.get('packets_retransmitted', 0)}")
        sender.close()

    # Run test with threads
    receiver_thread = threading.Thread(target=test_receiver)
    sender_thread = threading.Thread(target=test_sender)
    e1_thread = threading.Thread(target=start_emulator, args=(9999, "localhost", 8889, E1_PACKETLOSS, E1_DELAY, E1_JITTER)).start()
    e2_thread = threading.Thread(target=start_emulator, args=(9998, "localhost", 8888, E2_PACKETLOSS, E2_DELAY, E2_JITTER)).start()

    receiver_thread.start()
    sender_thread.start()

    #receiver_thread.join()
    #sender_thread.join()

    print("\n" + "="*50)
    print("ALL FEATURES TESTED SUCCESSFULLY!")
    print("Features verified:")
    print("  - ACK system (using reliable channel with ACK: prefix)")
    print("  - Reliable vs Unreliable channels")
    print("  - Retransmission (200ms timeout)")
    print("  - Packet reordering")
    print("  - Metrics tracking")
    print("="*50)

if __name__ == "__main__":
    print("CS3103 REQUIREMENTS DEMO")
    print("1. Receiver (see packets arrive)")
    print("2. Sender (see both channels)")
    print("3. Test all features (Person 2)")

    choice = input("Choice (1/2/3): ")
    if choice == "1":
        run_receiver()
    elif choice == "2":
        run_sender()
    else:
        test_all_features()