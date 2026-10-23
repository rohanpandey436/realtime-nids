import socket

for port in range(1, 101):
    s = socket.socket()
    s.settimeout(0.05)
    s.connect_ex(("127.0.0.1", port))
    s.close()

print("knocked on 100 ports of 127.0.0.1")
