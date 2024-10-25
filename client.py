import socket
import threading
import json
import ssl
import os
from colorama import Style, Fore

CLEAR_SCREEN = "\033[2J"
MOVE_CURSOR = "\033[{};{}H"
CLEAR_LINE = "\033[K"
INPUT_PROMPT = "You: "
MAX_MESSAGE_LENGTH_BYTES = 1024
PORT = 3000


class Client:
    """
    A client that connects to a server and allows for user registration and login.
    """

    def __init__(self, host, port):
        """
        Initialize the client with given host and port.
        """
        self.username = None
        self.logged_in = False
        self.messages = []
        self.error = None

        # Create a raw socket
        raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Wrap the raw socket in an SSL socket
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations("cert.pem")
        self.client_socket = context.wrap_socket(raw_socket, server_hostname=host)

        self.client_socket.connect((host, port))
        message = self.client_socket.recv(MAX_MESSAGE_LENGTH_BYTES).decode()
        json_data = json.loads(message)
        if json_data["type"] == "connection_failed":
            self.print_error(json_data["message"])
            exit(1)

    def clear_screen(self):
        """
        Clear the terminal screen.
        """
        print(CLEAR_SCREEN, end="")
        self.move_cursor(1, 1)

    def move_cursor(self, row, col):
        """
        Move the cursor to the specified row and column.
        """
        print(MOVE_CURSOR.format(row, col), end="")

    def clear_line(self):
        """
        Clear the current line.
        """
        print(CLEAR_LINE, end="")

    def print_error(self, message):
        """
        Print an error message in red.
        """
        print(Fore.RED + message + Style.RESET_ALL)

    def print_success(self, message):
        """
        Print a success message in green.
        """
        print(Fore.GREEN + message + Style.RESET_ALL)

    def refresh_display(self):
        """
        Refresh the display with the latest messages.
        """
        self.clear_screen()
        height, _ = os.get_terminal_size()
        for i, message in enumerate(self.messages[-height + 2 :]):
            self.move_cursor(i + 1, 1)
            if message.startswith(INPUT_PROMPT):
                print(Style.DIM + message + Style.RESET_ALL)
            else:
                print(message)
        if self.error:
            self.print_error(self.error)
            self.error = None
        self.move_cursor(height, 1)
        print("> ", end="", flush=True)

    def send_message(self, message):
        """
        Send a message to the server.
        """
        try:
            self.client_socket.send(message.encode())
        except socket.error as e:
            print(f"Error sending message: {e}")

    def register(self):
        """
        Register a new user.
        """
        username = input("Enter a new username: ")
        password = input("Enter a password: ")
        register_message = json.dumps(
            {"type": "register", "username": username, "password": password}
        )
        self.send_message(register_message)

        message = self.client_socket.recv(MAX_MESSAGE_LENGTH_BYTES).decode()
        json_data = json.loads(message)
        if json_data["type"] == "register_success":
            self.clear_screen()
            self.print_success("Registration successful. You can now log in.")
        elif json_data["type"] == "register_failed":
            self.clear_screen()
            self.print_error("Registration failed. Username may already exist.")

    def login(self):
        """
        Login to the server.
        """
        while not self.logged_in:
            choice = input("1. Login\n2. Register\nEnter your choice (1/2): ")
            self.clear_screen()

            if choice not in ["1", "2"]:
                self.print_error("Invalid choice. Please try again.")
                continue

            if choice == "2":
                self.register()
                continue

            self.username = input("Enter your username: ")
            password = input("Enter your password: ")
            login_message = json.dumps(
                {"type": "login", "username": self.username, "password": password}
            )
            self.send_message(login_message)

            message = self.client_socket.recv(MAX_MESSAGE_LENGTH_BYTES).decode()
            if not message:
                break

            json_data = json.loads(message)
            if json_data["type"] == "login_success":
                self.logged_in = True
                print("\nLogin successful. You can now chat.")
            elif json_data["type"] == "login_failed":
                self.clear_screen()
                self.print_error(json_data["message"])

    def receive_messages(self):
        """
        Receive messages from the server.
        """
        while True:
            try:
                message = self.client_socket.recv(MAX_MESSAGE_LENGTH_BYTES).decode()
                if not message:
                    # don't process empty messages
                    break

                json_data = json.loads(message)
                if json_data["type"] == "message":
                    self.messages.append(
                        f"{json_data['username']}: {json_data['message']}"
                    )
                    self.refresh_display()
            except socket.error:
                print("Connection to server lost")
                break

    def run(self):
        """
        Run the client, logging in and entering the chat loop.
        """
        self.clear_screen()
        self.login()
        self.clear_screen()

        # we want to receive messages in a separate thread so we can display them as they arrive
        # we use a daemon thread so it will automatically exit when the main thread exits
        receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
        receive_thread.start()

        while True:
            self.refresh_display()
            message = input()
            if message.lower() == "exit()":
                break
            if len(message) > MAX_MESSAGE_LENGTH_BYTES:
                # don't allow messages that exceed the max length
                self.error = f"Message exceeds maximum length of {MAX_MESSAGE_LENGTH_BYTES} bytes. Please try again."
                continue
            message_data = json.dumps(
                {"type": "message", "username": self.username, "message": message}
            )
            self.send_message(message_data)
            self.messages.append(f"{INPUT_PROMPT} {message}")

        self.client_socket.close()


if __name__ == "__main__":
    client = Client("localhost", PORT)
    client.run()
