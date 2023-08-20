import socket

# Create a UDP socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Send a message to IP address 127.0.0.1 and port 8888
message = "Hello, server!"
client_socket.sendto(message.encode(), ('127.0.0.1', 30000))
