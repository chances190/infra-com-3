#!/usr/bin/env python3

"""
Disclaimer: Este arquivo contém a lógica de interface de usuário TUI dos clientes, desenvolvida com a 
biblioteca `curses`. A implementação deste código contou com o forte auxílio do GitHub Copilot. No 
entanto, toda a lógica de funcionamento do sistema, incluindo o protocolo RDT 3.0 e as demais 
funcionalidades do cliente e do servidor, foi desenvolvida exclusivamente pela equipe do projeto, sem 
interferência do Copilot.

Atenciosamente,  
Github Copilot
"""

import curses
from enum import Enum, auto
import time
from .logic import Client  # Import the Client class

# Define application states as an enum
class AppMode(Enum):
    LOGIN = auto()
    NAVIGATION = auto()
    CONTENT = auto()

# Centralized state management
class AppState:
    def __init__(self):
        self.mode = AppMode.LOGIN
        self.messages = ["Welcome to the chat room!"]
        self.selected_content = "Welcome"  # Start with welcome screen
        self.current_topic = ""  # Track the current selected topic/item
        self.client = None
        self.chat_histories = {}  # Store chat histories by chat name
        self.current_chat_type = None  # "friend" or "group"
        self.refresh_needed = False

# Base UI component class
class UIComponent:
    def __init__(self, app_state, title):
        self.state = app_state
        self.title = title
        self.window = None
    
    def draw(self, stdscr):
        pass
    
    def handle_input(self, key):
        if key in (curses.KEY_LEFT, 27):
            self.state.mode = AppMode.NAVIGATION
        return False 
    
    def resize(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.window = curses.newwin(self.height, self.width, self.y, self.x)
        self.window.keypad(True)

# Menu component
class MenuComponent(UIComponent):
    def __init__(self, app_state, title, menu_structure, content_mapping):
        super().__init__(app_state, title)
        self.menu_structure = menu_structure
        self.content_mapping = content_mapping  # Map menu items to content components
        self.selected_menu_idx = 0  # Local state for menu index
        self.previous_menu_idx = {title: 0}  # Track previous indices for each menu locally
        self.prev_selected_item = None  # Track previously selected item
        self.last_refresh = 0  # Track when we last refreshed menu data
    
    def draw(self, colors):
        # Try to refresh menus before drawing
        self.refresh_menus()
        
        self.window.clear()
        self.window.border()
        self.window.addstr(0, 2, f" {self.title} ", colors.CYAN_BLACK)  # Use title property
        
        current_menu_items = self.menu_structure[self.title]
        for idx, item in enumerate(current_menu_items):
            y = idx + 2
            if idx == self.selected_menu_idx:
                self.window.addstr(y, 2, "> ", colors.CYAN_BLACK)
                self.window.addstr(y, 4, item, colors.WHITE_BLACK)
                
                # Update content preview on hover
                selected_item = current_menu_items[self.selected_menu_idx]
                if selected_item != self.prev_selected_item:
                    self.prev_selected_item = selected_item
                    self.update_content_preview(selected_item)
            else:
                self.window.addstr(y, 2, f"  {item}")
        
        self.window.refresh()
    
    def update_content_preview(self, selected_item):
        """Update the content preview based on the currently hovered item"""
        if selected_item == "Sair":
            return  # Don't change anything for exit option
        
        if selected_item in self.menu_structure:
            # It's a submenu - no content change needed
            pass
        else:
            # For content items, update the preview
            content_key = self.content_mapping.get(selected_item, "")
            if content_key:
                self.state.selected_content = content_key
                self.state.current_topic = selected_item
                
                # Set chat type based on where the item is located in the menu hierarchy
                if self.title == "Amigos":
                    self.state.current_chat_type = "friend"
                elif self.title == "Grupos":
                    self.state.current_chat_type = "group"
                
                # Mark that we need to refresh messages
                self.state.refresh_needed = True
    
    def handle_input(self, key):
        current_menu_items = self.menu_structure[self.title]
        
        if key == curses.KEY_UP:
            if self.selected_menu_idx > 0:
                self.selected_menu_idx -= 1
        elif key == curses.KEY_DOWN:
            if self.selected_menu_idx < len(current_menu_items) - 1:
                self.selected_menu_idx += 1
        elif key in (ord('\n'), curses.KEY_RIGHT):
            selected_item = current_menu_items[self.selected_menu_idx]
            if selected_item == "Sair":
                return True
            elif selected_item in self.menu_structure:
                self.previous_menu_idx[self.title] = self.selected_menu_idx
                self.title = selected_item  # Update title to the selected submenu
                self.selected_menu_idx = self.previous_menu_idx.get(selected_item, 0)
                # Update preview when entering submenu
                if self.selected_menu_idx < len(self.menu_structure[selected_item]):
                    self.update_content_preview(self.menu_structure[selected_item][self.selected_menu_idx])
            else:
                # If selecting a content item, switch to content mode
                content_key = self.content_mapping.get(selected_item, "")
                if content_key:
                    self.state.mode = AppMode.CONTENT
                    self.state.selected_content = content_key
                    self.state.current_topic = selected_item
        elif key in (27, curses.KEY_LEFT):
            if self.title != "Menu":
                parent_menu = "Menu"
                for menu, items in self.menu_structure.items():
                    if self.title in items:
                        parent_menu = menu
                        break
                self.previous_menu_idx[self.title] = self.selected_menu_idx
                self.title = parent_menu  # Update title to the parent menu
                self.selected_menu_idx = self.previous_menu_idx.get(parent_menu, 0)
                # Reset to Welcome when returning to main menu
                if parent_menu == "Menu":
                    self.state.selected_content = "Welcome"
                    self.state.current_topic = ""
                else:
                    # Update preview when going back to parent menu
                    self.update_content_preview(self.menu_structure[parent_menu][self.selected_menu_idx])
        
        # Special handling for adding friends or joining groups
        if self.title == "Descobrir.Usuários" and key == ord('a'):  # 'a' for add friend
            if self.selected_menu_idx < len(current_menu_items):
                selected_user = current_menu_items[self.selected_menu_idx]
                try:
                    self.state.client.follow(selected_user)
                    self.state.messages.append(f"Added {selected_user} as friend")
                    self.last_refresh = 0  # Force refresh
                except Exception as e:
                    self.state.messages.append(f"Error adding friend: {str(e)}")
        
        elif self.title == "Descobrir.Grupos" and key == ord('j'):  # 'j' for join group
            if self.selected_menu_idx < len(current_menu_items):
                selected_group = current_menu_items[self.selected_menu_idx]
                try:
                    # For simplicity, using group name as key
                    self.state.client.join_group(selected_group, selected_group)
                    self.state.messages.append(f"Joined group {selected_group}")
                    self.last_refresh = 0  # Force refresh
                except Exception as e:
                    self.state.messages.append(f"Error joining group: {str(e)}")
        
        return False
    
    def refresh_menus(self):
        """Update menu items from the server"""
        if not self.state.client or time.time() - self.last_refresh < 5:  # Only refresh every 5 seconds
            return
            
        try:
            # Update friends list
            friends = self.state.client.list_friends()
            self.menu_structure["Amigos"] = friends if friends else ["Nenhum amigo ainda"]
            
            # Update groups list
            mygroups = self.state.client.list_mygroups()
            self.menu_structure["Grupos"] = mygroups if mygroups else ["Nenhum grupo ainda"]
            
            # Update available users and groups
            all_users = self.state.client.list_cinners()
            self.menu_structure["Descobrir.Usuários"] = [u for u in all_users if u not in friends]
            
            all_groups = self.state.client.list_groups()
            self.menu_structure["Descobrir.Grupos"] = [g for g in all_groups if g not in mygroups]
            
            # Update content mappings
            for friend in friends:
                self.content_mapping[friend] = "Chat"
            
            for group in mygroups:
                self.content_mapping[group] = "Chat"
                
            self.last_refresh = time.time()
        except Exception:
            # Handle errors gracefully
            pass

# Content component
class ContentChatComponent(UIComponent):
    def __init__(self, app_state, title):
        super().__init__(app_state, title)
        self.is_typing = False  # Internal flag for typing mode
        self.cursor_pos = 0     # Cursor position in text input
        self.input_text = " "   # Always reset to a single space
    
    def draw(self, colors):
        self.window.clear()
        self.window.border()
        
        # Display title with current topic if available
        title = f" {self.title}"
        if hasattr(self.state, 'current_topic') and self.state.current_topic:
            title += f": {self.state.current_topic}"
        
        self.window.addstr(0, 2, title, colors.CYAN_BLACK)
        
        # Load messages if needed
        if self.state.refresh_needed and self.state.current_topic:
            try:
                messages = self.state.client.list_messages(self.state.current_topic)
                self.state.chat_histories[self.state.current_topic] = messages
                self.state.refresh_needed = False
            except Exception as e:
                self.state.messages.append(f"Error loading messages: {str(e)}")
        
        # Draw messages from chat history
        chat_messages = self.state.chat_histories.get(self.state.current_topic, [])
        display_messages = chat_messages[-(self.height - 4):] if chat_messages else ["No messages yet"]
        
        for idx, message in enumerate(display_messages):
            if isinstance(message, dict):
                # Format message from server response
                sender = message.get("sender", "Unknown")
                content = message.get("content", "")
                timestamp = message.get("timestamp", "")
                formatted_msg = f"{timestamp} - {sender}: {content}"
                self.window.addstr(idx + 1, 2, formatted_msg[:self.width - 4])
            else:
                # Format simple string message (like errors)
                self.window.addstr(idx + 1, 2, message[:self.width - 4])
        
        input_box_y = self.height - 2
        # Draw a bar dividing user input 
        self.window.addstr(input_box_y - 1, 2, "-" * (self.width - 4))

        # Always show the input prompt
        if self.state.mode == AppMode.NAVIGATION:
            self.window.addstr(input_box_y, 2, "> ", colors.WHITE_BLACK)
        elif self.state.mode == AppMode.CONTENT:
            self.window.addstr(input_box_y, 2, "> ", colors.CYAN_BLACK)
            if not self.is_typing:
                # When in content mode but not typing, show a highlight
                self.window.addstr(input_box_y, 4, " ", colors.BLACK_WHITE)
        
        self.window.refresh()
        return self.window
    
    def handle_input(self, key):
        if self.state.mode == AppMode.CONTENT:
            if key in (27,curses.KEY_LEFT):  # ESC or Left arrow to exit content mode
                self.state.mode = AppMode.NAVIGATION
            elif key == ord('\n'):  # Enter to start typing
                self.is_typing = True
                self.input_text = ""

                if self.handle_text_input():
                    if self.input_text.strip():
                        # Send message based on current chat type
                        try:
                            if self.state.current_chat_type == "friend":
                                self.state.client.chat_friend(self.state.current_topic, self.input_text)
                            elif self.state.current_chat_type == "group":
                                # For simplicity, assuming key is the group name
                                self.state.client.chat_group(self.state.current_topic, self.state.current_topic, self.input_text)
                            
                            # Refresh messages after sending
                            time.sleep(0.2)  # Give server time to process
                            self.state.refresh_needed = True
                        except Exception as e:
                            self.state.messages.append(f"Error sending message: {str(e)}")
                    
                    # Always reset input text after sending
                    self.input_text = ""
                
                self.is_typing = False
        return False
    
    def handle_text_input(self):
        """Handle text input with custom input management."""
        input_box_y = self.height - 2
        input_text = self.input_text.strip()
        cursor_pos = self.cursor_pos = len(input_text)
        max_width = self.width - 6  # Account for borders and prompt
        
        curses.curs_set(1)
        self._draw_input_line(input_box_y, input_text, cursor_pos)
        
        while True:
            try:
                key = self.window.getch()
                
                if key == 27:  
                    curses.curs_set(0)
                    cursor_pos = 0
                    self.input_text = input_text
                    return False
                    
                elif key == ord('\n'): 
                    curses.curs_set(0)
                    cursor_pos = 0
                    self.input_text = input_text
                    return True
                
                elif key == curses.KEY_LEFT and cursor_pos > 0:
                    cursor_pos -= 1
                    
                elif key == curses.KEY_RIGHT and cursor_pos < len(input_text):
                    cursor_pos += 1
                    
                elif key in (curses.KEY_BACKSPACE, 8, 127):  # Backspace
                    if cursor_pos > 0:
                        input_text = input_text[:cursor_pos-1] + input_text[cursor_pos:]
                        cursor_pos -= 1
                        
                elif key == curses.KEY_DC:  # Delete
                    if cursor_pos < len(input_text):
                        input_text = input_text[:cursor_pos] + input_text[cursor_pos+1:]
                        
                elif 32 <= key <= 126:  # Printable characters
                    if len(input_text) < max_width:
                        input_text = input_text[:cursor_pos] + chr(key) + input_text[cursor_pos:]
                        cursor_pos += 1
                
                self._draw_input_line(input_box_y, input_text, cursor_pos)
                
            except curses.error:
                curses.curs_set(0)
                return False
    
    def _draw_input_line(self, y, text, cursor_pos):
        max_visible = self.width - 8
        self.window.move(y, 2)
        self.window.clrtoeol()
        self.window.addstr(y, 2, "> ")
        
        if len(text) > max_visible:
            if cursor_pos < max_visible // 2:
                visible_text = text[:max_visible]
                display_cursor_pos = cursor_pos
            elif cursor_pos > len(text) - (max_visible // 2):
                visible_text = text[-(max_visible):]
                display_cursor_pos = cursor_pos - (len(text) - len(visible_text))
            else:
                start = cursor_pos - (max_visible // 2)
                visible_text = text[start:start + max_visible]
                display_cursor_pos = max_visible // 2
            
            self.window.addstr(y, 4, visible_text)
            self.window.move(y, 4 + display_cursor_pos)
        else:
            self.window.addstr(y, 4, text)
            self.window.move(y, 4 + cursor_pos)
            
        self.window.refresh()

# Welcome component
class WelcomeComponent(UIComponent):
    def resize(self, x, y, width, height):
        super().resize(x, y, width, height)

    def draw(self, colors):
        self.window.clear()
        self.window.border()
        # Display a proper welcome message with commands
        self.window.addstr(0, 2, " Welcome ", colors.CYAN_BLACK | curses.A_BOLD)
        
        welcome_message = [
            "Bem-vindo ao Chat de Infra-Com!      ",
            "Use as seguintes teclas para navegar:",
            "- ↑ / ↓: Navegar pelos menus         ",
            "- → / Enter: Selecionar item do menu ",
            "- ← / ESC: Voltar                    ",
            "",
            "Na tela Descobrir:                   ",
            "- 'a': Adicionar amigo               ",
            "- 'j': Entrar em grupo               "
        ]
        
        start_y = (self.height - len(welcome_message)) // 2
        
        for idx, line in enumerate(welcome_message):
            x = (self.width - len(line)) // 2  # Center the text horizontally
            self.window.addstr(start_y + idx, x, line)
        
        self.window.refresh()
        return self.window

# Login component
class LoginComponent(UIComponent):
    def __init__(self, app_state, title):
        super().__init__(app_state, title)
        self.username = ""
        self.error_message = ""
        
    def draw(self, colors):
        self.window.clear()
        self.window.border()
        self.window.addstr(0, 2, " Login ", colors.CYAN_BLACK | curses.A_BOLD)
        
        center_y = self.height // 2
        prompt_text = "Enter your username: "
        self.window.addstr(center_y - 2, (self.width - len(prompt_text)) // 2, prompt_text)
        
        # Draw input box
        box_width = 30
        box_x = (self.width - box_width) // 2
        self.window.addstr(center_y, box_x - 1, "┌" + "─" * box_width + "┐")
        self.window.addstr(center_y + 1, box_x - 1, "│")
        
        # Show username with padding if empty
        display_username = self.username if self.username else " "
        self.window.addstr(center_y + 1, box_x, display_username[:box_width].ljust(box_width))
        
        self.window.addstr(center_y + 1, box_x + box_width, "│")
        self.window.addstr(center_y + 2, box_x - 1, "└" + "─" * box_width + "┘")
        
        # Show instructions
        self.window.addstr(center_y + 4, (self.width - 30) // 2, "Press Enter to login")
        
        # Show error message if any
        if self.error_message:
            self.window.addstr(center_y + 6, (self.width - len(self.error_message)) // 2, 
                              self.error_message, colors.CYAN_BLACK)
        
        self.window.refresh()
        
    def handle_input(self, key):
        if key == ord('\n'):  # Enter key
            if not self.username.strip():
                self.error_message = "Username cannot be empty!"
                return False
                
            # Create client and attempt login
            self.state.client = Client(self.username)
            
            if self.state.client.login() is False:
                self.error_message = "Login failed"
                return False
            else:
                self.state.mode = AppMode.NAVIGATION
                self.state.selected_content = "Welcome"
                return True
                
        elif key in (curses.KEY_BACKSPACE, 8, 127):  # Backspace
            self.username = self.username[:-1]
            self.error_message = ""
        elif 32 <= key <= 126:  # Printable characters
            self.username += chr(key)
            self.error_message = ""
            
        return False

# Main application class
class ChatApp:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.state = AppState()
        self.menu_structure = {
            "Menu": ["Chats", "Grupos", "Amigos", "Descobrir", "Configurações", "Sair"],
            "Chats": ["Chat Geral"],
            "Grupos": [],  # Will be populated from server
            "Amigos": [],  # Will be populated from server
            "Descobrir": ["Usuários", "Grupos"],
            "Descobrir.Usuários": [],  # Will be populated from server
            "Descobrir.Grupos": [],    # Will be populated from server
            "Configurações": ["Opção 1", "Opção 2"],
            # No explicit "Voltar" option, use the arrow keys
        }
        # Map menu items to content components
        self.content_mapping = {
            "Chat Geral": "Chat",
            # Friends and groups will be added dynamically
        }
        self.setup_colors()
        self.menu = MenuComponent(self.state, "Menu", self.menu_structure, self.content_mapping)
        self.contents = {
            "Welcome": WelcomeComponent(self.state, "Bem-Vindo"),
            "Chat": ContentChatComponent(self.state, "Chat"),
        }
        self.login = LoginComponent(self.state, "Login")
        self.resize()
    
    def setup_colors(self):
        curses.start_color()
        curses.use_default_colors()
        
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_WHITE)
        
        class Colors:
            WHITE_BLACK = curses.color_pair(1)
            CYAN_BLACK = curses.color_pair(2)
            BLACK_WHITE = curses.color_pair(3)
            CYAN_WHITE = curses.color_pair(4)
        
        self.colors = Colors()
    
    def resize(self):
        sh, sw = self.stdscr.getmaxyx()
        left_width = sw // 4
        right_width = sw - left_width - 2
        content_height = sh - 2
        
        self.stdscr.clear()
        self.stdscr.attron(self.colors.CYAN_BLACK)
        self.stdscr.border()
        self.stdscr.attroff(self.colors.CYAN_BLACK)
        
        title = " Projeto Infra-Com: 3ª Entrega "
        self.stdscr.addstr(0, 2, title, self.colors.CYAN_BLACK | curses.A_BOLD)
        self.stdscr.refresh()
        
        self.menu.resize(1, 1, left_width, content_height)
        # Resize all registered content components
        for comp in self.contents.values():
            comp.resize(left_width + 1, 1, right_width, content_height)
        self.login.resize(1, 1, sw - 2, content_height)
    
    def run(self):
        curses.curs_set(0)
        
        while True:
            if self.state.mode == AppMode.LOGIN:
                self.login.draw(self.colors)
                key = self.stdscr.getch()
                if key == curses.KEY_RESIZE:
                    self.resize()
                else:
                    self.login.handle_input(key)
            else:
                self.menu.draw(self.colors)
                
                # Use Welcome as default when nothing is selected
                current_content = self.contents.get(self.state.selected_content, self.contents["Welcome"])
                current_content.draw(self.colors)
                
                key = self.stdscr.getch()
                if key == curses.KEY_RESIZE:
                    self.resize()
                elif self.state.mode == AppMode.NAVIGATION:
                    if self.menu.handle_input(key):
                        # Do logout before exiting
                        if self.state.client:
                            try:
                                self.state.client.logout()
                            except Exception:
                                pass
                        break
                elif self.state.mode == AppMode.CONTENT:
                    current_content.handle_input(key)

def main(stdscr):
    app = ChatApp(stdscr)
    app.run()

if __name__ == "__main__":
    curses.wrapper(main)