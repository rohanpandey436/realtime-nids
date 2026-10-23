# NIDS Build Roadmap

**Update, 9 October 2026:** the round 1 demo was built in a simpler layout than the one below: one sensor file (`sensor/nids.py`), one server file (`server/server.js`) and one page (`server/public/index.html`). Steps 0 to 12 are covered in that simpler form, except the config file, the separate parser and the queue thread. For what is built and what comes next, read `EVALUATION_1_GUIDE.md`, sections 1 and 14. Steps 13 onwards below still apply.

Every step says what to build, what to learn first, and how you know it is done. Do them in order. Commit to git after every step that works. No step contains code: you write all of it.

## Target folder layout

```
nids-project/
  sensor/            Python side
    config.json      interface name, server URL, thresholds
    capture.py       sniffing and per-second counters
    parser.py        packet to plain dictionary
    rules/
      portscan.py
      synflood.py
      arpspoof.py
    alerts.py        alert record, cool-down, sender thread
    main.py          wires everything together
  tests/             unittest files, one per rule
  server/            Node side
    server.js
    public/
      index.html
      style.css
      dashboard.js
    logs/alerts.log
  docs/              schema notes, test results, screenshots
```

---

## Phase A: Setup (week 4, day 1)

- [ ] **Step 0. Tools.** Install Nmap with Npcap (tick WinPcap compatible mode), Wireshark, Git. Create the venv, install Scapy, run git init, add .gitignore, create the folders above, write a README stating all code is yours.
  - Done when: an Administrator terminal captures five packets with Scapy and prints their summaries.

- [ ] **Step 1. Config file.** A JSON file holding the interface name, the server URL, and every threshold and window length (port scan 15 ports in 5 s, cool-down 30 s, SYN flood values, stats interval 1 s).
  - Learn: Python json module, reading a file, dictionaries.
  - Done when: a tiny loader function returns the settings and fails with a clear message if the file is missing or a key is absent.

## Phase B: Sensor basics (week 4)

- [ ] **Step 2. Capture and count.** Callback that checks each packet for TCP, UDP or ARP with haslayer and increments counters. Start sniff with your interface, the callback, store off, and the BPF filter "tcp or udp or arp".
  - Learn: sniff parameters, haslayer, BPF syntax, handling Ctrl+C.
  - Done when: counts rise when you browse and ping your router, and match Wireshark roughly.

- [ ] **Step 3. Parser.** Function that turns one packet into a dictionary: time, src and dst IP, protocol, src and dst port, TCP flags, and for ARP the op code, sender IP and sender MAC. Missing fields become None.
  - Learn: reading fields from layers, TCP flags attribute, ARP fields psrc, hwsrc, op.
  - Done when: printing only packets whose flags are exactly SYN matches Wireshark's SYN filter. Write the dictionary fields into docs/packet_schema.md.

- [ ] **Step 4. Stats thread.** Move the once-per-second printing into its own thread that wakes every second, reads and resets the counters, and prints packets per second by protocol.
  - Learn: threading.Thread, daemon threads, threading.Lock (callback and thread share the counters).
  - Done when: a line prints every second even when no packets arrive.

## Phase C: First two rules (week 5)

- [ ] **Step 5. Port-scan rule.** Dictionary from source IP to a deque of (time, dst port), fed only by pure SYN packets. On each SYN: append, pop from the left while older than the window, count distinct ports, alert above the threshold, then start a cool-down for that source.
  - Learn: collections.deque, defaultdict, sets for distinct counting, time.monotonic.
  - Done when: a unit test that feeds 20 crafted SYNs to 20 ports produces exactly one alert, and a test with 10 ports produces none.

- [ ] **Step 6. SYN-flood rule.** Per destination IP, a deque of SYN times and a count of completed handshakes (packets with ACK set and SYN clear). Alert when SYNs in the window pass the threshold while completions stay near zero.
  - Learn: TCP handshake states, why floods never complete.
  - Done when: a test with 200 SYNs and no ACKs alerts; a test with 200 SYNs each followed by an ACK does not.

