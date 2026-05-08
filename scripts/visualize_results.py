import json
import argparse
from datetime import datetime
from collections import defaultdict

def main():
    parser = argparse.ArgumentParser(description="Visualize K6 JSON output")
    parser.add_argument("input_file", help="Path to k6 JSON output file")
    args = parser.parse_args()

    # Track metrics over time
    # bucket by second
    timeline = defaultdict(lambda: {"202": 0, "429": 0, "500": 0, "other": 0})
    
    with open(args.input_file, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get("type") == "Point" and data.get("metric") == "http_reqs":
                    timestamp = data["data"]["time"]
                    # K6 time format is like "2023-10-12T14:32:00.000Z"
                    # truncate to second
                    time_sec = timestamp[:19]
                    
                    status = str(data["data"]["tags"].get("status", "other"))
                    if status not in ["202", "429", "500"]:
                        status = "other"
                        
                    timeline[time_sec][status] += 1
            except Exception as e:
                pass

    if not timeline:
        print("No valid HTTP request data found in the JSON file.")
        return

    # Sort by time
    sorted_times = sorted(timeline.keys())
    
    # Try to plot if matplotlib is available
    try:
        import matplotlib.pyplot as plt
        
        times = [datetime.strptime(t, "%Y-%m-%dT%H:%M:%S") for t in sorted_times]
        status_202 = [timeline[t]["202"] for t in sorted_times]
        status_429 = [timeline[t]["429"] for t in sorted_times]
        status_500 = [timeline[t]["500"] for t in sorted_times]

        plt.figure(figsize=(12, 6))
        plt.plot(times, status_202, label="202 Accepted (Processed/Debounced)", color="green")
        plt.plot(times, status_429, label="429 Too Many Requests (Rate Limited)", color="orange")
        if any(v > 0 for v in status_500):
            plt.plot(times, status_500, label="500 Internal Error", color="red")
            
        plt.title("API Throughput & Status Codes Over Time")
        plt.xlabel("Time")
        plt.ylabel("Requests per Second")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        output_file = "load_test_results.png"
        plt.savefig(output_file)
        print(f"Visualization saved to {output_file}")
        
    except ImportError:
        print("matplotlib not installed. Here is a text summary instead:")
        print("Time                 | 202s | 429s | 500s")
        print("-" * 45)
        for t in sorted_times:
            print(f"{t} | {timeline[t]['202']:4d} | {timeline[t]['429']:4d} | {timeline[t]['500']:4d}")

if __name__ == "__main__":
    main()
