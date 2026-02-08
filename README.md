# PyFrame - Python Warframe Overlay

A lightweight, non-Overwolf based overlay for Warframe.

## Features
- **Cycles & Activities**: Track Earth/Cetus/Vallis/Cambion cycles, plus Sorties, Archon Hunts, and Void Trader inventory.
- **Enhanced Search**: 
    - **Market Pricing**: Lowest online prices.
    - **Drop Locations**: Precise drop sources from official API.
    - **Wiki Integration**: Lore and stats summaries.
    - **Live Builds**: View top Overframe builds directly in the overlay via embedded browser.
- **Reference Library**: Built-in Damage Type effectiveness and Status Effect charts.
- **Smart Filtering**: Only shows Invasions with valuable rewards (Potatoes, Forma, Wraiths).
- **Notes Tab**: Keep track of your farming goals.
- **Stealth Mode**: `Ctrl+Alt+O` to toggle global visibility.

## Installation
1. Install Python 3.8+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python src/main.py
   ```
   Or simply run `run.bat`.

## Usage
- **Drag**: Click and drag the overlay to reposition.
- **Search**: Type an item name in the search bar and press Enter.
- **Toggle**: Use `Ctrl+Alt+O` to hide/show.
- **Exit**: Use `Ctrl+Alt+X` or close the terminal / `run.bat` window.
