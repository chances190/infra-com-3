from .logic import Client
from datetime import datetime

PURPLE = "\033[35m"
RESET = "\033[0m"

# mostra uma lista de comandos disponíveis para o usuário. É tipo um guia rápido pra não se perder.
def print_help():
    help_text = f"""
{PURPLE}Available commands:{RESET}
  logout                           - Log out from the server
  list cinners                     - List all users
  list friends                     - List your friends
  list mygroups                    - List groups you're in
  list groups                      - List all available groups
  list messages <chatname>         - List messages from a chat
  follow <username>                - Follow a user
  unfollow <username>              - Unfollow a user
  create_group <groupname>         - Create a new group
  delete_group <groupname>         - Delete a group you own
  join <groupname> <key>           - Join a group with a key
  leave <groupname>                - Leave a group
  ban <username>                   - Ban a user from your groups
  chat_group <groupname> <key> <message>  - Send message to group
  chat_friend <friendname> <message>      - Send message to friend
  exit                             - Exit the client
  help                             - Show this help message
"""
    print(help_text)

# formata uma string de timestamp para um formato mais amigável. Se der erro, devolve o original mesmo.
def format_timestamp(timestamp_str):
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%b %d, %H:%M")
    except Exception:
        return timestamp_str

# exibe mensagens de um chat. Se não tiver mensagens, avisa que está vazio.
def print_messages(messages):
    if not messages:
        print(f"{PURPLE}No messages found{RESET}")
        return
    
    for msg in messages:
        timestamp = format_timestamp(msg.get('timestamp', ''))
        sender = msg.get('sender', 'unknown')
        content = msg.get('content', '')
        
        print(f"{PURPLE}[{timestamp}] {sender}:{RESET} {content}")

# exibe uma lista de itens com título e mensagem de vazio, se necessário. Serve pra listas de usuários, grupos, etc.
def print_list(items, title, empty_message="No items found"):
    if not items:
        print(f"{PURPLE}{empty_message}{RESET}")
        return
    
    print(f"{PURPLE}{title}:{RESET}")
    if isinstance(items[0], dict):
        for i, item in enumerate(items, 1):
            if 'name' in item:
                print(f"  {i}. {item['name']}")
                details = []
                if 'owner' in item:
                    details.append(f"owner: {item['owner']}")
                if 'members' in item:
                    details.append(f"members: {item['members']}")
                if 'key' in item and item['key']:
                    details.append(f"key: {item['key']}")
                print("    " + ", ".join(details))
    else:

        for i, item in enumerate(items, 1):
            print(f"  {i}. {item}")

# Mostra uma mensagem de sucesso com um check verde.
def print_success(message):
    print(f"{PURPLE}✓ {message}{RESET}")

# Mostra uma mensagem de erro com um X vermelho.
def print_error(message):
    print(f"{PURPLE}✗ {message}{RESET}")

# Mostra uma mensagem informativa com um ícone de informação.
def print_info(message):
    print(f"{PURPLE}i {message}{RESET}")

