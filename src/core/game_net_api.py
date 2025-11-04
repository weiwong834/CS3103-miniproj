import socket
import time
import threading
from .packet import GamePacket
from .constants import *
from ..reliability.reorder_buffer import ReorderBuffer
from ..reliability.reliable_channel import ReliableChannel

class GameNetAPI:
    def __init__(self, host='localhost', port=8888, target_port=8889):
        self.host = host
        self.port = port
        self.target_port = target_port

        # Socket setup
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((host, port))
        self.socket.settimeout(0.1)
        self.next_seq = 0

        # Reliability components
        self.reliable_channel = ReliableChannel(self.socket)
        self.reorder_buffer = ReorderBuffer()

        # Metrics
        self.metrics = {
            'reliable_sent': 0,
            'unreliable_sent': 0,
            'reliable_received': 0,
            'unreliable_received': 0,
            'acks_sent': 0,
            'acks_received': 0,
            'total_latency': 0,
            'latency_count': 0,
            'packets_reordered': 0,
            'retransmissions': 0
        }

        # Receive thread for background ACK processing
        self.running = True
        self.receive_buffer = []
        self.buffer_lock = threading.Lock()
        self.receiver_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receiver_thread.start()

    def send(self, data, reliable=True):
        """
        Send data with optional reliability

        Args:
            data: String data to send
            reliable: If True, use reliable channel with ACK/retransmit
        """
        channel = CHANNEL_RELIABLE if reliable else CHANNEL_UNRELIABLE
        packet = GamePacket(channel, self.next_seq, data)
        packet_bytes = packet.to_bytes()

        # Send the packet
        self.socket.sendto(packet_bytes, (self.host, self.target_port))

        # Track for retransmission if reliable
        if reliable:
            self.reliable_channel.track_packet(packet_bytes, self.next_seq, (self.host, self.target_port))
            self.metrics['reliable_sent'] += 1
            print(f"[SEND] #{self.next_seq} RELIABLE: {data[:30]}... (tracked for ACK)")
        else:
            self.metrics['unreliable_sent'] += 1
            print(f"[SEND] #{self.next_seq} UNRELIABLE: {data[:30]}...")

        self.next_seq = (self.next_seq + 1) % 65536

    def _receive_loop(self):
        """
        Background thread for receiving packets and processing ACKs
        """
        while self.running:
            try:
                data, addr = self.socket.recvfrom(1024)
                packet = GamePacket.from_bytes(data)

                if packet:
                    # Calculate latency (current time - packet timestamp)
                    current_time_ms = int(time.time() * 1000)
                    latency = max(0, current_time_ms - packet.timestamp)
                    if latency > 10000:  # If latency > 10 seconds, likely a timestamp issue
                        latency = 0  # Default to 0 for display

                    # Handle ACK packets
                    if packet.is_ack():
                        # Extract the acked sequence number from payload
                        try:
                            acked_seq = int(packet.payload.split(':')[1])
                            self.reliable_channel.acknowledge(acked_seq)
                            self.metrics['acks_received'] += 1
                        except:
                            print(f"[ACK] Invalid ACK format: {packet.payload}")

                    # Handle reliable packets - send ACK and reorder
                    elif packet.channel_type == CHANNEL_RELIABLE:
                        # Send ACK immediately
                        ack_packet = GamePacket.create_ack(packet.seq_no)
                        self.socket.sendto(ack_packet.to_bytes(), addr)
                        self.metrics['acks_sent'] += 1
                        print(f"[ACK] Sent ACK for packet #{packet.seq_no}")

                        # Add to reorder buffer
                        ready_packets = self.reorder_buffer.add_packet(packet.seq_no, packet)

                        # Add ready packets to receive buffer
                        with self.buffer_lock:
                            for p in ready_packets:
                                self.receive_buffer.append(p)
                                self.metrics['reliable_received'] += 1
                                self.metrics['total_latency'] += latency
                                self.metrics['latency_count'] += 1
                                print(f"[RECV] #{p.seq_no} RELIABLE (ordered): {p.payload[:30]}... ({latency:.1f}ms)")

                    # Handle unreliable packets - deliver immediately
                    elif packet.channel_type == CHANNEL_UNRELIABLE:
                        with self.buffer_lock:
                            self.receive_buffer.append(packet)
                            self.metrics['unreliable_received'] += 1
                            self.metrics['total_latency'] += latency
                            self.metrics['latency_count'] += 1
                            print(f"[RECV] #{packet.seq_no} UNRELIABLE: {packet.payload[:30]}... ({latency:.1f}ms)")

            except socket.timeout:
                # Check for reorder timeout periodically
                timeout_packets = self.reorder_buffer.check_timeout()
                if timeout_packets:
                    with self.buffer_lock:
                        for p in timeout_packets:
                            self.receive_buffer.append(p)
                            self.metrics['reliable_received'] += 1
                            print(f"[RECV] #{p.seq_no} RELIABLE (after timeout): {p.payload[:30]}...")
                continue
            except Exception as e:
                if self.running:
                    print(f"[ERROR] Receive loop error: {e}")

    def receive(self):
        """
        Get next packet from receive buffer (application-level receive)

        Returns:
            GamePacket or None if no packets available
        """
        with self.buffer_lock:
            if self.receive_buffer:
                return self.receive_buffer.pop(0)
        return None

    def get_metrics(self):
        """
        Get performance metrics including reliability stats
        """
        metrics = self.metrics.copy()

        # Add reliability channel stats
        channel_stats = self.reliable_channel.get_stats()
        metrics['packets_acked'] = channel_stats['acked']
        metrics['packets_retransmitted'] = channel_stats['retransmitted']
        metrics['packets_failed'] = channel_stats['failed']
        metrics['total_retry_attempts'] = channel_stats['total_retries']

        # Add reorder buffer stats
        reorder_stats = self.reorder_buffer.get_stats()
        metrics['packets_reordered'] = reorder_stats['reordered']
        metrics['packets_buffered'] = reorder_stats['buffered']

        # Calculate average latency
        if metrics['latency_count'] > 0:
            metrics['avg_latency'] = metrics['total_latency'] / metrics['latency_count']
        else:
            metrics['avg_latency'] = 0

        # Calculate packet delivery ratio
        total_sent = metrics['reliable_sent'] + metrics['unreliable_sent']
        total_received = metrics['reliable_received'] + metrics['unreliable_received']
        if total_sent > 0:
            metrics['delivery_ratio'] = (total_received / total_sent) * 100
        else:
            metrics['delivery_ratio'] = 0

        return metrics

    def close(self):
        """Clean shutdown"""
        self.running = False
        self.reliable_channel.shutdown()
        if self.receiver_thread.is_alive():
            self.receiver_thread.join(timeout=1.0)
        self.socket.close()
        print("[SHUTDOWN] GameNetAPI closed cleanly")