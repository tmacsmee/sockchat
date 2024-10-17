import json
import bcrypt
import os


class AuthManager:
    """
    A class that manages user authentication and registration.
    """

    def __init__(self, users_file):
        """
        Initialize the authentication manager with the given users file.
        """
        self.users_file = users_file
        self.users = self.load_users()

    def load_users(self):
        """
        Load the users from the users file.
        """
        if os.path.exists(self.users_file):
            with open(self.users_file, "r") as f:
                return json.load(f)
        return {}

    def save_users(self):
        """
        Save the users to the users file.
        """
        with open(self.users_file, "w") as f:
            json.dump(self.users, f)

    def hash_password(self, password):
        """
        Hash the given password using bcrypt.
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def check_password(self, stored_password, provided_password):
        """
        Check if the provided password matches the stored password.
        """
        return bcrypt.checkpw(
            provided_password.encode("utf-8"), stored_password.encode("utf-8")
        )

    def register_user(self, username, password):
        """
        Register a new user with the given username and password.
        """
        if username not in self.users:
            hashed_password = self.hash_password(password)
            self.users[username] = hashed_password
            self.save_users()
            return True
        return False

    def authenticate_user(self, username, password):
        """
        Authenticate a user with the given username and password.
        """
        if username in self.users and self.check_password(
            self.users[username], password
        ):
            return True
        return False
