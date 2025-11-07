"""
Reorder Buffer for Reliable Channel
Handles out-of-order packet buffering and in-order delivery
"""

from typing import Dict, List, Optional, Tuple
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.constants import REORDER_BUFFER_SIZE, REORDER_TIMEOUT

class ReorderBuffer:
    def __init__(self, max_size: int = REORDER_BUFFER_SIZE, send_dup_ack_callback=None):
        """
        Initialize reorder buffer for reliable packets with duplicate ACK support

        Args:
            max_size: Maximum number of out-of-order packets to buffer
            send_dup_ack_callback: Function to send duplicate ACK for last in-order packet
        """
        self.max_size = max_size
        self.expected_seq = 0  # Next expected sequence number
        self.buffer: Dict[int, Tuple[object, float]] = {}  # {seq_no: (packet, timestamp)}
        self.delivered_count = 0
        self.reordered_count = 0
        self.skipped_count = 0
        self.gap_start_time = None  # Track when we first noticed a gap
        self.last_acked = -1  # Last in-order packet we ACKed
        self.send_dup_ack = send_dup_ack_callback  # Callback for duplicate ACKs
        self.dup_ack_count = 0  # Track duplicate ACKs sent

    def add_packet(self, seq_no: int, packet) -> List:
        """
        Add packet to buffer and return list of packets ready for delivery

        Args:
            seq_no: Packet sequence number
            packet: The packet object

        Returns:
            List of packets ready for in-order delivery
        """
        ready_packets = []
        current_time = time.time()

        # Check for timeout - skip missing packet if waiting too long
        if self.gap_start_time and (current_time - self.gap_start_time) >= REORDER_TIMEOUT:
            print(f"[REORDER] Timeout waiting for packet R#{self.expected_seq} "
                  f"({REORDER_TIMEOUT*1000:.0f}ms threshold), skipping to continue")
            self.skipped_count += 1
            self.expected_seq = (self.expected_seq + 1) % 65536
            self.gap_start_time = None

            # Deliver any now-ready buffered packets
            while self.expected_seq in self.buffer:
                buffered_packet, _ = self.buffer[self.expected_seq]
                ready_packets.append(buffered_packet)
                del self.buffer[self.expected_seq]
                self.expected_seq = (self.expected_seq + 1) % 65536
                self.delivered_count += 1

        # If this is the expected packet
        if seq_no == self.expected_seq:
            ready_packets.append(packet)
            self.expected_seq = (self.expected_seq + 1) % 65536
            self.delivered_count += 1
            self.gap_start_time = None  # Reset gap timer
            self.last_acked = seq_no  # Track last in-order packet

            # Check if buffered packets are now ready
            while self.expected_seq in self.buffer:
                buffered_packet, _ = self.buffer[self.expected_seq]
                ready_packets.append(buffered_packet)
                del self.buffer[self.expected_seq]
                self.expected_seq = (self.expected_seq + 1) % 65536
                self.delivered_count += 1
                self.reordered_count += 1
                print(f"[REORDER] Delivered buffered packet R#{self.expected_seq - 1} after gap filled")

        # If packet is ahead of expected (out-of-order)
        elif self._is_ahead(seq_no):
            if len(self.buffer) < self.max_size:
                if seq_no not in self.buffer:  # Avoid duplicates
                    self.buffer[seq_no] = (packet, current_time)
                    gap = seq_no - self.expected_seq
                    print(f"[REORDER] Buffering packet R#{seq_no}, expecting R#{self.expected_seq} (gap: {gap})")

                    # Start gap timer if not already started
                    if self.gap_start_time is None:
                        self.gap_start_time = current_time

                    # Send duplicate ACK for last in-order packet (Selective Repeat standard)
                    if self.send_dup_ack and self.last_acked >= 0:
                        self.send_dup_ack(self.last_acked)
                        self.dup_ack_count += 1
                        print(f"[DUP-ACK] Sent duplicate ACK for R#{self.last_acked} (gap detected at R#{seq_no})")
            else:
                print(f"[REORDER] Buffer full ({self.max_size}), dropping packet R#{seq_no}")

        # If packet is behind expected (late duplicate)
        else:
            print(f"[REORDER] Ignoring late/duplicate packet R#{seq_no}, expecting R#{self.expected_seq}")

        return ready_packets

    def _is_ahead(self, seq_no: int) -> bool:
        """
        Check if sequence number is ahead of expected (handling wraparound)
        """
        # Handle sequence number wraparound at 65536
        if self.expected_seq < 32768:
            # Expected is in first half
            return seq_no > self.expected_seq and seq_no < self.expected_seq + 32768
        else:
            # Expected is in second half
            return seq_no > self.expected_seq or seq_no < (self.expected_seq - 32768)

    def check_timeout(self) -> List:
        """
        Check for timeout and skip missing packets if necessary
        Called periodically to handle gaps that exceed threshold
        """
        ready_packets = []
        current_time = time.time()

        if self.gap_start_time and (current_time - self.gap_start_time) >= REORDER_TIMEOUT:
            print(f"[REORDER] Timeout waiting for packet R#{self.expected_seq} "
                  f"({REORDER_TIMEOUT*1000:.0f}ms threshold), skipping to continue")
            self.skipped_count += 1
            self.expected_seq = (self.expected_seq + 1) % 65536
            self.gap_start_time = None

            # Deliver any now-ready buffered packets
            while self.expected_seq in self.buffer:
                buffered_packet, _ = self.buffer[self.expected_seq]
                ready_packets.append(buffered_packet)
                del self.buffer[self.expected_seq]
                self.expected_seq = (self.expected_seq + 1) % 65536
                self.delivered_count += 1

        return ready_packets

    def get_stats(self) -> dict:
        """Get reordering statistics"""
        return {
            'delivered': self.delivered_count,
            'reordered': self.reordered_count,
            'buffered': len(self.buffer),
            'next_expected': self.expected_seq,
            'skipped': self.skipped_count
        }

    def reset(self):
        """Reset buffer state"""
        self.expected_seq = 0
        self.buffer.clear()
        self.delivered_count = 0
        self.reordered_count = 0