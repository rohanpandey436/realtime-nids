# Real-Time Network Intrusion Detection System

Captures live network packets, detects port scans and shows alerts on a live web dashboard.

## Parts

- `sensor/nids.py`: Python program that captures packets with Scapy, counts them and checks for port scans
- `sensor/scan_test.py`: test script that knocks on 100 ports of this laptop to trigger the alert
- `server/server.js`: Node.js server that receives alerts, saves them in `alerts.log` and pushes them to the browser
- `server/public/index.html`: live dashboard
- `design/`: DFD level 0, DFD level 1, use case diagram and flowchart

## Requirements

- Windows with Npcap installed (loopback support on)
- Python 3 with Scapy: `pip install scapy`
- Node.js, then inside `server`: `npm install`

## Run

1. `cd server` then `node server.js`
2. Open http://localhost:3000
3. In a second terminal: `cd sensor` then `python nids.py`
4. In a third terminal: `cd sensor` then `python scan_test.py`

## Status

Done: live capture, per-second packet counts, port scan detection, alert log, live dashboard.

Next: SYN flood detection, ARP spoofing detection, alert history on page load, testing from a second device.
