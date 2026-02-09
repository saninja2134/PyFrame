import PyInstaller.__main__
import os
import sys

# Define absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, 'src')
DIST_DIR = os.path.join(BASE_DIR, 'build_output', 'dist')
BUILD_DIR = os.path.join(BASE_DIR, 'build_output', 'build')
SPEC_DIR = os.path.join(BASE_DIR, 'build_output')

# Ensure output dirs exist
os.makedirs(DIST_DIR, exist_ok=True)

# --- CRITICAL FIX Check for PATH pollution ---
# We want to force PyInstaller to ONLY see our .venv and System32
venv_scripts = os.path.join(BASE_DIR, '.venv', 'Scripts')
venv_lib = os.path.join(BASE_DIR, '.venv', 'Lib', 'site-packages', 'PyQt6', 'Qt6', 'bin')
# Sanitize path to avoid picking up Anaconda/System Qt DLLs
original_path = os.environ['PATH']
os.environ['PATH'] = f"{venv_scripts};{venv_lib};C:\\Windows\\System32;C:\\Windows"

print(f"Build Path: {os.environ['PATH']}")

# Path to data
DATA_SRC = os.path.join(SRC_DIR, 'data')
DATA_DST = 'data'

# Run PyInstaller
PyInstaller.__main__.run([
    os.path.join(SRC_DIR, 'main.py'),
    '--name=PyFrame',
    '--onefile', # Changed from --onedir to --onefile for a single executable
    '--windowed',
    '--noconfirm',
    '--clean',
    f'--distpath={DIST_DIR}',
    f'--workpath={BUILD_DIR}',
    f'--specpath={SPEC_DIR}',
    
    # Critical: Add Data
    f'--add-data={DATA_SRC}{os.pathsep}{DATA_DST}',
    
    # Critical: Collect all PyQt6 components to avoid missing DLL/plugins
    '--collect-all=PyQt6',
    
    # Debug info (optional, helps if console was enabled, but we use windowed)
    # '--debug=all', 
])