# Essa é a função principal do programa. Ela gerencia o fluxo de comandos e interações do usuário.
def main():
    username = input(f"{PURPLE}Enter your username: {RESET}").strip()
    client = Client(username)
    
    if not client.login():
        print_error("Login failed. Exiting.")
        return
    
    print_success(f"Logged in as {username}. Type 'help' for commands.")
    
    try:
        while True:
            try:
                input_line = input(f"{PURPLE}> {RESET}").strip()
                if not input_line:
                    continue
                
                tokens = input_line.split()
                command = tokens[0]
                
                if command == "logout":
                    success = client.logout()
                    if success:
                        print_success("Logged out successfully.")
                        break
                    else:
                        print_error("Logout failed.")
                
                elif command == "list":
                    if len(tokens) < 2:
                        print_error("Invalid list command. Usage: list [cinners|friends|mygroups|groups|messages <chatname>]")
                        continue
                    
                    subcmd = tokens[1].lower()
                    if subcmd == "cinners":
                        users = client.list_cinners()
                        if users is not None:
                            print_list(users, "All users")
                        else:
                            print_error("Failed to retrieve user list.")
                    
                    elif subcmd == "friends":
                        friends = client.list_friends()
                        if friends is not None:
                            print_list(friends, "Your friends")
                        else:
                            print_error("Failed to retrieve friends list.")
                    
                    elif subcmd == "mygroups":
                        groups = client.list_mygroups()
                        if groups is not None:
                            print_list(groups, "Your groups")
                        else:
                            print_error("Failed to retrieve your groups.")
                    
                    elif subcmd == "groups":
                        groups = client.list_groups()
                        if groups is not None:
                            print_list(groups, "Available groups")
                        else:
                            print_error("Failed to retrieve group list.")
                    
                    elif subcmd == "messages":
                        if len(tokens) < 3:
                            print_error("Usage: list messages <chatname>")
                            continue
                        chat_name = tokens[2]
                        messages = client.list_messages(chat_name)
                        if messages is not None:
                            print_messages(messages)
                        else:
                            print_error(f"Failed to retrieve messages for {chat_name}.")
                    
                    else:
                        print_error("Unknown list subcommand. Use 'help' for available commands.")
                
                elif command == "follow":
                    if len(tokens) < 2:
                        print_error("Usage: follow <username>")
                        continue
                    friend = tokens[1]
                    success = client.follow(friend)
                    if success:
                        print_success(f"Started following {friend}.")
                    else:
                        print_error(f"Failed to follow {friend}.")
                
                elif command == "unfollow":
                    if len(tokens) < 2:
                        print_error("Usage: unfollow <username>")
                        continue
                    friend = tokens[1]
                    success = client.unfollow(friend)
                    if success:
                        print_success(f"Stopped following {friend}.")
                    else:
                        print_error(f"Failed to unfollow {friend}.")
                
                elif command == "create_group":
                    if len(tokens) < 2:
                        print_error("Usage: create_group <groupname>")
                        continue
                    group = tokens[1]
                    success = client.create_group(group)
                    if success:
                        print_success(f"Group {group} created.")
                    else:
                        print_error(f"Failed to create group {group}.")
                
                elif command == "delete_group":
                    if len(tokens) < 2:
                        print_error("Usage: delete_group <groupname>")
                        continue
                    group = tokens[1]
                    success = client.delete_group(group)
                    if success:
                        print_success(f"Group {group} deleted.")
                    else:
                        print_error(f"Failed to delete group {group}.")
                
                elif command == "join":
                    if len(tokens) < 3:
                        print_error("Usage: join <groupname> <key>")
                        continue
                    group = tokens[1]
                    key = tokens[2]
                    success = client.join_group(group, key)
                    if success:
                        print_success(f"Joined group {group}.")
                    else:
                        print_error(f"Failed to join group {group}.")
                
                elif command == "leave":
                    if len(tokens) < 2:
                        print_error("Usage: leave <groupname>")
                        continue
                    group = tokens[1]
                    success = client.leave_group(group)
                    if success:
                        print_success(f"Left group {group}.")
                    else:
                        print_error(f"Failed to leave group {group}.")
                
                elif command == "ban":
                    if len(tokens) < 2:
                        print_error("Usage: ban <username>")
                        continue
                    user = tokens[1]
                    success = client.ban_user(user)
                    if success:
                        print_success(f"Banned {user}.")
                    else:
                        print_error(f"Failed to ban {user}.")
                
                elif command == "chat_group":
                    if len(tokens) < 4:
                        print_error("Usage: chat_group <groupname> <key> <message>")
                        continue
                    group = tokens[1]
                    key = tokens[2]
                    message = " ".join(tokens[3:])
                    success = client.chat_group(group, key, message)
                    if success:
                        print_success(f"Message sent to group {group}.")
                    else:
                        print_error(f"Failed to send message to group {group}.")
                
                elif command == "chat_friend":
                    if len(tokens) < 3:
                        print_error("Usage: chat_friend <friendname> <message>")
                        continue
                    friend = tokens[1]
                    message = " ".join(tokens[2:])
                    success = client.chat_friend(friend, message)
                    if success:
                        print_success(f"Message sent to {friend}.")
                    else:
                        print_error(f"Failed to send message to {friend}.")
                
                elif command == "exit":
                    client.logout()
                    print_info("Goodbye!")
                    break
                
                elif command == "help":
                    print_help()
                
                else:
                    print_error("Unknown command. Type 'help' for available commands.")
            
            except Exception as e:
                print_error(f"Error processing command: {e}")
    
    except KeyboardInterrupt:
        print(f"\n{PURPLE}Use 'exit' to logout and quit.{RESET}")
    finally:
        client.socket.close()

if __name__ == "__main__":
    main()