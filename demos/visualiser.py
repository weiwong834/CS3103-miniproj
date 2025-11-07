import re
import matplotlib.pyplot as plt
from collections import defaultdict

# Load your log file
with open('test_log.txt', 'r', encoding='utf-16') as f:
    logs = f.read()
    print(logs)


# ✅ Fix 1: Match "R#0" or "#0" and capture Total latency
latency_pattern = r'\[ACK\]\s+Received ACK for packet\s+R?#(\d+)\s+\(RTT:\s*[\d.]+ms,\s*Total:\s*([\d.]+)ms\)'
latency_matches = re.findall(latency_pattern, logs)

test_line = "[ACK] Received ACK for packet R#4 (RTT: 30.5ms, Total: 667.0ms)"
print(re.search(latency_pattern, test_line)) 

packet_ids = [int(m[0]) for m in latency_matches]
latencies = [float(m[1]) for m in latency_matches]

print(f"Found {len(latency_matches)} latency entries")

# ✅ Fix 2: Retransmission regex (already correct, but verify)
retransmit_pattern = r'\[RETRANSMIT\] Packet R?#(\d+) lost, attempt (\d+)/\d+'
retransmit_matches = re.findall(retransmit_pattern, logs)

print(f"Found {len(retransmit_matches)} retransmission entries")

retransmit_count = defaultdict(int)
for packet_id, attempt in retransmit_matches:
    retransmit_count[int(packet_id)] += 1

# Include all packets from latency data, even if they have 0 retransmissions
if packet_ids:
    all_packet_ids = sorted(set(packet_ids))
    retransmit_attempts = [retransmit_count.get(pid, 0) for pid in all_packet_ids]
    retransmit_packet_ids = all_packet_ids
else:
    retransmit_packet_ids = list(retransmit_count.keys())
    retransmit_attempts = list(retransmit_count.values())

# Plot only if data exists
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

if packet_ids:
    ax1.scatter(packet_ids, latencies, alpha=0.7, color='blue')
    ax1.set_title('Packet Latency (ms)')
    ax1.set_xlabel('Packet ID')
    ax1.set_ylabel('Latency (ms)')
    ax1.grid(True)
else:
    ax1.text(0.5, 0.5, 'No latency data found', ha='center', va='center')
    ax1.set_title('Packet Latency (ms)')

if retransmit_packet_ids:
    colors = ['green' if count == 0 else 'red' for count in retransmit_attempts]
    ax2.bar(retransmit_packet_ids, retransmit_attempts, color=colors, alpha=0.7)
    ax2.set_title('Retransmission Attempts per Packet')
    ax2.set_xlabel('Packet ID')
    ax2.set_ylabel('Number of Retries')
    ax2.grid(True)
else:
    ax2.text(0.5, 0.5, 'No retransmission data found', ha='center', va='center')
    ax2.set_title('Retransmission Attempts')

plt.tight_layout()
plt.savefig('metrics.png', dpi=150)
plt.show()