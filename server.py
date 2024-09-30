import socket
import select
import json
import ssl
import signal
from auth import AuthManager

BACKLOG = 5
USERS_FILE = "users.json"


class Server:
    def __init__(self, host, port):
        self.clients = {}  # {client_socket: {'username': str, 'address': tuple}}
        self.auth_manager = AuthManager(USERS_FILE)

        # Create a raw socket
        raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        raw_socket.bind((host, port))
        raw_socket.listen(BACKLOG)
        raw_socket.setblocking(False)

        # Wrap the raw socket in an SSL socket
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
        self.server_socket = context.wrap_socket(raw_socket, server_side=True)

        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signal, frame):
        print("Server is shutting down...")
        self.server_socket.close()
        for client_socket in self.clients:
            client_socket.close()
        exit(0)

    def broadcast(self, message, sender_socket):
        for client_socket in self.clients:
            if client_socket != sender_socket:
                try:
                    json_string = json.dumps(
                        {
                            "type": "message",
                            "username": self.clients[sender_socket]["username"],
                            "message": message,
                        }
                    )
                    client_socket.send(json_string.encode())
                except socket.error:
                    self.remove_client(client_socket)

    def remove_client(self, client_socket):
        if client_socket in self.clients:
            print(f"Client {self.clients[client_socket]['username']} disconnected")
            del self.clients[client_socket]
            client_socket.close()

    def handle_client(self, client_socket):
        try:
            message = client_socket.recv(1024).decode()
            if not message:
                self.remove_client(client_socket)
                return

            json_data = json.loads(message)
            message_type = json_data["type"]

            if message_type == "login":
                username = json_data["username"]
                password = json_data["password"]
                if self.auth_manager.authenticate_user(username, password):
                    self.clients[client_socket]["username"] = username
                    print(f"User {username} logged in")
                    client_socket.send(json.dumps({"type": "login_success"}).encode())
                else:
                    print(f"Login failed for user {username}")
                    client_socket.send(json.dumps({"type": "login_failed"}).encode())
            elif message_type == "register":
                username = json_data["username"]
                password = json_data["password"]
                if self.auth_manager.register_user(username, password):
                    print(f"New user {username} registered")
                    client_socket.send(
                        json.dumps({"type": "register_success"}).encode()
                    )
                else:
                    print(f"Registration failed for user {username}")
                    client_socket.send(json.dumps({"type": "register_failed"}).encode())
            elif message_type == "message":
                content = json_data["message"]
                print(f"Received message: {content}")
                self.broadcast(content, client_socket)
            else:
                self.remove_client(client_socket)

        except socket.error:
            self.remove_client(client_socket)

    def run(self):
        print("Server started, waiting for connections...")
        while True:
            readable_sockets, _, exceptional_sockets = select.select(
                [self.server_socket] + list(self.clients.keys()),
                [],
                list(self.clients.keys()),
            )

            for notified_socket in readable_sockets:
                if notified_socket == self.server_socket:
                    client_socket, client_address = self.server_socket.accept()
                    print(f"New connection from {client_address}")
                    self.clients[client_socket] = {
                        "username": None,
                        "address": client_address,
                    }
                else:
                    self.handle_client(notified_socket)

            for notified_socket in exceptional_sockets:
                self.remove_client(notified_socket)


if __name__ == "__main__":
    server = Server("localhost", 1234)
    server.run()
