"""
Launcher for Annual Report Analyser.
This ensures the app always runs from the src directory.
"""
import os
import sys
from pathlib import Path

def main():
    """Launch the Streamlit app from the src directory."""
    # Get the project root (where this file is located)
    project_root = Path(__file__).parent.resolve()
    src_dir = project_root / "src"
    
    # Change working directory to src
    os.chdir(src_dir)
    print(f"Working directory set to: {os.getcwd()}")
    
    # Run streamlit
    os.system(f"{sys.executable} -m streamlit run app.py")


if __name__ == "__main__":
    main()
