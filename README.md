# sockchat

A command line chat app using sockets.

## Installation

1. Install requirements

```sh
pip install -r requirements.txt
```

1. Generate an SSL certificate and key

```sh
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

## Usage

1. Start the server

```sh
python server.py
```

2. Connect a client

```sh
python client.py
```

3. Chat.

## Disclaimer

This is a small project and is filled with jank. This should not be used for any mildly sensitive application.
