# NIDS Mini Project: Briefing for the Guide Meeting

Everything below is what you should be able to say, in your own words, before you hand over the synopsis. Read it twice, then close it and explain the project aloud to yourself.

## 1. The one-minute pitch

"My project is a real-time Network Intrusion Detection System for small networks such as a home, hostel or lab. A Python program captures every packet on my laptop's Wi-Fi interface using Scapy. A rule engine that I write myself looks for three attack patterns: port scans, SYN floods and ARP spoofing. Every alert is sent as JSON to a Node.js server, which pushes it instantly to a browser dashboard over Socket.IO, so the threat appears as a red banner within a second. I deliberately avoid machine learning so that every alert can be traced to a counter and a packet, and I can explain every line in the viva."

## 2. Why this problem matters

- Small networks have no monitoring at all. A router log is not a detection system.
- Wireshark captures everything but only for manual, after-the-fact analysis. It never raises an alert.
- Snort and Zeek are powerful production tools, but they need large rule sets in their own syntax, expert tuning, and they report to text logs, not a live screen.
- Machine-learning prototypes score well on old datasets such as KDD Cup 99, but their decisions cannot be explained and they are rarely deployed.
- Commercial appliances have dashboards but cost too much for students and small offices.
- The gap: something light enough for a laptop, transparent enough to explain, and immediate enough to show a threat within a second.

## 3. Concepts you must be able to explain

- **IDS vs IPS vs firewall.** A firewall decides what is allowed through. An IPS blocks what it detects. An IDS is passive: it only watches and reports. Your project is an IDS, which is why it is safe to run on a live network.
- **NIDS vs HIDS.** A NIDS watches packets on the wire. A HIDS watches one machine's logs and processes. Yours is a NIDS running on one host.
- **Signature vs anomaly detection.** Signature: match known patterns or rules. Anomaly: model normal behaviour and flag deviations. Your rules are threshold signatures, a form of signature detection with counters.
- **Packet layers.** Ethernet frame carries an IP packet, which carries a TCP or UDP segment. ARP sits directly on Ethernet and has no IP header. Scapy exposes each layer as an object you can test for and read fields from.
- **Promiscuous mode and switches.** Normally a network card drops frames not addressed to it. Promiscuous mode passes everything to software. On a switched network you still only receive broadcast traffic, traffic to your own machine, and anything the switch floods or mirrors. Wi-Fi in managed mode behaves like a switch. That is why your test attacks target the monitoring laptop itself.
- **TCP three-way handshake.** Client sends SYN, server replies SYN-ACK, client sends ACK. Flags are bits in the TCP header: SYN is 0x02, ACK is 0x10, so SYN-ACK is 0x12. RST is 0x04 and FIN is 0x01.
- **Half-open connection.** A SYN that the server answered but never received the final ACK for. The server holds it in a backlog queue with a timer. A flood of these fills the queue and legitimate clients get refused.
- **ARP.** Address Resolution Protocol maps an IP address to a MAC address on the local network. A request is opcode 1, a reply is opcode 2. ARP has no authentication and hosts accept replies they never asked for, which is what spoofing exploits.
- **Sliding window vs fixed window.** A fixed window resets every N seconds, so an attack split across the boundary is missed. A sliding window keeps a timestamped list of recent events and drops anything older than N seconds on every check, so the count is always for the last N seconds.
- **HTTP POST vs WebSocket.** POST is a one-shot request and response, good for the Python sensor to hand an alert to the server. A WebSocket is a persistent two-way connection, good for the server to push to browsers without them polling. Socket.IO wraps WebSocket with automatic reconnection and named events.

## 4. Architecture and the journey of one packet

