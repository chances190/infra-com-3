import rdt
import json
import random
import string
from datetime import datetime

SERVER_ADDR = ("localhost", 5001)

class Server:
    def __init__(self):
        self.socket = rdt.RDTSocket(port=SERVER_ADDR[1])

        self.users = {}  # username -> {online: bool}
        self.friends = {}  # username -> [friend_usernames]
        self.groups = {}  # group_name -> {owner: username, members: [usernames], key: access_key}
        self.messages = {
            "direct": {},  # user1_user2 -> [{sender, content, timestamp}]
            "group": {}    # group_name -> [{sender, content, timestamp}]
        }
        self.banned_users = []
        self.log_message("Server started on {}:{}".format(*SERVER_ADDR))
    
    def log_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\033[36m[{timestamp}] SERVER: {message}\033[0m")
    
    def start(self):
        try:
            while True:
                self.handle_client()
        except KeyboardInterrupt:
            self.log_message("Server shutting down...")
        finally:
            self.socket.close()
    
    def handle_client(self):
        connected_user = None

        try:
            while True:
                data = self.socket.recv()
                if data is None:
                    break

                try:
                    request = json.loads(data.decode())
                    command = request.get("command", "")
                    username = request.get("user", "")

                    if username in self.banned_users and command != "logout":
                        self.log_message(f"Rejected request from banned user: {username}")
                        continue

                    response = self.handle_command(request)

                    if command == "login":
                        self.users[username] = {"online": True}
                    elif command == "logout" and connected_user:
                        if username in self.users:
                            self.users[username]["online"] = False
                        connected_user = None

                    # Send response for commands that expect one
                    if response is not None:
                        self.socket.send(json.dumps(response).encode())

                except json.JSONDecodeError:
                    self.log_message(f"Received invalid JSON data: {data.decode("utf-8")}")
                except Exception as e:
                    self.log_message(f"Error handling client command: {str(e)}. Packet content: {data.decode("utf-8")}")

        except Exception as e:
            self.log_message(f"Client connection error: {str(e)}")
    
    def handle_command(self, request):
        command = request["command"]
        username = request["user"]
        
        self.log_message(f"Received command: {command} from {username}")
        
        # Command handlers
        if command == "login":
            return self.handle_login(username)
        elif command == "logout":
            return self.handle_logout(username)
        elif command == "list:cinners":
            return self.handle_list_cinners()
        elif command == "list:friends":
            return self.handle_list_friends(username)
        elif command == "list:mygroups":
            return self.handle_list_mygroups(username)
        elif command == "list:groups":
            return self.handle_list_groups()
        elif command == "follow":
            return self.handle_follow(username, request["friend"])
        elif command == "unfollow":
            return self.handle_unfollow(username, request["friend"])
        elif command == "create_group":
            return self.handle_create_group(username, request["group"])
        elif command == "delete_group":
            return self.handle_delete_group(username, request["group"])
        elif command == "join":
            return self.handle_join_group(username, request["group"], request["key"])
        elif command == "leave":
            return self.handle_leave_group(username, request["group"])
        elif command == "ban":
            return self.handle_ban_user(username, request["target"])
        elif command == "chat_group":
            return self.handle_chat_group(username, request["group"], request["key"], request["message"])
        elif command == "chat_friend":
            return self.handle_chat_friend(username, request["friend"], request["message"])
        elif command == "list:messages":
            return self.handle_list_messages(username, request["chat"])
        else:
            self.log_message(f"Unknown command: {command}")
            return None
    
    # Command Handler Methods
    def handle_login(self, username):
        if username not in self.users:
            self.users[username] = {"online": True, "socket": None}
            self.friends[username] = []
            self.log_message(f"User registered: {username}")
        else:
            self.users[username]["online"] = True
            self.log_message(f"User logged in: {username}")
        return None
    
    def handle_logout(self, username):
        if username in self.users:
            self.users[username]["online"] = False
            self.log_message(f"User logged out: {username}")
        return None
    
    def handle_list_cinners(self):
        return [user for user in self.users.keys()]
    
    def handle_list_friends(self, username):
        if username not in self.friends:
            return []
        return [friend for friend in self.friends[username]]
    
    def handle_list_mygroups(self, username):
        user_groups = []
        for group_name, group_info in self.groups.items():
            if username in group_info["members"] or username == group_info["owner"]:
                user_groups.append({
                    "name": group_name,
                    "owner": group_info["owner"],
                    "key": group_info["key"] if username == group_info["owner"] else "",
                    "members": len(group_info["members"])
                })
        return user_groups
    
    def handle_list_groups(self):
        return [{"name": group_name, 
                 "owner": group_info["owner"], 
                 "members": len(group_info["members"])} 
                for group_name, group_info in self.groups.items()]
    
    def handle_follow(self, username, friend_name):
        if username == friend_name:
            return False
        
        if friend_name not in self.users:
            return False
        
        if username not in self.friends:
            self.friends[username] = []
        
        if friend_name not in self.friends[username]:
            self.friends[username].append(friend_name)
            self.log_message(f"{username} is now following {friend_name}")
        
        # Create a conversation key for direct messages
        chat_key = self._get_direct_chat_key(username, friend_name)
        if chat_key not in self.messages["direct"]:
            self.messages["direct"][chat_key] = []
        
        return True
    
    def handle_unfollow(self, username, friend_name):
        if username in self.friends and friend_name in self.friends[username]:
            self.friends[username].remove(friend_name)
            self.log_message(f"{username} unfollowed {friend_name}")
            return True
        return False
    
    def handle_create_group(self, username, group_name):
        if not group_name or group_name in self.groups:
            return False
        
        # Generate a random key for the group
        key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        self.groups[group_name] = {
            "owner": username,
            "members": [username],
            "key": key
        }
        
        # Create message storage for the group
        self.messages["group"][group_name] = []
        
        self.log_message(f"Group created: {group_name} by {username} with key {key}")
        return True
    
    def handle_delete_group(self, username, group_name):
        if group_name in self.groups and self.groups[group_name]["owner"] == username:
            del self.groups[group_name]
            if group_name in self.messages["group"]:
                del self.messages["group"][group_name]
            self.log_message(f"Group deleted: {group_name} by {username}")
            return True
        return False
    
    def handle_join_group(self, username, group_name, key):
        if group_name not in self.groups:
            return False
        
        group = self.groups[group_name]
        
        # Owner can join without key, others need correct key
        if username == group["owner"] or key == group["key"]:
            if username not in group["members"]:
                group["members"].append(username)
                self.log_message(f"{username} joined group: {group_name}")
            return True
        return False
    
    def handle_leave_group(self, username, group_name):
        if group_name in self.groups:
            group = self.groups[group_name]
            
            # Owner can't leave their own group
            if username == group["owner"]:
                return False
            
            if username in group["members"]:
                group["members"].remove(username)
                self.log_message(f"{username} left group: {group_name}")
                return True
        return False
    
    def handle_ban_user(self, username, target_user):
        # Only allow ban if user is admin (for this example, let's consider all users as non-admins)
        # In a real app, you'd check admin privileges
        if username == "admin" and target_user not in self.banned_users:
            self.banned_users.append(target_user)
            self.log_message(f"User banned: {target_user} by {username}")
            return True
        return False
    
    def handle_chat_group(self, username, group_name, key, message):
        if group_name not in self.groups:
            return False
        
        group = self.groups[group_name]
        
        # Check if user is in group or is the owner
        if username not in group["members"] and username != group["owner"]:
            return False
        
        # Store the message
        new_message = {
            "sender": username,
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        
        self.messages["group"][group_name].append(new_message)
        self.log_message(f"Group message to {group_name} from {username}: {message}")
        
        return True
    
    def handle_chat_friend(self, username, friend_name, message):
        if friend_name not in self.users or username not in self.friends.get(friend_name, []):
            return False
        
        # Store the message
        chat_key = self._get_direct_chat_key(username, friend_name)
        if chat_key not in self.messages["direct"]:
            self.messages["direct"][chat_key] = []
        
        new_message = {
            "sender": username,
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        
        self.messages["direct"][chat_key].append(new_message)
        self.log_message(f"Direct message to {friend_name} from {username}: {message}")
        
        return True

    def handle_list_messages(self, username, chat_name):
        # Check if it's a direct chat
        if "_" in chat_name:
            parts = chat_name.split("_")
            if len(parts) == 2 and (username == parts[0] or username == parts[1]):
                chat_key = self._get_direct_chat_key(parts[0], parts[1])
                return self.messages["direct"].get(chat_key, [])
        
        # Check if it's a group chat
        elif chat_name in self.groups:
            group = self.groups[chat_name]
            if username in group["members"] or username == group["owner"]:
                return self.messages["group"].get(chat_name, [])
        
        return []
    
    def _get_direct_chat_key(self, user1, user2):
        # Sort usernames alphabetically to ensure consistency
        return "_".join(sorted([user1, user2]))

# Start the server when run as a script
if __name__ == "__main__":
    server = Server()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServer shutting down...")
