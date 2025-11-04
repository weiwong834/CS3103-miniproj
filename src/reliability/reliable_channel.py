"""
Reliable Channel Manager
Handles ACKs, retransmissions, and packet tracking
"""

import time
import threading
from typing import Dict, Optional
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.constants import RETRANSMIT_TIMEOUT, MAX_RETRANSMITS, CHANNEL_ACK

class PendingPacket:
    """Track a packet awaiting ACK"""
    def __init__(self, packet_data: bytes, seq_no: int, destination):
        self.packet_data = packet_data
        self.seq_no = seq_no
        self.destination = destination
        self.send_time = time.time()
        self.retry_count = 0
        self.acked = False

class ReliableChannel:
    def __init__(self, socket_ref):
        """
        Initialize reliable channel manager

        Args:
            socket_ref: Reference to the UDP socket for sending
        """
        self.socket = socket_ref
        self.pending_packets: Dict[int, PendingPacket] = {}
        self.lock = threading.Lock()

        # Statistics
        self.stats = {
            'sent': 0,
            'acked': 0,
            'retransmitted': 0,
            'failed': 0,
            'total_retries': 0
        }

        # Start retransmission timer thread
        self.running = True
        self.timer_thread = threading.Thread(target=self._retransmission_timer, daemon=True)
        self.timer_thread.start()

    def track_packet(self, packet_data: bytes, seq_no: int, destination):
        """
        Add packet to pending list for ACK tracking

        Args:
            packet_data: The complete packet bytes
            seq_no: Sequence number
            destination: (host, port) tuple
        """
        with self.lock:
            self.pending_packets[seq_no] = PendingPacket(packet_data, seq_no, destination)
            self.stats['sent'] += 1

    def acknowledge(self, seq_no: int):
        """
        Mark packet as acknowledged

        Args:
            seq_no: Sequence number of ACKed packet
        """
        with self.lock:
            if seq_no in self.pending_packets:
                packet = self.pending_packets[seq_no]
                if not packet.acked:
                    packet.acked = True
                    rtt = (time.time() - packet.send_time) * 1000
                    self.stats['acked'] += 1
                    print(f"[ACK] Received ACK for packet #{seq_no} (RTT: {rtt:.1f}ms)")
                    # Remove from pending
                    del self.pending_packets[seq_no]

    def _retransmission_timer(self):
        """
        Background thread that checks for packets needing retransmission
        """
        while self.running:
            current_time = time.time()
            packets_to_retry = []

            with self.lock:
                for seq_no, packet in list(self.pending_packets.items()):
                    if packet.acked:
                        continue

                    time_elapsed = current_time - packet.send_time

                    if time_elapsed >= RETRANSMIT_TIMEOUT:
                        if packet.retry_count < MAX_RETRANSMITS:
                            packets_to_retry.append(packet)
                        else:
                            # Max retries reached, give up
                            print(f"[RETRANSMIT] Packet #{seq_no} failed after {MAX_RETRANSMITS} retries")
                            self.stats['failed'] += 1
                            del self.pending_packets[seq_no]

            # Retransmit outside the lock to avoid blocking
            for packet in packets_to_retry:
                self._retransmit_packet(packet)

            # Check every 50ms for efficiency
            time.sleep(0.05)

    def _retransmit_packet(self, packet: PendingPacket):
        """
        Retransmit a packet
        """
        packet.retry_count += 1
        packet.send_time = time.time()  # Reset timer

        try:
            self.socket.sendto(packet.packet_data, packet.destination)
            self.stats['retransmitted'] += 1
            self.stats['total_retries'] += 1
            print(f"[RETRANSMIT] Packet #{packet.seq_no} lost, attempt {packet.retry_count}/{MAX_RETRANSMITS} "
                  f"({RETRANSMIT_TIMEOUT * 1000:.0f}ms timeout)")
        except Exception as e:
            print(f"[RETRANSMIT] Error resending packet #{packet.seq_no}: {e}")

    def get_stats(self) -> dict:
        """Get channel statistics"""
        with self.lock:
            return self.stats.copy()

    def shutdown(self):
        """Shutdown the retransmission timer"""
        self.running = False
        if self.timer_thread.is_alive():
            self.timer_thread.join(timeout=1.0)