1. The Wi-Fi card, through the Npcap driver, delivers a raw frame to Scapy's sniff function.
2. A Berkeley Packet Filter such as "tcp or udp or arp" runs inside the driver so Python only sees relevant frames.
3. Scapy calls your callback function once per packet with a decoded packet object.
4. The Sniffer Engine extracts the fields you need: source and destination IP, ports, TCP flags, ARP opcode and addresses, plus a timestamp. It also increments per-second counters for the dashboard.
5. The Threat Detection Module runs each rule on those fields. Rules keep their own state in dictionaries and deques.
6. When a rule fires, it builds an alert record and drops it on an internal queue. A separate worker thread sends the queue contents by HTTP POST, so the capture loop is never blocked by network delays.
7. The Express server validates the JSON, adds a server timestamp, appends one line to alerts.log, and emits a Socket.IO event to all connected browsers.
8. The dashboard's JavaScript receives the event and updates the DOM: a red banner, a row in the history table, and the live charts.

A sensible alert record has: type, severity, source IP, destination IP or port list, the counter value and threshold that fired, a human-readable message, and the sensor timestamp.

## 5. The three rules

### Port scan

- State: a dictionary from source IP to a deque of pairs (timestamp, destination port), recording only packets whose TCP flag is exactly SYN.
- On each SYN: append the pair, pop from the front while the oldest timestamp is older than 5 seconds, count the distinct ports in what remains. If the count exceeds 15, raise an alert and start a 30-second cool-down for that source so you do not raise hundreds of duplicates.
- Why SYN only: a scanner sends a SYN to every port. Normal browsing opens connections to a few ports, mostly 80 and 443, on many different hosts, so it never reaches 15 distinct ports on one host.
- Why 15 in 5 seconds: Nmap's default scan touches 1000 ports in seconds, so any real scan crosses the threshold immediately, while legitimate software stays far below it. The thresholds live in a config file so you can show tuning.
- Test: run an Nmap SYN scan from a second device on your own Wi-Fi against your laptop, or a Scapy script that sends SYNs to 30 ports.

### SYN flood

- State: per destination IP, a deque of SYN timestamps, and a counter of handshakes completed, which you detect from packets with ACK set and SYN clear that follow a SYN-ACK.
- On each packet: update the window, compute SYNs in the last 2 seconds and the ratio of SYNs to completed handshakes. Alert when SYNs exceed a threshold such as 100 in the window while completions stay near zero.
- Why: a legitimate burst of connections completes handshakes; a flood never does, because the sources are spoofed or the attacker ignores the SYN-ACK. This is the imbalance idea from the SYN-flood literature and RFC 4987.
- Mitigation you should know: SYN cookies, which let a server avoid storing state until the handshake completes.
- Test: a Scapy script on a second device sending a few hundred SYNs with random source ports to your laptop. Never point this at anything you do not own.

### ARP spoofing

- State: a trust table from IP address to MAC address. At start-up learn the gateway's IP from the routing table and its MAC with a normal ARP request, and add your own machine.
- On each ARP reply: if the sender IP is in the trust table and the sender MAC differs, raise a critical alert. Also count ARP replies per second; a burst of unsolicited replies for the gateway is itself suspicious.
- Why: the attacker keeps telling your machine that the gateway's IP now lives at the attacker's MAC, so all your traffic flows through the attacker first. This is a man-in-the-middle attack.
- Test: from a second laptop, use Scapy to craft an ARP reply that claims the gateway IP with a fake MAC, only on your own isolated Wi-Fi. This is the same principle as the arpwatch tool.

## 6. Technology choices and how to defend them

- **Scapy rather than raw sockets.** Windows raw sockets cannot capture at layer 2 and cannot see ARP. Scapy over Npcap gives full frames and decodes every layer for you, so you spend your time on detection logic.
- **Python for capture, Node.js for the web part.** Each language is used where it is strongest. The HTTP POST boundary is language-neutral, so either side can be tested alone with a tool like curl. It also demonstrates the decoupled sensor-and-server design used in real monitoring products.
- **Socket.IO rather than page polling.** Polling every second wastes requests and still delays alerts. Socket.IO pushes within milliseconds, reconnects automatically, and lets you name events such as alert and stats.
- **Rules rather than machine learning.** Rules are deterministic, explainable, need no training data, and run in real time on a laptop. You can quote the Sommer and Paxson paper on why ML intrusion detection is rarely deployed.
- **Performance.** Filter in the driver with BPF, tell Scapy not to store packets in memory, do minimal work in the callback, hand off HTTP calls to a worker thread, and send dashboard statistics once per second rather than per packet.

