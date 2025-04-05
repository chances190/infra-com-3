import rdt
import json

SERVER_ADDR = ("localhost", 5001)

class Client:
    def __init__(self, login):
        self.login = login
        self.socket = rdt.RDTSocket()
        self.socket.connect(SERVER_ADDR)

    def login(self):
        data = json.dumps({"command": "login", "user": self.login})
        self.socket.send(data.encode())

    def logout(self):
        data = json.dumps({"command": "logout", "user": self.login})
        self.socket.send(data.encode())

    def list_cinners(self):
        data = json.dumps({"command": "list:cinners", "user": self.login})
        self.socket.send(data.encode())
        response = json.loads(self.socket.recv().decode())
        if not isinstance(response, list):
            print("Error: Response is not a list.")
            exit(1)
        return response

    def list_friends(self):
        data = json.dumps({"command": "list:friends", "user": self.login})
        self.socket.send(data.encode())
        response = json.loads(self.socket.recv().decode())
        if not isinstance(response, list):
            print("Error: Response is not a list.")
            exit(1)
        return response

    def list_mygroups(self):
        data = json.dumps({"command": "list:mygroups", "user": self.login})
        self.socket.send(data.encode())
        response = json.loads(self.socket.recv().decode())
        if not isinstance(response, list):
            print("Error: Response is not a list.")
            exit(1)
        return response

    def list_groups(self):
        data = json.dumps({"command": "list:groups", "user": self.login})
        self.socket.send(data.encode())
        response = json.loads(self.socket.recv().decode())
        if not isinstance(response, list):
            print("Error: Response is not a list.")
            exit(1)
        return response

    def follow(self, friend_name):
        data = json.dumps({"command": "follow", "user": self.login, "friend": friend_name})
        self.socket.send(data.encode())

    def unfollow(self, friend_name):
        data = json.dumps({"command": "unfollow", "user": self.login, "friend": friend_name})
        self.socket.send(data.encode())

    def create_group(self, group_name):
        data = json.dumps({"command": "create_group", "user": self.login, "group": group_name})
        self.socket.send(data.encode())

    def delete_group(self, group_name):
        data = json.dumps({"command": "delete_group", "user": self.login, "group": group_name})
        self.socket.send(data.encode())

    def join_group(self, group_name, group_key):
        data = json.dumps({"command": "join", "user": self.login, "group": group_name, "key": group_key})
        self.socket.send(data.encode())

    def leave_group(self, group_name):
        data = json.dumps({"command": "leave", "user": self.login, "group": group_name})
        self.socket.send(data.encode())

    def ban_user(self, user_name):
        data = json.dumps({"command": "ban", "user": self.login, "target": user_name})
        self.socket.send(data.encode())

    def chat_group(self, group_name, group_key, message):
        data = json.dumps({"command": "chat_group", "user": self.login, "group": group_name, "key": group_key, "message": message})
        self.socket.send(data.encode())

    def chat_friend(self, friend_name, message):
        data = json.dumps({"command": "chat_friend", "user": self.login, "friend": friend_name, "message": message})
        self.socket.send(data.encode())

    def list_messages(self, chat_name):
        data = json.dumps({"command": "list:messages", "user": self.login, "chat": chat_name})
        self.socket.send(data.encode())
        response = json.loads(self.socket.recv().decode())
        if not isinstance(response, list):
            print("Error: Response is not a list.")
            exit(1)
        return response