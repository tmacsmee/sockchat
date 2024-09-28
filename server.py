import ssl
import socket
import select

class Server:
  def __init__(self, host, port):
    self.host = host
    self.port = port
    self.clients = []
    self.server_socket = None

  def start(self):
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.server_socket:
      self.server_socket.bind((self.host, self.port))
      self.server_socket.listen(2)
      print(f"Server is listening on {self.host}:{self.port}")

      with context.wrap_socket(self.server_socket, server_side=True) as secure_socket:
        for _ in range(2):
          conn, addr = secure_socket.accept()
          print(f"Connection from {addr}")
          self.clients.append(conn)

        while True:
          readable, _, _ = select.select(self.clients, [], [])
          for client_socket in readable:
            self.handle_client(client_socket)

  def handle_client(self, client_socket):
    try:
      data = client_socket.recv(1024)
      if not data:
        print("Client disconnected")
        self.stop()
        return
      self.broadcast(data, client_socket)

    except ssl.SSLError as e:
      print(f"SSL Error: {e}")
      self.stop()
      return
    
    except Exception as e:
      print(f"Error: {e}")
      self.stop()
      return
  

  def broadcast(self, data, sender): 
    for client_socket in self.clients:
      if client_socket != sender:
        try:
          client_socket.send(data)
        except Exception as e:
          print(f"Error: {e}")
          self.stop()
          return
  
  def stop(self):
    for client_socket in self.clients:
      client_socket.close()
    self.clients = []

    if self.server_socket:
      self.server_socket.close()

if __name__ == "__main__":
  server = Server("localhost", 1234)
  try:
    server.start()
  except KeyboardInterrupt:
    print("Stopping server...")
  finally:
    server.stop()
    