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


class Client:
    def __init__(self, host, port):
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

    def clear_screen(self):
        print(CLEAR_SCREEN, end="")
        self.move_cursor(1, 1)

    def move_cursor(self, row, col):
        print(MOVE_CURSOR.format(row, col), end="")

    def clear_line(self):
        print(CLEAR_LINE, end="")

    def print_error(self, message):
        print(Fore.RED + message + Style.RESET_ALL)

    def print_success(self, message):
        print(Fore.GREEN + message + Style.RESET_ALL)

    def refresh_display(self):
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
        try:
            self.client_socket.send(message.encode())
        except socket.error as e:
            print(f"Error sending message: {e}")

    def register(self):
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
        while True:
            try:
                message = self.client_socket.recv(MAX_MESSAGE_LENGTH_BYTES).decode()
                if not message:
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
        self.clear_screen()
        self.login()
        self.clear_screen()

        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.start()

        while True:
            self.refresh_display()
            message = input()
            if message.lower() == "exit()":
                break
            if len(message) > MAX_MESSAGE_LENGTH_BYTES:
                self.error = f"Message exceeds maximum length of {MAX_MESSAGE_LENGTH_BYTES} bytes. Please try again."
                continue
            message_data = json.dumps(
                {"type": "message", "username": self.username, "message": message}
            )
            self.send_message(message_data)
            self.messages.append(f"{INPUT_PROMPT} {message}")

        self.client_socket.close()


if __name__ == "__main__":
    client = Client("localhost", 1234)
    client.run()
