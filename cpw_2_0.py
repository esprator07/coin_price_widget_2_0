import customtkinter as ctk
import requests
import threading
import time
import json

# Visual theme settings
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class BinanceApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Binance USDT Pair Tracker")
        self.root.geometry("500x700")
        
        self.selected_coins = []
        self.all_coins = []
        self.coin_checkboxes = {}
        self.price_labels = {}
        self.previous_prices = {}
        
        self.create_welcome_page()
        
    def create_welcome_page(self):
        # Search box
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", self.filter_coins)
        search_entry = ctk.CTkEntry(
            self.root, 
            placeholder_text="Search coin...", 
            textvariable=self.search_var,
            width=400,
            height=35
        )
        search_entry.pack(pady=10)
        
        # Scrollable frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self.root, width=450, height=450)
        self.scrollable_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Info label
        self.info_label = ctk.CTkLabel(self.root, text="Loading coin list...")
        self.info_label.pack(pady=5)
        
        # Button - always visible at the bottom
        self.ok_button = ctk.CTkButton(
            self.root, 
            text="Confirm Selection (Max 10)", 
            command=self.proceed_to_price_tracker,
            state="disabled",
            width=200,
            height=35
        )
        self.ok_button.pack(pady=10)
        
        # Get coin list via thread
        threading.Thread(target=self.fetch_coin_list, daemon=True).start()
    
    def filter_coins(self, *args):
        search_text = self.search_var.get().upper()
        
        # Clear all widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Show filtered coins
        if search_text:
            filtered_coins = [coin for coin in self.all_coins if search_text in coin]
        else:
            filtered_coins = self.all_coins
        
        for coin in sorted(filtered_coins):
            self.add_coin_checkbox(coin)
    
    def add_coin_checkbox(self, coin):
        frame = ctk.CTkFrame(self.scrollable_frame, height=30)
        frame.pack(fill="x", pady=2, padx=5)
        
        var = ctk.IntVar()
        checkbox = ctk.CTkCheckBox(frame, text=coin, variable=var, width=300)
        checkbox.pack(side="left", padx=5, pady=2)
        
        # Track checkbox changes
        checkbox.configure(command=lambda c=coin, v=var: self.on_checkbox_change(c, v))
        
        self.coin_checkboxes[coin] = var
    
    def on_checkbox_change(self, coin, var):
        if var.get() == 1:
            if len(self.selected_coins) >= 10:
                var.set(0)  # Prevent selecting more than 10
                return
            self.selected_coins.append(coin)
        else:
            if coin in self.selected_coins:
                self.selected_coins.remove(coin)
        
        # Update button state
        self.ok_button.configure(state="normal" if self.selected_coins else "disabled")
        self.update_info_label()
    
    def update_info_label(self):
        count = len(self.selected_coins)
        self.info_label.configure(text=f"Selected coins: {count}/10")
    
    def fetch_coin_list(self):
        try:
            response = requests.get("https://api.binance.com/api/v3/exchangeInfo")
            data = response.json()
            
            # Filter USDT pairs
            usdt_pairs = [
                symbol['symbol'] for symbol in data['symbols'] 
                if symbol['symbol'].endswith('USDT') and symbol['status'] == 'TRADING'
            ]
            
            # Sort alphabetically
            self.all_coins = sorted(usdt_pairs)
            
            # UI update must be done in main thread
            self.root.after(0, self.display_coins)
            
        except Exception as e:
            self.root.after(0, lambda: self.info_label.configure(text=f"Error: {str(e)}"))
    
    def display_coins(self):
        # Clear previous widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # Show all coins
        for coin in self.all_coins:
            self.add_coin_checkbox(coin)
        
        self.info_label.configure(text=f"Total {len(self.all_coins)} USDT pairs found. You can select up to 10 coins.")
    
    def proceed_to_price_tracker(self):
        # Clear welcome page
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.create_price_tracker_page()
        
        # Start price tracking thread
        threading.Thread(target=self.update_prices, daemon=True).start()
    
    def create_price_tracker_page(self):
        self.root.title("")
        self.root.geometry("300x400")
        self.root.overrideredirect(False)  # Remove title bar but keep window controls
        self.root.attributes('-topmost', True)  # Always on top
        
        # Remove window title
        self.root.wm_attributes("-toolwindow", 1)
        
        # Scrollable frame
        self.price_frame = ctk.CTkScrollableFrame(self.root, width=280, height=380)
        self.price_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Create a price label for each coin
        for coin in self.selected_coins:
            frame = ctk.CTkFrame(self.price_frame, height=30, fg_color="transparent")
            frame.pack(fill="x", pady=2, padx=5)
            
            coin_label = ctk.CTkLabel(frame, text=coin, width=120)
            coin_label.pack(side="left", padx=5)
            
            price_label = ctk.CTkLabel(frame, text="Loading...", width=150, text_color="white")
            price_label.pack(side="left", padx=5)
            
            self.price_labels[coin] = price_label
            self.previous_prices[coin] = 0.0
        
        # Back button
        back_button = ctk.CTkButton(
            self.root, 
            text="Back", 
            command=self.go_back,
            width=100,
            height=30
        )
        back_button.pack(pady=5)
    
    def update_prices(self):
        while True:
            try:
                # Create URL
                symbols = [f'"{coin}"' for coin in self.selected_coins]
                url = f'https://api.binance.com/api/v3/ticker/price?&symbols=[{",".join(symbols)}]'
                
                response = requests.get(url)
                result = json.loads(response.content)
                
                # Update price for each coin
                for coin_data in result:
                    coin = coin_data['symbol']
                    current_price = float(coin_data['price'])
                    
                    # Determine color based on price change
                    if self.previous_prices[coin] > 0:
                        if current_price > self.previous_prices[coin]:
                            color = "green"
                        elif current_price < self.previous_prices[coin]:
                            color = "red"
                        else:
                            color = "white"  # Changed from black to white for dark theme
                    else:
                        color = "white"  # First load
                    
                    self.previous_prices[coin] = current_price
                    
                    # UI update must be done in main thread
                    self.root.after(0, lambda c=coin, p=current_price, col=color: 
                                   self.update_price_label(c, p, col))
                
                # Wait 10 seconds
                time.sleep(10)
                
            except Exception as e:
                print(f"Error: {str(e)}")
                time.sleep(10)
    
    def update_price_label(self, coin, price, color):
        if coin in self.price_labels:
            formatted_price = f"{price:.8f}".rstrip('0').rstrip('.')
            if len(formatted_price.split('.')[0]) < 4:
                formatted_price = f"{price:.8f}"
            
            self.price_labels[coin].configure(
                text=formatted_price,
                text_color=color
            )
    
    def go_back(self):
        # Clear price tracker page
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Reset selected coins
        self.selected_coins = []
        self.previous_prices = {}
        
        # Recreate welcome page
        self.create_welcome_page()
        
        # Remove always on top property
        self.root.attributes('-topmost', False)
        self.root.geometry("500x600")
        self.root.title("Binance USDT Pair Tracker")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = BinanceApp()
    app.run()