## 7. Testing and evaluation plan

- Ethics first: only your own laptop, your own second device, your own Wi-Fi. Never scan or flood the college network without written permission.
- Unit tests: build packets with Scapy in a test script and feed them straight into each rule function without sniffing. This proves the logic independently of the network.
- Integration tests: run the sensor, the server and the dashboard, then generate each attack and record the time from attack start to banner.
- Metrics for the report: detection latency in seconds, false positives during 10 minutes of normal browsing and streaming, CPU and memory of the sensor, packets per second handled.
- Keep screenshots and log excerpts from every test; they become figures in the 40-page report.

## 8. Diagrams you will need for the report

- Level-0 DFD: user, network, and the system as one process with alerts flowing to the dashboard.
- Level-1 DFD: capture, detect, deliver, display as separate processes with the alert log as a data store.
- Use-case diagram: administrator views dashboard, configures thresholds, reviews history.
- Sequence diagram: packet to alert to banner, showing the HTTP POST and the Socket.IO emit.
- Class or module diagram: Sniffer, RuleEngine, PortScanRule, SynFloodRule, ArpSpoofRule, AlertSender.
- Deployment diagram: laptop sensor, Node server, browser clients on the same LAN.

## 9. Questions the guide may ask

- Why not just use Snort? Snort is a large expert tool with its own rule language and no live web view. The aim is a transparent, small system whose every line I wrote and can explain.
- What is the difference between your IDS and a firewall? A firewall enforces rules on what passes. My system only observes and reports; it blocks nothing.
- What can you actually see on Wi-Fi? Broadcasts, traffic to my machine, and whatever the access point sends me. So my tests target my own laptop, which is realistic for a host-based network sensor. Full LAN coverage would need a mirror port.
- How do you avoid a flood of duplicate alerts? A cool-down per source and rule; a repeat within the cool-down updates the existing alert's counter instead of creating a new one.
- Why HTTP POST and not have Python talk to the browser directly? Separation of concerns: the sensor stays simple and can run on another machine; the server owns logging and fan-out to many browsers.
- How do you know the threshold is right? It is configurable, and week 8 measures false positives during normal use and latency during attacks, then documents the chosen values.
- What if Scapy misses packets under load? The BPF filter reduces load, the callback is minimal, and I will report the packets-per-second the sensor sustains. For a small network this is well within a laptop's capacity.
- How do you test safely? Own devices, own Wi-Fi, crafted packets, and unit tests that never touch the network.
- What is new here compared to existing work? The combination: deterministic explainable rules, a language-neutral alert pipeline, and a real-time web dashboard, sized for a small network and built from first principles.
- What will you show at mid-term? Live packet counters on the dashboard and a port-scan alert appearing when I scan my laptop from my phone.

## 10. Handing over the synopsis

Say: "Sir, this is my synopsis in the department format. The cover, index and seven sections follow the template. Section 2 has seven objectives; the work plan in Section 5 is mapped to the ten-week milestones including the week 6 mid-term demo; the references are numbered and cited in the text." Then ask two things: whether the designation printed under the guide's name is correct, and whether the title wording is acceptable as it will be locked in week 3.

## 11. Before you print

- Confirm the guide's designation and correct it on the cover if needed.
- Open each web reference once so the access date is honest.
- Print single-sided on A4, sign on the index page, get the guide's signature, submit the original and keep a photocopy for the logbook file.
