import time
from .constants import HEADER_SIZE, CHANNEL_RELIABLE

class GamePacket:
    def __init__(self, channel_type, seq_no, payload, timestamp=None):
        self.channel_type = channel_type
        self.seq_no = seq_no
        self.payload = payload
        if timestamp is None:
            self.timestamp = int(time.time() * 1000)
        else:
            self.timestamp = timestamp

    def to_bytes(self):
        """7-byte header"""
        header = bytes([
            self.channel_type,
            (self.seq_no >> 8) & 0xFF,
            self.seq_no & 0xFF,
            (self.timestamp >> 24) & 0xFF,
            (self.timestamp >> 16) & 0xFF,
            (self.timestamp >> 8) & 0xFF,
            self.timestamp & 0xFF
        ])
        return header + self.payload.encode('utf-8')

    def is_ack(self):
        """Check if this is an ACK packet (reliable channel with ACK: prefix)"""
        return self.channel_type == CHANNEL_RELIABLE and self.payload.startswith("ACK:")

    def is_control_packet(self):
        """Check if this is a control packet (ACK or other control messages)"""
        return self.channel_type == CHANNEL_RELIABLE and self.payload.startswith("ACK:")

    @classmethod
    def create_ack(cls, seq_no):
        """Create an ACK packet for the given sequence number"""
        # ACK uses CHANNEL_RELIABLE with special payload prefix
        return cls(CHANNEL_RELIABLE, seq_no, f"ACK:{seq_no}")

    @classmethod
    def from_bytes(cls, data):
        if len(data) < HEADER_SIZE:
            return None
        channel_type = data[0]
        seq_no = (data[1] << 8) | data[2]
        timestamp = (data[3] << 24) | (data[4] << 16) | (data[5] << 8) | data[6]
        payload = data[HEADER_SIZE:].decode('utf-8')
        return cls(channel_type, seq_no, payload, timestamp)