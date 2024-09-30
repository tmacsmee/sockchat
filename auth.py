import json
import bcrypt
import os


class AuthManager:
    def __init__(self, users_file):
        self.users_file = users_file
        self.users = self.load_users()

    def load_users(self):
        if os.path.exists(self.users_file):
            with open(self.users_file, "r") as f:
                return json.load(f)
        return {}

    def save_users(self):
        with open(self.users_file, "w") as f:
            json.dump(self.users, f)

    def hash_password(self, password):
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def check_password(self, stored_password, provided_password):
        return bcrypt.checkpw(
            provided_password.encode("utf-8"), stored_password.encode("utf-8")
        )

    def register_user(self, username, password):
        if username not in self.users:
            hashed_password = self.hash_password(password)
            self.users[username] = hashed_password
            self.save_users()
            return True
        return False

    def authenticate_user(self, username, password):
        if username in self.users and self.check_password(
            self.users[username], password
        ):
            return True
        return False
