## ✅ What’s Already Done (by Persons 1–3)

### Core Protocol (`src/core/`, `src/reliability/`)

- ✅ **Hybrid UDP channels** (Person 1):
  - Channel `0` = **Reliable** (with ACKs, retransmission, reordering)
  - Channel `1` = **Unreliable** (fire-and-forget)
- ✅ **7-byte header**: `| ChannelType (1B) | SeqNo (2B) | Timestamp (4B) | Payload |`
- ✅ **Reliability features** (Person 2):
  - ACK system with RTT measurement (uses reliable channel with "ACK:" prefix)
  - Duplicate ACK mechanism for fast recovery (Selective Repeat)
  - Retransmission: 150ms timeout, max 12 retries (13 total attempts)
  - Reordering buffer: delivers reliable packets **in-order**
  - Buffer timeout: skips missing reliable packets after 2000ms
- ✅ **Realistic game traffic** (Person 3):
  - Mock JSON payloads: `score_update`, `position`, `chat`, `state_save`
  - 30-second demo at ~20 packets/sec (meets spec: 10–100 pps)

### How to Test What Works

```bash
# Test basic reliability (Person 2's features)
python demo_requirements.py
# → Choose option 3: "Test all features"

# Run Person 3's advanced demo
python demos/demo_advanced.py
# → Terminal A: receiver (option 2)
# → Terminal B: sender (option 1)
```

✅ You'll see logs like:

```
[ACK] Received ACK for packet R#5 (RTT: 12.3ms)
[REORDER] Buffering packet R#7, expecting R#6 (gap: 1)
[DUP-ACK-SEND] Sent duplicate ACK for R#5
[FAST-RETRANSMIT] Immediately retransmitting R#6 after 3 duplicate ACKs
[RECV] R#6 RELIABLE (ordered): {"type":"position",...} (15.1ms)
[RECV] R#7 RELIABLE (ordered): {"type":"score_update",...} (18.2ms)
```

---

## (Person 4)

### 1. **Network Emulator** (`src/network/emulator.py`)

Simulate real-world network conditions **between sender and receiver**:

- **Packet loss**: 0% (baseline), 2% (low loss), 10%+ (high loss)
- **Delay**: Add fixed/variable latency (e.g., 50ms–200ms)
- **Jitter**: Randomize delay per packet
- **Reordering**: Artificially shuffle packet arrival order

> 💡 **Tip**: You can either:
>
> - Wrap the existing `GameNetAPI` with a proxy that injects network effects, OR
> - Use system tools like `tc` (Linux) / `clumsy` (Windows) and document them

### 2. **Metrics Collection** (`src/network/metrics.py`)

Extend `GameNetAPI.get_metrics()` to measure **separately for reliable/unreliable channels**:

- **Latency**: One-way delay (already partially implemented)
- **Jitter**: RFC 3550 definition: `J = J + (|D(i-1,i)| - J)/16`
- **Throughput**: Total bytes received / duration (bytes/sec)
- **Delivery Ratio**: `(Packets received / Packets sent) × 100%`

### 3. **Visualization** (`src/network/visualizer.py`)

Generate **comparison plots** for **at least 2 network conditions** (e.g., 0% loss vs. 10% loss):

- Latency/jitter CDF or time-series
- Throughput over time
- Delivery ratio bar chart

> 📊 Use `matplotlib` or export CSV for Excel

### 4. **Integration**

- Ensure your emulator works with `demo_advanced.py`
- Add command-line args to control loss/delay (e.g., `--loss 10 --delay 100`)

---

## 📁 Key Files You’ll Work On

```
src/network/
├── emulator.py      # Your network simulator
├── metrics.py       # Enhanced metrics (jitter, throughput, etc.)
└── visualizer.py    # Plotting/generation of results
```
