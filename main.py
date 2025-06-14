"""
Main entry point for the AI Agent SQL Assistant
"""

import subprocess
import sys
import os

def main():
    """Launch the SQL Assistant Chat UI using Streamlit"""
    
    print("🚀 Starting AI Agent SQL Assistant...")
    print("🔗 The web interface will open automatically")
    print("💡 Use Ctrl+C to stop the server")
    print("-" * 50)
    
    # Get the path to the chat UI file
    chat_ui_path = os.path.join("ai_agent_service", "chat_ui.py")
    
    # Launch Streamlit with the chat UI
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            chat_ui_path,
            "--server.port=8501",
            "--server.headless=false",
            "--browser.gatherUsageStats=false",
            "--theme.base=dark"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 SQL Assistant stopped. Goodbye!")
    except Exception as e:
        print(f"❌ Error starting SQL Assistant: {e}")
        print("🔧 Try running: streamlit run ai_agent_service/chat_ui.py")

if __name__ == "__main__":
    main()