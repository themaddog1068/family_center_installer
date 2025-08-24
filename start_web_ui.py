#!/usr/bin/env python3
"""
Simple script to start the web configuration interface.
"""

import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from src.config.config_manager import ConfigManager
    from src.services.web_config_ui import create_web_config_ui
    from src.services.web_content_service import create_web_content_service
except ImportError:
    print(
        "❌ Error: Could not import required modules. Make sure you're in the correct directory."
    )
    sys.exit(1)


def main():
    print("🌐 Starting Web Config UI...")
    print("🌐 Web config UI will be available at: http://localhost:8080/config")

    # Initialize services
    config_manager = ConfigManager()
    web_content_service = create_web_content_service(config_manager)

    # Create and start web config UI
    web_config_ui = create_web_config_ui(config_manager, web_content_service)

    print("🏠 Initializing Web Config UI...")
    print("🌐 Starting web config UI on http://localhost:8080")

    try:
        web_config_ui.start(host="0.0.0.0", port=8080)
    except KeyboardInterrupt:
        print("\n🛑 Web Config UI stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
