import socket

for _ in range(300):
    s = socket.socket()
    s.settimeout(0.02)
    s.connect_ex(("127.0.0.1", 9))
    s.close()

print("sent 300 connection attempts to port 9 of 127.0.0.1")
