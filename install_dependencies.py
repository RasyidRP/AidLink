import subprocess
import sys

# List of required packages
required_packages = [
    'osmnx',
    'folium',
    'networkx',
    'flask',
    'shapely',
    'firebase-admin',
    'pandas'
]

# Install each package if not already installed
for package in required_packages:
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
