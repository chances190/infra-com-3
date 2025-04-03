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

# Define application states as an enum
class AppMode(Enum):
    NAVIGATION = auto()
    CONTENT = auto()

# Centralized state management
class AppState:
    def __init__(self):
        self.mode = AppMode.NAVIGATION
        self.messages = ["Welcome to the chat room!"]
        self.selected_content = ""

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
    def __init__(self, app_state, title, menu_structure):
        super().__init__(app_state, title)
        self.menu_structure = menu_structure
        self.selected_menu_idx = 0  # Local state for menu index
        self.previous_menu_idx = {title: 0}  # Track previous indices for each menu locally
    
    def draw(self, colors):
        self.window.clear()
        self.window.border()
        self.window.addstr(0, 2, f" {self.title} ", colors.CYAN_BLACK)  # Use title property
        
        current_menu_items = self.menu_structure[self.title]
        for idx, item in enumerate(current_menu_items):
            y = idx + 2
            if idx == self.selected_menu_idx:
                self.window.addstr(y, 2, "> ", colors.CYAN_BLACK)
                self.window.addstr(y, 4, item, colors.WHITE_BLACK)
            else:
                self.window.addstr(y, 2, f"  {item}")
        
        self.window.refresh()
    
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
            else:
                # Ensure selected_content is set correctly
                self.state.mode = AppMode.CONTENT
                self.state.selected_content = selected_item
        elif key in (27, curses.KEY_LEFT):
            self.state.selected_content = ""
            if self.title != "Menu":
                parent_menu = "Menu"
                for menu, items in self.menu_structure.items():
                    if self.title in items:
                        parent_menu = menu
                        break
                self.previous_menu_idx[self.title] = self.selected_menu_idx
                self.title = parent_menu  # Update title to the parent menu
                self.selected_menu_idx = self.previous_menu_idx.get(parent_menu, 0)
        
        return False

# Content component
class ContentChatComponent(UIComponent):
    def __init__(self, app_state, title):
        super().__init__(app_state, title)
        self.is_typing = False  # Internal flag for typing mode
        self.cursor_pos = 0     # Cursor position in text input
        self.input_text = " "
    
    def draw(self, colors):
        self.window.clear()
        self.window.border()
        self.window.addstr(0, 2, f" Chat: {self.state.selected_content} ", colors.CYAN_BLACK)
        
        for idx, message in enumerate(self.state.messages[-(self.height - 4):]):
            self.window.addstr(idx + 1, 2, message[:self.width - 4])
        
        input_box_y = self.height - 2
        self.window.addstr(input_box_y - 1, 2, "-" * (self.width - 4))

        if self.state.mode == AppMode.CONTENT:
            self.window.addstr(input_box_y, 2, "> ", colors.CYAN_BLACK)
            if not self.is_typing:
                self.window.addstr(input_box_y, 4, self.input_text, colors.BLACK_WHITE)
            else:
                pass  # Typing handled separately
        else:
            self.window.addstr(input_box_y, 2, "> ")
        
        self.window.refresh()
        return self.window
    
    def handle_input(self, key):
        if self.state.mode == AppMode.CONTENT:
            if key == 27:  # ESC to exit content mode
                self.input_text = " "
                self.state.mode = AppMode.NAVIGATION
            elif key == curses.KEY_LEFT:  # Left arrow to exit content mode
                self.state.mode = AppMode.NAVIGATION
            elif key == ord('\n'):  # Enter to start typing
                self.is_typing = True
                if self.handle_text_input():
                    self.state.messages.append(self.input_text.strip())
                    self.input_text = " "
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
            "- ← / ESC: Voltar                    "
        ]
        
        start_y = (self.height - len(welcome_message)) // 2
        
        for idx, line in enumerate(welcome_message):
            x = (self.width - len(line)) // 2  # Center the text horizontally
            self.window.addstr(start_y + idx, x, line)
        
        self.window.refresh()
        return self.window

# Direct Messages component
class DirectMessagesComponent(UIComponent):
    def resize(self, x, y, width, height):
        super().resize(x, y, width, height)

    def draw(self, colors):
        self.window.clear()
        self.window.border()
        self.window.addstr(0, 2, " Direct Messages ", colors.CYAN_BLACK)
        self.window.refresh()
        return self.window


# Main application class
class ChatApp:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.state = AppState()
        self.menu_structure = {
            "Menu": ["Chats", "Grupos", "Amigos", "Configurações", "Sair"],
            "Chats": ["Chat"],
            "Grupos": ["Grupo 1", "Grupo 2"],
            "Amigos": ["Pessoa 1", "Pessoa 2"],
            "Configurações": ["Opção 1", "Opção 2"],
        }
        self.setup_colors()
        self.menu = MenuComponent(self.state, "Menu", self.menu_structure)
        self.contents = {
            "Welcome": WelcomeComponent(self.state, "Bem-Vindo"),
            "Chat": ContentChatComponent(self.state, "Chat"),
            "DMs": DirectMessagesComponent(self.state, "DMs"),
        }
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
    
    def run(self):
        curses.curs_set(0)
        
        while True:
            self.menu.draw(self.colors)
            
            current_content = self.contents.get(self.state.selected_content, self.contents["Chat"])
            current_content.draw(self.colors)
            
            key = self.stdscr.getch()
            if key == curses.KEY_RESIZE:
                self.resize()
            elif self.state.mode == AppMode.NAVIGATION:
                if self.menu.handle_input(key):
                    break
            elif self.state.mode == AppMode.CONTENT:
                current_content.handle_input(key)

def main(stdscr):
    app = ChatApp(stdscr)
    app.run()

if __name__ == "__main__":
    curses.wrapper(main)