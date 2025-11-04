"""
Reorder Buffer for Reliable Channel
Handles out-of-order packet buffering and in-order delivery
"""

from typing import Dict, List, Optional
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.constants import REORDER_BUFFER_SIZE

class ReorderBuffer:
    def __init__(self, max_size: int = REORDER_BUFFER_SIZE):
        """
        Initialize reorder buffer for reliable packets

        Args:
            max_size: Maximum number of out-of-order packets to buffer
        """
        self.max_size = max_size
        self.expected_seq = 0  # Next expected sequence number
        self.buffer: Dict[int, object] = {}  # Out-of-order packets
        self.delivered_count = 0
        self.reordered_count = 0

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

        # If this is the expected packet
        if seq_no == self.expected_seq:
            ready_packets.append(packet)
            self.expected_seq = (self.expected_seq + 1) % 65536
            self.delivered_count += 1

            # Check if buffered packets are now ready
            while self.expected_seq in self.buffer:
                ready_packets.append(self.buffer[self.expected_seq])
                del self.buffer[self.expected_seq]
                self.expected_seq = (self.expected_seq + 1) % 65536
                self.delivered_count += 1
                self.reordered_count += 1
                print(f"[REORDER] Delivered buffered packet #{self.expected_seq - 1} after gap filled")

        # If packet is ahead of expected (out-of-order)
        elif self._is_ahead(seq_no):
            if len(self.buffer) < self.max_size:
                if seq_no not in self.buffer:  # Avoid duplicates
                    self.buffer[seq_no] = packet
                    gap = seq_no - self.expected_seq
                    print(f"[REORDER] Buffering packet #{seq_no}, expecting #{self.expected_seq} (gap: {gap})")
            else:
                print(f"[REORDER] Buffer full ({self.max_size}), dropping packet #{seq_no}")

        # If packet is behind expected (late duplicate)
        else:
            print(f"[REORDER] Ignoring late/duplicate packet #{seq_no}, expecting #{self.expected_seq}")

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

    def get_stats(self) -> dict:
        """Get reordering statistics"""
        return {
            'delivered': self.delivered_count,
            'reordered': self.reordered_count,
            'buffered': len(self.buffer),
            'next_expected': self.expected_seq
        }

    def reset(self):
        """Reset buffer state"""
        self.expected_seq = 0
        self.buffer.clear()
        self.delivered_count = 0
        self.reordered_count = 0