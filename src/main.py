import sys
import time
from datetime import datetime, timezone
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from overlay import WarframeOverlay
from api_clients import WarframeAPI, WarframeReference
from pynput import keyboard

class OverlayController(QObject):
    toggle_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.overlay = WarframeOverlay()
        self.visible = True
        
        # State storage for cycles
        self.cycle_data = {}
        self.nightwave_html = ""
        self.last_fetch_time = 0
        
        # Initialize Reference Tab
        self.overlay.set_reference_text(WarframeReference.DAMAGE_TABLE)

        # Connect internal signals for thread safety
        self.toggle_requested.connect(self.toggle_visibility_safe)
        self.quit_requested.connect(self.quit_app_safe)

        # Connect search signal
        self.overlay.search_triggered.connect(self.handle_search)
        self.overlay.exit_triggered.connect(self.quit_app_safe)

        # Setup hotkey listener
        self.listener = keyboard.GlobalHotKeys({
            '<ctrl>+<alt>+o': self.emit_toggle,
            '<ctrl>+<alt>+x': self.emit_quit
        })
        self.listener.start()

        # Timer for data fetching (Sync every 2 mins)
        self.fetch_timer = QTimer()
        self.fetch_timer.timeout.connect(self.update_world_data)
        self.fetch_timer.start(120000)

        # Timer for UI countdowns (Every 1 second)
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_cycle_display)
        self.ui_timer.start(1000)

        self.update_world_data()

    def emit_toggle(self):
        self.toggle_requested.emit()

    def emit_quit(self):
        self.quit_requested.emit()

    def toggle_visibility_safe(self):
        self.visible = not self.visible
        if self.visible:
            self.overlay.show()
            self.overlay.raise_()
            self.overlay.activateWindow()
        else:
            self.overlay.hide()

    def quit_app_safe(self):
        self.listener.stop()
        self.overlay.close()
        if hasattr(self.overlay, 'browser'):
            self.overlay.browser.setPage(None)
        self.app.quit()

    def handle_search(self, query):
        self.overlay.update_search_results(f"Searching for '{query}'...")
        
        # Price Check
        price_text, full_name = WarframeAPI.get_market_item_price(query)
        
        # Wiki Info
        wiki_text = WarframeAPI.get_wiki_info(full_name)
        
        # Drop / Acqusition Info
        drop_text = WarframeAPI.get_drop_locations(full_name)

        # Compile HTML for Summary
        summary_html = f"""
        <style>
            h3 {{ margin-top: 0; margin-bottom: 5px; color: #00d2ff; font-size: 14px; }}
            div {{ margin-bottom: 10px; }}
            b {{ color: #eee; }}
        </style>
        <h2 style='color: #fff; margin-bottom: 10px;'>{full_name}</h2>
        <div>{price_text}</div>
        <div>{drop_text}</div>
        <div style='font-size: 11px;'>{wiki_text}</div>
        """
        
        # Update Info Tab (Top Section)
        self.overlay.set_reference_text(summary_html)
        
        # Update Search Tab (optional, but good for history)
        self.overlay.update_search_results(summary_html)

        # BiS Mods URL (Bottom Section)
        bis_url = WarframeAPI.get_bis_mods(full_name)
        if bis_url.startswith("http"):
            self.overlay.load_build_url(bis_url)
        else:
            # Load Overframe home or search if no direct hit
            self.overlay.load_build_url(bis_url if "http" in bis_url else "https://overframe.gg")

    def parse_time(self, time_str):
        if not time_str: return None
        try:
            # Handle ISO strings (e.g., 2026-02-08T20:00:00.558Z)
            return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except:
            return None

    def update_cycle_display(self):
        if not self.cycle_data: return

        now = datetime.now(timezone.utc)
        cycle_lines = []
        needs_refresh = False

        term_map = {
            'earth': 'Earth', 'cetus': 'Cetus', 'vallis': 'Vallis', 
            'cambion': 'Cambion', 'zariman': 'Zariman'
        }

        cycle_lines.append("<b>Cycles:</b>")
        
        for key, label in term_map.items():
            info = self.cycle_data.get(key)
            if not info:
                cycle_lines.append(f"{label}: N/A")
                continue
            
            expiry = info.get('expiry')
            state_str = info.get('state', 'Unknown').capitalize()

            if expiry:
                delta = expiry - now
                total_seconds = int(delta.total_seconds())

                if total_seconds <= 0:
                    needs_refresh = True
                    # Just show 0s or Validating if it's lagging behind
                    time_str = "Syncing..."
                else:
                    # Format time left
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    
                    parts = []
                    if hours > 0: parts.append(f"{hours}h")
                    parts.append(f"{minutes}m")
                    parts.append(f"{seconds}s")
                    time_str = " ".join(parts)
                
                cycle_lines.append(f"{label}: {state_str} ({time_str})")
            else:
                cycle_lines.append(f"{label}: {state_str}")

        if needs_refresh:
            # Prevent spamming API (Cooldown of 15s)
            # If a cycle ends, it needs a bit to update serverside anyway
            if time.time() - self.last_fetch_time > 15:
                print("Cycle expired, refreshing...")
                self.update_world_data()

        final_html = "<br>".join(cycle_lines) + "<br><br>" + self.nightwave_html
        self.overlay.update_cycles_tab(final_html)

    def update_world_data(self):
        # Fetch world state info
        state = WarframeAPI.get_world_state()
        self.last_fetch_time = time.time()
        
        if state:
            try:
                # --- Tab 1: Cycles ---
                # Store Data for Local Countdown
                self.cycle_data = {
                    'earth': {
                        'state': state.get('earthCycle', {}).get('state', 'Unknown'),
                        'expiry': self.parse_time(state.get('earthCycle', {}).get('expiry'))
                    },
                    'cetus': {
                        'state': state.get('cetusCycle', {}).get('state', 'Unknown'),
                        'expiry': self.parse_time(state.get('cetusCycle', {}).get('expiry'))
                    },
                    'vallis': {
                        'state': state.get('vallisCycle', {}).get('state', 'Unknown'),
                        'expiry': self.parse_time(state.get('vallisCycle', {}).get('expiry'))
                    },
                    'cambion': {
                        'state': state.get('cambionCycle', {}).get('active', state.get('cambionCycle', {}).get('state', 'Unknown')),
                        'expiry': self.parse_time(state.get('cambionCycle', {}).get('expiry'))
                    },
                    'zariman': {
                        'state': state.get('zarimanCycle', {}).get('state', 'Unknown'),
                        'expiry': self.parse_time(state.get('zarimanCycle', {}).get('expiry'))
                    }
                }
                
                # Nightwave (Static until next fetch)
                nw = state.get('nightwave')
                self.nightwave_html = ""
                if nw and nw.get('activeChallenges'):
                    self.nightwave_html += "<b>Nightwave:</b><br>"
                    for c in nw['activeChallenges'][:3]:
                        self.nightwave_html += f"- {c['title']} ({c['reputation']})<br>"
                
                # Update Activities directly
                self.update_cycle_display()

                # --- Tab 2: Activities ---
                activities_text = ""
                
                # Sortie
                sortie = state.get('sortie', {})
                if sortie:
                    boss = sortie.get('boss', 'Unknown')
                    faction = sortie.get('faction', 'Unknown')
                    activities_text += f"<b>Sortie ({boss} - {faction}):</b><br>"
                    for idx, mission in enumerate(sortie.get('variants', []), 1):
                        activities_text += f"{idx}. {mission['missionType']} - {mission.get('modifier', 'None')}<br>"
                    activities_text += "<br>"

                # Archon Hunt
                archon = state.get('archonHunt', {})
                if archon:
                    boss = archon.get('boss', 'Unknown')
                    activities_text += f"<b>Archon Hunt ({boss}):</b><br>"
                    for idx, mission in enumerate(archon.get('variants', []), 1):
                        activities_text += f"{idx}. {mission['missionType']}<br>"
                    activities_text += "<br>"

                # Void Trader
                trader = state.get('voidTrader', {})
                activities_text += f"<b>Void Trader:</b><br>{WarframeAPI.process_void_trader(trader)}<br><br>"

                # Invasions
                invasions = WarframeAPI.process_invasions(state.get('invasions', []))
                if invasions:
                    activities_text += "<b>Interesting Invasions:</b><br>"
                    for inv in invasions:
                        activities_text += f"- {inv}<br>"
                    activities_text += "<br>"

                # Fissures (only non-standard/SP/Storms or just basic summary)
                # Let's show active fissures counts or high tier ones
                fissures = state.get('fissures', [])
                if fissures:
                    activities_text += f"<b>Active Fissures: {len(fissures)}</b><br>"
                
                self.overlay.update_activities_tab(activities_text)

            except Exception as e:
                err_msg = f"Error parsing state: {e}"
                self.overlay.update_cycles_tab(err_msg)
        else:
            self.overlay.update_cycles_tab("Failed to fetch world state data.<br>Check internet connection.")
            self.overlay.update_activities_tab("Failed to fetch world state.")

    def run(self):
        self.overlay.show()
        sys.exit(self.app.exec())

if __name__ == "__main__":
    controller = OverlayController()
    controller.run()
