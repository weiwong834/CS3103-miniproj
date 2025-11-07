SENDER_PORT = 8888
EMULATOR_PORT = 9999
RECEIVER_PORT = 8889
HEADER_SIZE = 7
CHANNEL_RELIABLE = 0
CHANNEL_UNRELIABLE = 1
# ACK and NACK are not separate channels - they use CHANNEL_RELIABLE with special payload
RETRANSMIT_TIMEOUT = 0.15  # 150ms - Faster retransmission for high loss
MAX_RETRANSMITS = 12  # 13 total attempts - handles up to 40% loss well
REORDER_BUFFER_SIZE = 500  # Max out-of-order packets to buffer
REORDER_TIMEOUT = 2.0  # 2000ms - Allows time for all retransmit attempts
DUP_ACK_THRESHOLD = 3  # Number of duplicate ACKs to trigger fast retransmit 