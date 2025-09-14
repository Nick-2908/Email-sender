import subprocess
import os
import sys

def main():
    """Run the Streamlit application from the project root directory"""
    
    # Get the directory where this script is located (project root)
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the frontend directory
    frontend_dir = os.path.join(project_root, 'frontend')
    
    # Path to the app.py file
    app_path = os.path.join(frontend_dir, 'app.py')
    
    # Check if the app.py file exists
    if not os.path.exists(app_path):
        print(f"❌ Error: app.py not found at {app_path}")
        print("Make sure you have the correct project structure:")
        print("├── backend/")
        print("│   └── backend.py")
        print("├── frontend/")
        print("│   └── app.py")
        print("└── run.py")
        sys.exit(1)
    
    # Check if .env file exists
    env_path = os.path.join(project_root, '.env')
    if not os.path.exists(env_path):
        print("⚠️  Warning: .env file not found!")
        print("Create a .env file with your Google API key:")
        print("GOOGLE_API_KEY=your_api_key_here")
        print()
    
    print("🚀 Starting Email Drafting Assistant...")
    print(f"📁 Project root: {project_root}")
    print(f"🎯 Running: streamlit run {app_path}")
    print("🌐 The app will open in your browser automatically")
    print()
    print("Press Ctrl+C to stop the application")
    print("-" * 50)
    
    try:
        # Run streamlit with the app.py file
        subprocess.run([
            'streamlit', 'run', app_path,
            '--server.address', 'localhost',
            '--server.port', '8501',
            '--browser.gatherUsageStats', 'false'
        ], cwd=project_root)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except FileNotFoundError:
        print("❌ Error: Streamlit not found!")
        print("Install it with: pip install streamlit")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()