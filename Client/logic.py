import rdt
import json

SERVER_ADDR = ("localhost", 5001)

class Client:
    def __init__(self, username):
        self.username = username
        self.socket = rdt.RDTSocket()
        self.socket.connect(SERVER_ADDR)
        if self.socket.send("Handshake") is False:
            self.log_message("Failed to connect to server. Shutting down")
            exit(1)
        self.log_message("Client started")
            
    def log_message(self, message, color=None):
        formatted_message = f"Client {self.username}: {message}"
        print(f"\033[33m{formatted_message}\033[0m")

    def login(self):
        data = json.dumps({"command": "login", "user": self.username})
        self.log_message(f"Logging in as {self.username}")
        if self.socket.send(data.encode()) is False:
            self.log_message("Failed to login: Connection error")
            return False
        return True

    def logout(self):
        data = json.dumps({"command": "logout", "user": self.username})
        self.log_message(f"Logging out: {self.username}")
        if self.socket.send(data.encode()) is False:
            self.log_message("Error during logout: Connection error")
            return False
        return True

    def list_cinners(self):
        data = json.dumps({"command": "list:cinners", "user": self.username})
        self.log_message("Requesting list of all users")
        if self.socket.send(data.encode()) is False:
            self.log_message("Error: Failed to send data to server.")
            return None
        response = self.socket.recv()
        if response is None:
            self.log_message("Error: Received None from server.")
            return None
        response = json.loads(response.decode())
        if not isinstance(response, list):
            self.log_message("Error: Response is not a list.")
            return None
        return response

    def list_friends(self):
        data = json.dumps({"command": "list:friends", "user": self.username})
        self.log_message("Requesting friend list")
        if self.socket.send(data.encode()) is False:
            self.log_message("Error: Failed to send data to server.")
            return None
        response = self.socket.recv()
        if response is None:
            self.log_message("Error: Received None from server.")
            return None
        response = json.loads(response.decode())
        if not isinstance(response, list):
            self.log_message("Error: Response is not a list.")
            return None
        return response

    def list_mygroups(self):
        data = json.dumps({"command": "list:mygroups", "user": self.username})
        self.log_message("Requesting my groups")
        if self.socket.send(data.encode()) is False:
            self.log_message("Error: Failed to send data to server.")
            return None
        response = self.socket.recv()
        if response is None:
            self.log_message("Error: Received None from server.")
            return None
        response = json.loads(response.decode())
        if not isinstance(response, list):
            self.log_message("Error: Response is not a list.")
            return None
        return response

    def list_groups(self):
        data = json.dumps({"command": "list:groups", "user": self.username})
        self.log_message("Requesting available groups")
        if self.socket.send(data.encode()) is False:
            self.log_message("Error: Failed to send data to server.")
            return None
        response = self.socket.recv()
        if response is None:
            self.log_message("Error: Received None from server.")
            return None
        response = json.loads(response.decode())
        if not isinstance(response, list):
            self.log_message("Error: Response is not a list.")
            return None
        return response

    def follow(self, friend_name):
        data = json.dumps({"command": "follow", "user": self.username, "friend": friend_name})
        self.log_message(f"Following user: {friend_name}")
        if self.socket.send(data.encode()) is False:
            self.log_message(f"Error: Failed to follow {friend_name}.")
            return False
        return True

    def unfollow(self, friend_name):
        data = json.dumps({"command": "unfollow", "user": self.username, "friend": friend_name})
        self.log_message(f"Unfollowing user: {friend_name}")
        if self.socket.send(data.encode()) is False:
            self.log_message(f"Error: Failed to unfollow {friend_name}.")
            return False
        return True

    def create_group(self, group_name):
        data = json.dumps({"command": "create_group", "user": self.username, "group": group_name})
        self.log_message(f"Creating group: {group_name}")
        if self.socket.send(data.encode()) is False:
            self.log_message(f"Error: Failed to create group {group_name}.")
            return False
        return True

    def delete_group(self, group_name):
        data = json.dumps({"command": "delete_group", "user": self.username, "group": group_name})
        self.log_message(f"Deleting group: {group_name}")
        if self.socket.send(data.encode()) is False:
            self.log_message(f"Error: Failed to delete group {group_name}.")
            return False
        return True

    def join_group(self, group_name, group_key):
        data = json.dumps({"command": "join", "user": self.username, "group": group_name, "key": group_key})
        self.log_message(f"Joining group: {group_name}")
        if self.socket.send(data.encode()) is False:
            self.log_message(f"Error: Failed to join group {group_name}.")
            return False
        return True

    def leave_group(self, group_name):
        data = json.dumps({"command": "leave", "user": self.username, "group": group_name})
        self.log_message(f"Leaving group: {group_name}")
        if self.socket.send(data.encode()) is False:
            self.log_message(f"Error: Failed to leave group {group_name}.")
            return False
        return True

    def ban_user(self, user_name):
        data = json.dumps({"command": "ban", "user": self.username, "target": user_name})
        self.log_message(f"Banning user: {user_name}")
        if self.socket.send(data.encode()) is False:
            self.log_message(f"Error: Failed to ban user {user_name}.")
            return False
        return True

    def chat_group(self, group_name, group_key, message):
        data = json.dumps({"command": "chat_group", "user": self.username, "group": group_name, "key": group_key, "message": message})
        self.log_message(f"TO GROUP '{group_name}': {message}")
        if self.socket.send(data.encode()) is False:
            self.log_message(f"Error: Failed to send message to group {group_name}.")
            return False
        return True

    def chat_friend(self, friend_name, message):
        data = json.dumps({"command": "chat_friend", "user": self.username, "friend": friend_name, "message": message})
        self.log_message(f"TO USER '{friend_name}': {message}")
        if self.socket.send(data.encode()) is False:
            self.log_message(f"Error: Failed to send message to {friend_name}.")
            return False
        return True

    def list_messages(self, chat_name):
        data = json.dumps({"command": "list:messages", "user": self.username, "chat": chat_name})
        self.log_message(f"Getting messages for: {chat_name}")
        if self.socket.send(data.encode()) is False:
            self.log_message(f"Error: Failed to request messages for {chat_name}.")
            return None
        response = self.socket.recv()
        if response is None:
            self.log_message("Error: Received None from server.")
            return None
        response = json.loads(response.decode())
        if not isinstance(response, list):
            self.log_message("Error: Response is not a list.")
            return None
        return response
