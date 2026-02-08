import sys
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

        # Setup timer for periodic updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_world_data)
        self.timer.start(120000)  # Update world state every 2 mins

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

    def update_world_data(self):
        # Fetch world state info
        state = WarframeAPI.get_world_state()
        if state:
            try:
                # --- Tab 1: Cycles ---
                # Earth
                e = state.get('earthCycle', {})
                earth = f"{e.get('state', 'Unknown').capitalize()} ({e.get('timeLeft', '')})"
                
                # Cetus
                c = state.get('cetusCycle', {})
                cetus = f"{c.get('state', 'Unknown').capitalize()} ({c.get('timeLeft', '')})"
                
                # Vallis (might not have timeLeft, depends on provider state)
                v = state.get('vallisCycle', {})
                vallis = f"{v.get('state', 'Unknown').capitalize()} ({v.get('timeLeft', '')})" if v.get('timeLeft') else v.get('state', 'Unknown').capitalize()
                
                # Cambion
                cam = state.get('cambionCycle', {})
                cambion = f"{cam.get('active', cam.get('state', 'Unknown')).capitalize()} ({cam.get('timeLeft', '')})"
                
                # Zariman
                z = state.get('zarimanCycle', {})
                zariman = f"{z.get('state', 'Unknown').capitalize()} ({z.get('timeLeft', '')})"
                
                cycles_text = (
                    f"<b>Cycles:</b><br>"
                    f"Earth: {earth}<br>"
                    f"Cetus: {cetus}<br>"
                    f"Vallis: {vallis}<br>"
                    f"Cambion: {cambion}<br>"
                    f"Zariman: {zariman}<br><br>"
                )
                
                # Nightwave
                nw = state.get('nightwave')
                if nw and nw.get('activeChallenges'):
                    cycles_text += "<b>Nightwave:</b><br>"
                    for c in nw['activeChallenges'][:3]:
                        cycles_text += f"- {c['title']} ({c['reputation']})<br>"
                
                self.overlay.update_cycles_tab(cycles_text)

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

    def run(self):
        self.overlay.show()
        sys.exit(self.app.exec())

if __name__ == "__main__":
    controller = OverlayController()
    controller.run()
