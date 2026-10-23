import os
import queue
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sensor"))
import nids
from scapy.all import ARP, Ether, IP, TCP

GATEWAY = nids.cfg["gateway"]
GOOD_MAC = "aa:bb:cc:dd:ee:01"
BAD_MAC = "de:ad:be:ef:00:01"
VICTIM = "192.168.29.171"


def tcp(src, dst, dport, flags, t, sport=40000):
    p = Ether() / IP(src=src, dst=dst) / TCP(sport=sport, dport=dport, flags=flags)
    p.time = t
    return p


def arp(op, ip, mac, t):
    p = Ether(src=mac) / ARP(op=op, psrc=ip, hwsrc=mac, pdst=VICTIM)
    p.time = t
    return p


class RuleTests(unittest.TestCase):
    def setUp(self):
        for store in (nids.syn_by_src, nids.syn_by_dst, nids.ack_by_dst, nids.last_alert, nids.trusted):
            store.clear()
        nids.trusted[GATEWAY] = GOOD_MAC
        nids.outbox = queue.Queue()
        nids.live = False

    def alerts(self):
        found = []
        while not nids.outbox.empty():
            path, data = nids.outbox.get()
            if path == "/alert":
                found.append(data)
        return found

    def test_port_scan_fires_once(self):
        for port in range(1, 21):
            nids.handle(tcp("10.0.0.5", VICTIM, port, "S", 100 + port * 0.01))
        found = self.alerts()
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["type"], "Port Scan")
        self.assertEqual(found[0]["severity"], "medium")
        self.assertEqual(found[0]["src"], "10.0.0.5")

    def test_few_ports_no_alert(self):
        for port in range(1, 11):
            nids.handle(tcp("10.0.0.5", VICTIM, port, "S", 100 + port * 0.01))
        self.assertEqual(self.alerts(), [])

    def test_syn_ack_replies_are_ignored(self):
        for port in range(1, 31):
            nids.handle(tcp(VICTIM, "10.0.0.5", port, "SA", 100 + port * 0.01))
        self.assertEqual(self.alerts(), [])

    def test_slow_scan_stays_under_window(self):
        for port in range(1, 31):
            nids.handle(tcp("10.0.0.5", VICTIM, port, "S", 100 + port * 1.0))
        self.assertEqual(self.alerts(), [])

    def test_cooldown_blocks_repeat_alert(self):
        for port in range(1, 21):
            nids.handle(tcp("10.0.0.5", VICTIM, port, "S", 100 + port * 0.01))
        for port in range(100, 140):
            nids.handle(tcp("10.0.0.5", VICTIM, port, "S", 110 + port * 0.01))
        self.assertEqual(len(self.alerts()), 1)
        for port in range(200, 240):
            nids.handle(tcp("10.0.0.5", VICTIM, port, "S", 150 + port * 0.01))
        self.assertEqual(len(self.alerts()), 1)

    def test_syn_flood_fires(self):
        for i in range(120):
            nids.handle(tcp("10.0.%d.%d" % (i // 250, i % 250 + 1), VICTIM, 80, "S", 200 + i * 0.01, sport=1000 + i))
        found = self.alerts()
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["type"], "SYN Flood")
        self.assertEqual(found[0]["severity"], "high")

    def test_completed_handshakes_are_not_a_flood(self):
        for i in range(120):
            t = 200 + i * 0.01
            nids.handle(tcp("10.0.0.5", VICTIM, 80, "S", t, sport=1000 + i))
            nids.handle(tcp(VICTIM, "10.0.0.5", 1000 + i, "SA", t + 0.001, sport=80))
            nids.handle(tcp("10.0.0.5", VICTIM, 80, "A", t + 0.002, sport=1000 + i))
        self.assertEqual(self.alerts(), [])

    def test_port_scan_is_not_reported_as_flood(self):
        for port in range(1, 121):
            nids.handle(tcp("10.0.0.5", VICTIM, port, "S", 300 + port * 0.01))
        found = self.alerts()
        self.assertEqual([a["type"] for a in found], ["Port Scan"])

    def test_arp_spoof_fires(self):
        nids.handle(arp(2, GATEWAY, BAD_MAC, 400))
        found = self.alerts()
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["type"], "ARP Spoofing")
        self.assertEqual(found[0]["severity"], "critical")
        self.assertEqual(found[0]["src"], GATEWAY)

    def test_genuine_arp_traffic_is_ignored(self):
        nids.handle(arp(2, GATEWAY, GOOD_MAC, 400))
        nids.handle(arp(1, GATEWAY, BAD_MAC, 401))
        nids.handle(arp(2, "192.168.29.77", BAD_MAC, 402))
        self.assertEqual(self.alerts(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
