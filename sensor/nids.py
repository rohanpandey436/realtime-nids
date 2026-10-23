import json
import os
import queue
import threading
import time
import urllib.request
from collections import defaultdict, deque

from scapy.all import ARP, IP, TCP, UDP, conf, getmacbyip, sniff

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(os.path.join(HERE, "config.json")))
WINDOW = cfg["window_seconds"]
COOLDOWN = cfg["cooldown_seconds"]

counts = {"TCP": 0, "UDP": 0, "ARP": 0}
syn_by_src = defaultdict(deque)
syn_by_dst = defaultdict(deque)
ack_by_dst = defaultdict(deque)
trusted = {}
last_alert = {}
outbox = queue.Queue()
live = True


def send(path, data):
    request = urllib.request.Request(cfg["server"] + path, json.dumps(data).encode(), {"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(request, timeout=2)
    except OSError:
        print("server not reachable")


def sender():
    while True:
        path, data = outbox.get()
        send(path, data)
        outbox.task_done()


def stats():
    while True:
        time.sleep(1)
        snapshot = dict(counts)
        for name in counts:
            counts[name] = 0
        print(snapshot)
        outbox.put(("/stats", snapshot))


def trim(history, now):
    while history and now - history[0][0] > WINDOW:
        history.popleft()


def alert(kind, severity, src, dst, detail, packet, subject):
    now = float(packet.time)
    if now - last_alert.get((kind, subject), 0) < COOLDOWN:
        return
    last_alert[(kind, subject)] = now
    record = {"type": kind, "severity": severity, "src": src, "dst": dst, "detail": detail,
              "time": time.strftime("%H:%M:%S", time.localtime(now))}
    if live:
        record["latency_ms"] = round((time.time() - now) * 1000)
    print("ALERT", record)
    outbox.put(("/alert", record))


def check_tcp(packet):
    ip, tcp = packet[IP], packet[TCP]
    now = float(packet.time)
    if tcp.flags == "S":
        history = syn_by_src[ip.src]
        history.append((now, tcp.dport))
        trim(history, now)
        ports = {port for _, port in history}
        if len(ports) > cfg["port_scan_ports"]:
            alert("Port Scan", "medium", ip.src, ip.dst, "%d ports in %d s" % (len(ports), WINDOW), packet, ip.src)
        syns = syn_by_dst[ip.dst]
        syns.append((now, tcp.dport))
        trim(syns, now)
        trim(ack_by_dst[ip.dst], now)
        completed = len(ack_by_dst[ip.dst])
        target_ports = {port for _, port in syns}
        if len(syns) >= cfg["syn_flood_syns"] and len(target_ports) <= 3 and completed < len(syns) / 10:
            alert("SYN Flood", "high", ip.src, ip.dst, "%d SYN, %d completed" % (len(syns), completed), packet, ip.dst)
    elif "A" in tcp.flags and "R" not in tcp.flags:
        ack_by_dst[ip.dst].append((now, tcp.dport))


def check_arp(packet):
    arp = packet[ARP]
    known = trusted.get(arp.psrc)
    if arp.op == 2 and known and arp.hwsrc.lower() != known.lower():
        alert("ARP Spoofing", "critical", arp.psrc, arp.pdst, "MAC changed from %s to %s" % (known, arp.hwsrc), packet, arp.psrc)


def handle(packet):
    for name, layer in (("TCP", TCP), ("UDP", UDP), ("ARP", ARP)):
        if packet.haslayer(layer):
            counts[name] += 1
    if packet.haslayer(IP) and packet.haslayer(TCP):
        check_tcp(packet)
    elif packet.haslayer(ARP):
        check_arp(packet)


def learn_gateway():
    mac = cfg["gateway_mac"] or getmacbyip(cfg["gateway"])
    if mac:
        trusted[cfg["gateway"]] = mac
        print("trusted gateway", cfg["gateway"], "at", mac)
    else:
        print("gateway MAC unknown, ARP rule is off")


if __name__ == "__main__":
    learn_gateway()
    threading.Thread(target=sender, daemon=True).start()
    threading.Thread(target=stats, daemon=True).start()
    print("NIDS sensor started on", cfg["interface"], "press Ctrl+C to stop")
    sniff(iface=[cfg["interface"], conf.loopback_name], filter="(tcp or udp or arp) and not port 3000", prn=handle, store=False)
