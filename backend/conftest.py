import sys
from pathlib import Path

# Add the backend directory to the Python path so that imports work correctly
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