- [ ] **Step 7. Alerts module.** One function builds an alert dictionary (type, severity, src, dst, value that fired, threshold, message, time). A queue receives alerts; a worker thread takes them off and, for now, just prints them.
  - Learn: queue.Queue, producer and consumer pattern.
  - Done when: rules no longer print directly; everything flows through the queue.

- [ ] **Step 8. main.py.** Loads config, starts the stats thread and the alert worker, starts sniff with a callback that parses the packet and passes it to each rule.
  - Done when: an Nmap scan from a second device or VM against your laptop's Wi-Fi IP prints a port-scan alert.

## Phase D: Server and dashboard (week 6, mid-term)

- [ ] **Step 9. Express server.** npm init, install express. Routes: POST /api/alerts validates required fields, adds a server timestamp, appends one JSON line to logs/alerts.log, replies with a status. GET /api/alerts returns the last 50 alerts. Serve the public folder as static files.
  - Learn: express.json middleware, route handlers, fs.appendFile, HTTP status codes 201 and 400.
  - Done when: a request from Postman or a Python shell adds a line to the log and bad JSON gets a 400.

- [ ] **Step 10. Sensor sends alerts.** The worker thread now posts each alert as JSON with urllib.request. If the server is down, catch the error and keep going; the sensor must never crash because the server is off.
  - Learn: urllib.request.Request, headers, try and except for URLError.
  - Done when: a scan produces a new line in alerts.log.

- [ ] **Step 11. Socket.IO.** Install socket.io, attach it to the HTTP server. After saving an alert, emit an "alert" event. Add POST /api/stats that the stats thread calls once a second and emit a "stats" event.
  - Learn: http.createServer with Express, io.emit, connection event.
  - Done when: two open browser tabs both receive events.

- [ ] **Step 12. Basic dashboard.** index.html with a stats area, an alert list and a hidden red banner. dashboard.js connects, updates the numbers on "stats", and on "alert" adds a list item and shows the banner for a few seconds. On page load, fetch GET /api/alerts to show history.
  - Learn: socket.io client script, fetch, DOM createElement, setTimeout.
  - Done when: **mid-term demo works**: live counters plus a port-scan banner when your laptop is scanned.

## Phase E: Complete the system (weeks 7 and 8)

- [ ] **Step 13. ARP-spoof rule.** At start-up find the gateway IP from Scapy's routing table and its MAC with a normal ARP lookup; store both plus your own IP and MAC in a trust table. On every ARP reply, alert critical if a trusted IP arrives with a different MAC. Also count ARP replies per second as a warning signal.
  - Learn: conf.route, getmacbyip, ARP op codes 1 and 2, man-in-the-middle concept.
  - Done when: unit test with a forged reply alerts; a genuine reply does not.

- [ ] **Step 14. Dashboard polish.** Protocol chart with Chart.js updated every second, alert history table, severity colours (low, medium, critical), alert counter per type, connection status indicator.
  - Done when: it looks clean enough for screenshots in the report.

- [ ] **Step 15. Integration testing.** Attacker VM or second device on your own Wi-Fi only. Run each attack three times and record: time from attack start to banner, whether it fired once or repeated, and the counter value. Then 10 minutes of normal browsing and a video to count false positives. Record CPU and memory of the sensor.
  - Done when: docs/test_results.md has a table for every test, with screenshots.

- [ ] **Step 16. Hardening.** Validate config values, handle a wrong interface name with a clear message, add a clean shutdown for both threads, make the server reject oversized or malformed payloads, tune thresholds from step 15 and write down why.

## Phase F: Report and viva (weeks 9 and 10)

- [ ] **Step 17. Diagrams.** Level-0 and level-1 DFD, use-case, sequence diagram from packet to banner, module diagram, deployment diagram. Draw them in draw.io yourself.
- [ ] **Step 18. Report.** 40 pages in the college format, your own words, screenshots and test tables from step 15. Run the plagiarism check early.
- [ ] **Step 19. PPT and rehearsal.** 10 to 12 slides. Rehearse the live demo with the VM attacker at least twice, and keep a screen recording as backup in case the demo network fails.
- [ ] **Step 20. Viva prep.** For every file, be able to explain each function, why each data structure was chosen, and what happens when a packet arrives.

---

## Weekly logbook template

Date. What I built. What I learned. What broke and how I fixed it. What is next.
