import socket
import select
import json
import ssl
import signal
from auth import AuthManager

BACKLOG = 5
USERS_FILE = "users.json"
MAX_MESSAGE_LENGTH_BYTES = 1024


class Server:
    """
    A server that handles multiple client connections using SSL encryption.
    """

    def __init__(self, host, port):
        """
        Initialize the server with given host and port.
        """
        self.clients = {}  # { client_socket: { 'username': str, 'address': tuple } }
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
        """
        Handle SIGINT (e.g. Ctrl+C) to gracefully shut down the server.
        """
        print("Server is shutting down...")
        self.server_socket.close()
        for client_socket in self.clients:
            client_socket.close()
        exit(0)

    def broadcast(self, message, sender_socket):
        """
        Send a message to all connected clients except the sender.
        """
        for client_socket in self.clients:
            # we don't want to send the message to the sender
            if client_socket == sender_socket:
                continue

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
        """
        Remove a client from the server.
        """
        if client_socket in self.clients:
            print(f"Client {self.clients[client_socket]['username']} disconnected")
            del self.clients[client_socket]
            client_socket.close()

    def handle_client(self, client_socket):
        """
        Handle all communication from a client.
        """
        try:
            message = client_socket.recv(MAX_MESSAGE_LENGTH_BYTES).decode()
            if not message:
                # client disconnected or sent empty message
                self.remove_client(client_socket)
                return

            json_data = json.loads(message)
            message_type = json_data["type"]

            if message_type == "login":
                self.handle_login(client_socket, json_data)
            elif message_type == "register":
                self.handle_register(client_socket, json_data)
            elif message_type == "message":
                self.handle_message(client_socket, json_data)
            else:
                self.remove_client(client_socket)

        except socket.error:
            self.remove_client(client_socket)

    def handle_login(self, client_socket, json_data):
        """
        Handle a login request from a client.
        """
        username = json_data["username"]
        password = json_data["password"]

        # check if username already associated with session, if so, reject login
        for client in self.clients:
            if self.clients[client]["username"] == username:
                print(f"Client {username} already logged in")
                client_socket.send(
                    json.dumps(
                        {
                            "type": "login_failed",
                            "message": "You are already logged in",
                        }
                    ).encode()
                )
                return

        # check if username and password are correct
        if self.auth_manager.authenticate_user(username, password):
            self.clients[client_socket]["username"] = username
            print(f"User {username} logged in")
            client_socket.send(json.dumps({"type": "login_success"}).encode())

        else:
            print(f"Login failed for user {username}")
            client_socket.send(
                json.dumps(
                    {
                        "type": "login_failed",
                        "message": "Incorrect username or password",
                    }
                ).encode()
            )

    def handle_register(self, client_socket, json_data):
        """
        Handle a registration request from a client.
        """
        username = json_data["username"]
        password = json_data["password"]
        if self.auth_manager.register_user(username, password):
            print(f"New user {username} registered")
            client_socket.send(json.dumps({"type": "register_success"}).encode())
        else:
            print(f"Registration failed for user {username}")
            client_socket.send(json.dumps({"type": "register_failed"}).encode())

    def handle_message(self, client_socket, json_data):
        """
        Handle a message from a client.
        """
        content = json_data["message"]
        print(
            f"Received message from {self.clients[client_socket]['username']}: {content}"
        )
        self.broadcast(content, client_socket)

    def run(self):
        """
        Run the server, listening for connections and handling client communication.
        """
        print("Server started, waiting for connections...")
        while True:
            # check for new connections, readable data, and exceptional conditions
            # timeout of 0.5 seconds to prevent blocking indefinitely
            readable_sockets, _, exceptional_sockets = select.select(
                [self.server_socket] + list(self.clients.keys()),
                [],
                list(self.clients.keys()),
                0.5,
            )

            for notified_socket in readable_sockets:
                if notified_socket == self.server_socket:
                    # new connection
                    client_socket, client_address = self.server_socket.accept()
                    print(f"New connection from {client_address}")
                    self.clients[client_socket] = {
                        "username": None,
                        "address": client_address,
                    }
                else:
                    # handle client communication
                    self.handle_client(notified_socket)

            for notified_socket in exceptional_sockets:
                self.remove_client(notified_socket)


if __name__ == "__main__":
    server = Server("localhost", 1234)
    server.run()
