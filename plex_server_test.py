import os
import platform
import psutil
import subprocess
import requests
from time import time
import json
import threading
from plexapi.server import PlexServer

# Configuration
PLEX_URL = "http://localhost:32400"  # Change to your Plex server URL
PLEX_TOKEN = "YOUR_TOKEN_HERE"  # Provided Plex token
SAMPLE_VIDEO = "/DESTINATION/sample.mp4"  # Path to the sample video


# Core Functions
def get_system_info():
    """Gather basic system information."""
    info = {
        "OS": platform.system(),
        "OS Version": platform.version(),
        "OS Release": platform.release(),
        "Processor": platform.processor(),
        "CPU Cores": psutil.cpu_count(logical=False),
        "Logical CPUs": psutil.cpu_count(logical=True),
        "Memory": f"{psutil.virtual_memory().total / (1024 ** 3):.2f} GB",
    }
    return info


def monitor_system_metrics(duration=60):
    """Monitor CPU, memory, and disk usage over a given duration."""
    metrics = []
    end_time = time() + duration
    while time() < end_time:
        metrics.append({
            "timestamp": time(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent,
        })
    return metrics


def simulate_concurrent_streams(stream_count=5):
    """Simulate multiple concurrent streams using the Plex API."""
    plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    # Extract the sample video title from the file name (remove extension)
    video_title = os.path.splitext(os.path.basename(SAMPLE_VIDEO))[0]

    print(f"Searching for video '{video_title}' in Plex library...")
    search_results = plex.library.search(title=video_title)

    # Filter search results to include only video media
    video_results = [item for item in search_results if hasattr(item, "getStreamURL")]

    if not video_results:
        print(f"Error: Video '{video_title}' not found in Plex library or no valid video objects found.")
        return {"Concurrent Streams": f"Video '{video_title}' not found or invalid type"}

    video = video_results[0]  # Get the first matching video object

    print(f"Starting {stream_count} concurrent streams for '{video.title}'...")
    threads = []

    def play_stream(index):
        print(f"Stream {index + 1} started.")
        try:
            video.getStreamURL()  # Simulate requesting the video stream
        except Exception as e:
            print(f"Error in Stream {index + 1}: {e}")
        print(f"Stream {index + 1} ended.")

    for i in range(stream_count):
        thread = threading.Thread(target=play_stream, args=(i,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    return {"Concurrent Streams": f"Simulated {stream_count} streams successfully"}


def monitor_plex_transcoding():
    """Monitor Plex-specific metrics for active transcodes."""
    plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    sessions = plex.sessions()
    transcodes = []
    for session in sessions:
        if session.transcodeSession:
            transcodes.append({
                "title": session.grandparentTitle or session.title,
                "bitrate": session.transcodeSession.videoDecision,
                "container": session.transcodeSession.container,
                "videoCodec": session.transcodeSession.videoCodec,
            })
    return {"Active Transcodes": transcodes}


def test_transcoding():
    """Test transcoding performance using FFmpeg."""
    output_video = "/home/plex/Desktop/output.mp4"

    # Check if the input video exists
    if not os.path.exists(SAMPLE_VIDEO):
        print(f"Error: File not found: {SAMPLE_VIDEO}")
        return {"Transcoding Test": "Sample video not found"}

    print(f"Starting transcoding test for '{SAMPLE_VIDEO}'...")
    start_time = time()

    # Execute FFmpeg transcoding
    result = subprocess.run(
        ["ffmpeg", "-i", SAMPLE_VIDEO, "-vf", "scale=1280:720", "-preset", "fast", output_video],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    elapsed_time = time() - start_time

    if result.returncode == 0:
        # Successful transcoding
        os.remove(output_video)  # Clean up the output file after the test
        return {"Transcoding Test": f"Transcoding completed in {elapsed_time:.2f} seconds"}
    else:
        # Handle FFmpeg error
        print(f"FFmpeg error:\n{result.stderr}")
        return {"Transcoding Test": "FFmpeg failed"}


def generate_report(stream_count=5, metrics_duration=60):
    """Run all tests and generate a comprehensive Plex stress test report."""
    report = {}
    report["System Information"] = get_system_info()
    report["System Metrics"] = monitor_system_metrics(metrics_duration)
    report["Concurrent Streams"] = simulate_concurrent_streams(stream_count)
    report["Transcoding Test"] = test_transcoding()
    report["Plex Transcoding Metrics"] = monitor_plex_transcoding()
    return report


# Entry Point
if __name__ == "__main__":
    mode = input("Choose mode (report): ").strip().lower()

    if mode == "report":
        stream_count = int(input("Enter number of concurrent streams: "))
        metrics_duration = int(input("Enter metrics monitoring duration (seconds): "))
        print(f"Generating Plex stress test report using sample video: {SAMPLE_VIDEO}...")
        report = generate_report(stream_count, metrics_duration)
        print(json.dumps(report, indent=4))
    else:
        print("Invalid mode. Please choose 'report'.")
