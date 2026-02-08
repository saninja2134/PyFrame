import os
import sys

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Run the main script
if __name__ == "__main__":
    from src.main import OverlayController
    controller = OverlayController()
    controller.run()
