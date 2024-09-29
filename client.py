import socket
import ssl
import json
import select

class Client:
  def __init__(self, host, port):
    self.host = host
    self.port = port
    self.client_socket = None

  def connect(self):
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.load_verify_locations("cert.pem")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
      client_socket.connect((self.host, self.port))
      print(f"Connected to {self.host}:{self.port}")

      with context.wrap_socket(client_socket, server_hostname=self.host) as self.client_socket:
        self.login()

    
  
  def login(self):
    choice = input("Do you want to login or register? (l/r): ")
    username = input("Username: ")
    password = input("Password: ")

    if choice not in ["l", "r"]:
      print("Invalid choice. Please try again.")
      return
  
    message = {
      "message_type": "login" if choice == "l" else "register",
      "username": username,
      "password": password
    }

    self.client_socket.send(json.dumps(message).encode())
    
    while True:
      readable, _, _ = select.select([self.client_socket], [], [])
      for _ in readable:
        self.handle_message()

  def handle_message(self):
    try:
      data = self.client_socket.recv(1024)
      if not data:
        print("Server disconnected")
        self.stop()
        return
      json_data = json.loads(data.decode())
      print(json_data)
    except ssl.SSLError as e:
      print(f"SSL Error: {e}")
      self.stop()
      return
    except json.JSONDecodeError as e:
      print(f"Error decoding JSON: {e}")
      self.stop()
      return
    except Exception as e:
      print(f"Error: {e}")
      self.stop()
      return
    
  def stop(self):
    self.client_socket.close()


if __name__ == "__main__":
  client = Client("localhost", 1234)
  try:
    client.connect()
    client.login("username", "password")
  except KeyboardInterrupt:
    print("Shutting down client...")
  finally:
    client.stop()
  

