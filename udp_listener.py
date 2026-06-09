import socket

IP = "0.0.0.0"
PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((IP, PORT))

print(f"Listening on {IP}:{PORT}")
print("Press Ctrl+C to stop")

try:
    while True:
        data, addr = sock.recvfrom(65535)

        print("\nReceived:")
        print(data.decode("utf-8"))

except KeyboardInterrupt:
    print("\nStopping listener...")

finally:
    sock.close()
    print("Socket closed.")