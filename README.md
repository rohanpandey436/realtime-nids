# Real-Time Network Intrusion Detection System (NIDS)

A lightweight, real-time NIDS that captures live network traffic, detects three common attacks
using transparent rules, and shows alerts on a web dashboard within about a second.

B.Tech CSE mini project. Repository: https://github.com/rohanpandey436/realtime-nids

## What it detects

| Attack | Rule |
|---|---|
| Port scan | One source contacts more than 15 distinct ports in a 5-second window |
| SYN flood | 100+ half-open handshakes to one host with almost no completions |
| ARP spoofing | A trusted gateway address appears with a different MAC address |

No machine learning is used: every alert can be traced to a counter and a threshold.

## Architecture

```
Network -> Sniffer (Python + Scapy) -> Rule engine -> HTTP POST (JSON)
        -> Server (Node.js + Express) -> alerts.log
        -> Socket.IO -> Live dashboard (HTML/CSS/JS + Chart.js)
```

## Project layout

- `sensor/` : Python sensor (`nids.py`), config and the two test scripts
- `server/` : Node.js server (`server.js`) and the dashboard in `public/`
- `tests/`  : automated unit tests for the three rules
- `design/` : DFDs, use-case, sequence, component, deployment diagrams and screenshots
- `report/` : the mini-project report (DOCX and PDF)
- `synopsis/` : the approved synopsis

## Requirements

- Windows with Npcap installed (loopback support on)
- Python 3 with Scapy: `pip install scapy`
- Node.js, then inside `server`: `npm install`

## Run

```bash
# terminal 1
cd server
node server.js

# terminal 2
cd sensor
python nids.py

# terminal 3 (generate a test attack)
cd sensor
python scan_test.py      # port scan
python flood_test.py     # SYN flood
```

Open http://localhost:3000 to see the dashboard.

## Tests

```bash
python -m unittest tests.test_rules -v
```

All ten tests should pass.

## Configuration

Thresholds and the interface name are in `sensor/config.json`, so they can be changed
without editing the code.
