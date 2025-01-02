import os
import platform
import psutil
import subprocess
import speedtest
from time import time
import json
import socket
import requests


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


def cpu_benchmark():
    """Perform a simple CPU benchmark."""
    start_time = time()
    for _ in range(10**7):
        _ = 3.14159 * 2.71828
    elapsed_time = time() - start_time
    return {"CPU Benchmark (10M ops)": f"{elapsed_time:.2f} seconds"}


def analyze_ffprobe(video_path):
    """Run ffprobe to extract video details."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=codec_name,width,height,bit_rate", "-of", "json", video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode == 0:
            return result.stdout  # JSON formatted video details
        else:
            print(f"Error running ffprobe:\n{result.stderr}")
            return None
    except FileNotFoundError:
        print("Error: ffprobe is not installed or not in PATH.")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


def evaluate_transcoding(duration, elapsed_time, resolution):
    """Evaluate the transcoding speed based on video properties."""
    real_time_ratio = elapsed_time / duration
    feedback = f"Transcoding completed in {elapsed_time:.2f} seconds.\n"
    feedback += f"Real-time ratio: {real_time_ratio:.2f}x\n"
    
    if real_time_ratio <= 1.0:
        feedback += "Excellent speed (faster than real-time transcoding).\n"
    elif real_time_ratio <= 2.0:
        feedback += "Good speed for CPU-based transcoding.\n"
    else:
        feedback += "Slow speed. Consider using hardware acceleration (e.g., NVENC).\n"
    
    if resolution[1] > 1080:
        feedback += "4K video transcoding is resource-intensive; consider upgrading hardware.\n"
    elif resolution[1] > 720:
        feedback += "1080p video transcoding is reasonable but can benefit from GPU acceleration.\n"
    else:
        feedback += "720p or lower resolution is relatively lightweight for most systems.\n"
    
    return feedback


def test_transcoding():
    """Test transcoding performance using FFmpeg."""
    sample_video = "/LOCATION/OF/sample.mp4"
    output_video = "/LOCATION/OF/output.mp4"

    # Check if the input video exists
    if not os.path.exists(sample_video):
        print(f"Error: File not found: {sample_video}")
        return {"Transcoding Test": "Sample video not found"}

    # Extract video details using ffprobe
    ffprobe_output = analyze_ffprobe(sample_video)
    if not ffprobe_output:
        return {"Transcoding Test": "Failed to analyze video properties"}
    
    # Parse ffprobe JSON
    ffprobe_data = json.loads(ffprobe_output)
    duration = float(ffprobe_data["format"]["duration"])
    width = int(ffprobe_data["streams"][0]["width"])
    height = int(ffprobe_data["streams"][0]["height"])
    codec_name = ffprobe_data["streams"][0]["codec_name"]
    bitrate = int(ffprobe_data["format"].get("bit_rate", 0)) / 1e6  # Convert to Mbps

    print(f"Video Details:\n- Codec: {codec_name}\n- Resolution: {width}x{height}\n- Duration: {duration:.2f}s\n- Bitrate: {bitrate:.2f} Mbps")

    try:
        print("Starting transcoding test...")
        start_time = time()

        # Execute FFmpeg transcoding
        result = subprocess.run(
            ["ffmpeg", "-i", sample_video, "-vf", "scale=1280:720", "-preset", "fast", output_video],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        elapsed_time = time() - start_time

        if result.returncode == 0:
            # Successful transcoding
            os.remove(output_video)  # Clean up the output file after the test
            feedback = evaluate_transcoding(duration, elapsed_time, (width, height))
            print(feedback)
            return {"Transcoding Test": feedback}
        else:
            # Handle FFmpeg error
            print(f"FFmpeg error:\n{result.stderr}")
            return {"Transcoding Test": "FFmpeg failed"}

    except FileNotFoundError:
        print("Error: FFmpeg is not installed or not in PATH.")
        return {"Transcoding Test": "FFmpeg not installed"}

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"Transcoding Test": f"Unexpected error: {str(e)}"}


def network_test_manual():
    """Measure download speed manually using wget."""
    import shutil
    test_url = "http://speedtest.tele2.net/1MB.zip"  # Test file URL
    test_file = "test_file.zip"
    try:
        start_time = time()
        with open(test_file, "wb") as f:
            with requests.get(test_url, stream=True) as r:
                shutil.copyfileobj(r.raw, f)
        elapsed_time = time() - start_time
        file_size_mb = 1  # 1MB test file
        download_speed = file_size_mb / elapsed_time * 8  # Convert to Mbps
        os.remove(test_file)
        return {"Download Speed (Manual)": f"{download_speed:.2f} Mbps"}
    except Exception as e:
        return {"Network Test (Manual)": f"Failed - {str(e)}"}


def disk_io_test():
    """Measure disk read/write performance."""
    test_file = "disk_test.tmp"
    try:
        # Write test
        start_time = time()
        with open(test_file, "wb") as f:
            f.write(os.urandom(100 * 1024 * 1024))
        write_time = time() - start_time

        # Read test
        start_time = time()
        with open(test_file, "rb") as f:
            f.read()
        read_time = time() - start_time

        os.remove(test_file)
        return {
            "Disk Write Speed": f"{100 / write_time:.2f} MB/s",
            "Disk Read Speed": f"{100 / read_time:.2f} MB/s"
        }
    except Exception as e:
        return {"Disk I/O Test": f"Failed - {str(e)}"}


def generate_report():
    """Run all tests and generate a comprehensive report."""
    report = {}
    report["System Information"] = get_system_info()
    report.update(cpu_benchmark())
    report.update(test_transcoding())
    report.update(network_test_manual())
    report.update(disk_io_test())
    return report


# Server Function
def server(host="0.0.0.0", port=5000):
    """Start a server to handle client test requests."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Server listening on {host}:{port}")
    
    while True:
        client_socket, address = server_socket.accept()
        print(f"Connection from {address}")
        
        try:
            # Receive request
            request = client_socket.recv(1024).decode("utf-8")
            if request == "RUN_TESTS":
                print("Running tests...")
                report = generate_report()
                # Send report to client
                client_socket.send(json.dumps(report).encode("utf-8"))
        except Exception as e:
            print(f"Error: {e}")
        finally:
            client_socket.close()


# Client Function
def client(server_host, server_port):
    """Connect to the server and request tests."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((server_host, server_port))
        client_socket.send("RUN_TESTS".encode("utf-8"))
        
        # Receive and print report
        response = client_socket.recv(1024 * 10).decode("utf-8")
        report = json.loads(response)
        print(json.dumps(report, indent=4))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()


# Entry Point
if __name__ == "__main__":
    mode = input("Choose mode (report/server/client): ").strip().lower()

    if mode == "report":
        print("Generating report...")
        report = generate_report()
        print(json.dumps(report, indent=4))
    elif mode == "server":
        server_host = input("Enter server host (default 0.0.0.0): ") or "0.0.0.0"
        server_port = int(input("Enter server port (default 5000): ") or "5000")
        server(server_host, server_port)
    elif mode == "client":
        server_host = input("Enter server host (default localhost): ") or "localhost"
        server_port = int(input("Enter server port (default 5000): ") or "5000")
        client(server_host, server_port)
    else:
        print("Invalid mode. Please choose 'report', 'server', or 'client'.")
