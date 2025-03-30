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
    INPUT = auto()

# Centralized state management
class AppState:
    def __init__(self):
        self.mode = AppMode.NAVIGATION
        self.messages = ["Welcome to the chat room!"]
        self.selected_menu_idx = 0
        self.input_text = ""

# Base UI component class
class UIComponent:
    def __init__(self, app_state):
        self.state = app_state
    
    def draw(self, stdscr):
        pass
    
    def handle_input(self, key):
        return False  # Return True if the app should exit
    
    def resize(self):
        pass

# Menu component
class MenuComponent(UIComponent):
    def __init__(self, app_state, items, x, y, width, height):
        super().__init__(app_state)
        self.items = items
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.window = None
        self.create_window()
        
    def create_window(self):
        self.window = curses.newwin(self.height, self.width, self.y, self.x)
        self.window.keypad(True)
    
    def resize(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.create_window()
    
    def draw(self, colors):
        self.window.clear()
        self.window.border()
        self.window.addstr(0, 2, " Menu ", colors.CYAN_BLACK)
        
        for idx, item in enumerate(self.items):
            y = idx + 2
            if idx == self.state.selected_menu_idx:
                self.window.addstr(y, 2, "> ", colors.CYAN_BLACK)
                if self.state.mode == AppMode.INPUT:
                    self.window.addstr(y, 4, item, colors.WHITE_BLACK)
                else:
                    self.window.addstr(y, 4, item, colors.BLACK_WHITE)
            else:
                self.window.addstr(y, 2, f"  {item}")
        
        self.window.refresh()
    
    def handle_input(self, key):
        if self.state.mode == AppMode.NAVIGATION:
            if key == curses.KEY_UP and self.state.selected_menu_idx > 0:
                self.state.selected_menu_idx -= 1
            elif key == curses.KEY_DOWN and self.state.selected_menu_idx < len(self.items) - 1:
                self.state.selected_menu_idx += 1
            elif key in (ord('\n'), curses.KEY_RIGHT):
                if self.items[self.state.selected_menu_idx] == "Exit":
                    return True  # Signal app to exit
                self.state.mode = AppMode.INPUT
        return False

# Content component
class ContentComponent(UIComponent):
    def __init__(self, app_state, x, y, width, height):
        super().__init__(app_state)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.window = None
        self.is_typing = False  # Internal flag for typing mode
        self.cursor_pos = 0     # Cursor position in text input
        self.state.input_text = " "
        self.create_window()
        
    def create_window(self):
        self.window = curses.newwin(self.height, self.width, self.y, self.x)
        self.window.keypad(True)
    
    def resize(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.create_window()
    
    def draw(self, colors):
        self.window.clear()
        self.window.border()
        self.window.addstr(0, 2, " Chat Room ", colors.CYAN_BLACK)
        
        # Display messages
        for idx, message in enumerate(self.state.messages[-(self.height - 4):]):
            self.window.addstr(idx + 1, 2, message[:self.width - 4])
        
        # Draw input box separator
        input_box_y = self.height - 2
        self.window.addstr(input_box_y - 1, 2, "-" * (self.width - 4))
        
        # Draw input area based on component state
        self.window.addstr(input_box_y, 2, "> ", colors.CYAN_BLACK)
        
        if not self.is_typing:
            if self.state.mode == AppMode.INPUT:
                # Highlighted but not actively typing
                self.window.addstr(input_box_y, 4, self.state.input_text, colors.BLACK_WHITE)
            else:
                # Normal state
                self.window.addstr(input_box_y, 4, self.state.input_text)
        else:
            # Actively typing - handled separately by handle_text_input
            pass
            
        self.window.refresh()
        return self.window
    
    def handle_input(self, key):
        if self.state.mode == AppMode.INPUT:
            if key == 27:  # ESC to exit input mode and clear text
                self.state.input_text = " "
                self.state.mode = AppMode.NAVIGATION
            elif key == curses.KEY_LEFT:  # Left arrow to exit input mode
                self.state.mode = AppMode.NAVIGATION
            elif key == ord('\n'):  # Enter to start text input
                self.is_typing = True
                if self.handle_text_input():
                    self.state.messages.append(self.state.input_text.strip())
                    self.state.input_text = " "
                self.is_typing = False
        return False
    
    def handle_text_input(self):
        """Handle text input with custom input management."""
        input_box_y = self.height - 2
        input_text = self.state.input_text.strip()
        cursor_pos = self.cursor_pos = len(input_text)
        max_width = self.width - 6  # Account for borders and prompt
        
        # Show cursor and clear input line
        curses.curs_set(1)
        
        # First draw of input area
        self._draw_input_line(input_box_y, input_text, cursor_pos)
        
        while True:
            try:
                key = self.window.getch()
                
                if key == 27:  
                    curses.curs_set(0)
                    cursor_pos = 0
                    self.state.input_text = input_text
                    return False
                    
                elif key == ord('\n'): 
                    curses.curs_set(0)
                    cursor_pos = 0
                    self.state.input_text = input_text
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
                
                # Update and redraw input line
                self._draw_input_line(input_box_y, input_text, cursor_pos)
                
            except curses.error:
                # Handle curses error gracefully, e.g., during terminal resize
                curses.curs_set(0)
                return False
    
    
    def _draw_input_line(self, y, text, cursor_pos):
        """Draw the input line with cursor positioning."""

        max_visible = self.width - 8
        
        # Clear input line
        self.window.move(y, 2)
        self.window.clrtoeol()
        
        # Add prompt
        self.window.addstr(y, 2, "> ")
        
        # Handle scrolling for long text
        if len(text) > max_visible:
            # Determine visible portion based on cursor position
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
                
            # Draw text
            self.window.addstr(y, 4, visible_text)
            
            # Position cursor
            self.window.move(y, 4 + display_cursor_pos)
        else:
            # For short text, just show everything
            self.window.addstr(y, 4, text)
            self.window.move(y, 4 + cursor_pos)
            
        self.window.refresh()

# Main application class
class ChatApp:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.state = AppState()
        self.menu_items = ["Home", "Settings", "Help", "Exit"]
        self.setup_colors()
        
        # Initialize size and components after resize
        self.resize()
    
    def setup_colors(self):
        curses.start_color()
        curses.use_default_colors()
        
        # Define color pairs
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_WHITE)
        
        # Create a colors object for easier access
        class Colors:
            WHITE_BLACK = curses.color_pair(1)
            CYAN_BLACK = curses.color_pair(2)
            BLACK_WHITE = curses.color_pair(3)
            CYAN_WHITE = curses.color_pair(4)
        
        self.colors = Colors()
    
    def resize(self):
        # Get terminal dimensions
        sh, sw = self.stdscr.getmaxyx()
        
        # Calculate panel dimensions
        left_width = sw // 4
        right_width = sw - left_width - 2
        content_height = sh - 2
        
        # Clear screen and draw main border
        self.stdscr.clear()
        self.stdscr.attron(self.colors.CYAN_BLACK)
        self.stdscr.border()
        self.stdscr.attroff(self.colors.CYAN_BLACK)
        
        # Add title
        title = " Projeto Infra-Com: 3ª Entrega "
        self.stdscr.addstr(0, 2, title, self.colors.CYAN_BLACK | curses.A_BOLD)
        self.stdscr.refresh()
        
        # Create or resize components
        if not hasattr(self, 'menu'):
            self.menu = MenuComponent(self.state, self.menu_items, 1, 1, left_width, content_height)
            self.content = ContentComponent(self.state, left_width + 1, 1, right_width, content_height)
        else:
            self.menu.resize(1, 1, left_width, content_height)
            self.content.resize(left_width + 1, 1, right_width, content_height)
    
    def run(self):
        curses.curs_set(0)  # Hide cursor by default
        
        while True:
            # Draw components
            self.menu.draw(self.colors)
            self.content.draw(self.colors)
            
            # Handle input
            key = self.stdscr.getch()
            
            if key == curses.KEY_RESIZE:
                self.resize()
            elif self.state.mode == AppMode.NAVIGATION:
                if self.menu.handle_input(key):
                    break
            elif self.state.mode == AppMode.INPUT:
                self.content.handle_input(key)

def main(stdscr):
    app = ChatApp(stdscr)
    app.run()

if __name__ == "__main__":
    curses.wrapper(main)