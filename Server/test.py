import json
from rdt.rdt3 import RDTSocket

# Define the server address and port
HOST = '127.0.0.1'  # localhost
PORT = 5001

# List of raw JSON commands to send
commands = [
    {"command": "login", "user": "test_user"},
    {"command": "list:cinners", "user": "test_user"},
    {"command": "list:friends", "user": "test_user"},
    {"command": "list:mygroups", "user": "test_user"},
    {"command": "list:groups", "user": "test_user"},
    {"command": "follow", "user": "test_user", "friend": "friend_name"},
    {"command": "unfollow", "user": "test_user", "friend": "friend_name"},
    {"command": "create_group", "user": "test_user", "group": "group_name"},
    {"command": "delete_group", "user": "test_user", "group": "group_name"},
    {"command": "join", "user": "test_user", "group": "group_name", "key": "group_key"},
    {"command": "leave", "user": "test_user", "group": "group_name"},
    {"command": "ban", "user": "test_user", "target": "user_name"},
    {"command": "chat_group", "user": "test_user", "group": "group_name", "key": "group_key", "message": "Hello Group"},
    {"command": "chat_friend", "user": "test_user", "friend": "friend_name", "message": "Hello Friend"},
    {"command": "list:messages", "user": "test_user", "chat": "chat_name"},
    {"command": "logout", "user": "test_user"}
]

# Create an RDT socket
rdt_socket = RDTSocket()
try:
    # Connect to the server
    rdt_socket.connect((HOST, PORT))

    for command in commands:
        # Convert the command to JSON string
        json_data = json.dumps(command)

        # Send the JSON data
        rdt_socket.send(json_data.encode())

        # Receive the response from the server
        response = rdt_socket.recv()

        if response is None:
            print(f"Command {command['command']} returned None, moving to next.")
            continue

        # Decode and print the response
        response_data = json.loads(response.decode('utf-8'))
        print(f"Response for {command['command']}: {json.dumps(response_data, indent=4)}")

except Exception as e:
    print("An error occurred:", e)
finally:
    rdt_socket.close()