import os
import subprocess
import sys
import time

def run_project():
    # Detect the current python executable (will use virtual environment python if active)
    python_bin = sys.executable
    print(f"Using Python: {python_bin}")

    # Check if .env file exists; if not, copy it from .env.example
    if not os.path.exists(".env"):
        print("📝 Creating .env from .env.example...")
        if os.path.exists(".env.example"):
            with open(".env.example", "r") as f_src:
                with open(".env", "w") as f_dest:
                    f_dest.write(f_src.read())
        else:
            print("⚠️ Warning: .env.example not found. Please create a .env file.")

    # 1. Run the data ingestion and dbt transformations
    print("\n🔄 Step 1: Running the Data Pipeline (Ingestion & Transformations)...")
    try:
        # Use Kaggle fallback data by default for speed, or switch to live API.
        # Let's run with '--source remotive' to fetch live data as standard,
        # but fallback to kaggle if it fails or if the user requests.
        result = subprocess.run([python_bin, "-m", "src.orchestration.runner", "--source", "all"])
        if result.returncode != 0:
            print("⚠️ Pipeline execution had issues, but attempting to start servers anyway...")
    except Exception as e:
        print(f"❌ Failed to run pipeline: {e}")

    # 2. Start the FastAPI API Server in the background
    print("\n⚡ Step 2: Starting FastAPI Backend Server on http://localhost:8000 ...")
    api_process = None
    try:
        api_process = subprocess.Popen(
            [python_bin, "-m", "uvicorn", "src.serving.api.main:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
    except Exception as e:
        print(f"❌ Failed to start FastAPI server: {e}")
        return

    # Wait for the API to boot up (simple check)
    time.sleep(3)

    # 3. Start the Streamlit Dashboard
    print("\n📊 Step 3: Starting Streamlit Dashboard on http://localhost:8501 ...")
    dashboard_process = None
    try:
        # Streamlit runs blockingly in the main thread
        dashboard_process = subprocess.run([
            python_bin, "-m", "streamlit", "run", "src/serving/dashboard/app.py", 
            "--server.address", "0.0.0.0", 
            "--server.port", "8501"
        ])
    except KeyboardInterrupt:
        print("\n👋 Stopping servers...")
    finally:
        # Clean up background process
        if api_process:
            print("Stopping FastAPI Backend...")
            api_process.terminate()
            try:
                api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                api_process.kill()
        print("✨ Done!")

if __name__ == "__main__":
    try:
        run_project()
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
