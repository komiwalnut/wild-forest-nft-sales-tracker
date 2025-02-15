import os
from fastapi import FastAPI
from datetime import datetime, timezone
import re

app = FastAPI()


def get_timestamps_from_files():
    timestamps = []
    directory = "./lords_buyers"

    pattern = r'lords_buyers_(\d+)\.csv'

    try:
        for filename in os.listdir(directory):
            match = re.match(pattern, filename)
            if match:
                timestamp = int(match.group(1))
                start_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                end_time = datetime.fromtimestamp(timestamp + 7 * 24 * 60 * 60, tz=timezone.utc)

                timestamps.append({
                    "timestamp": timestamp,
                    "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S UTC")
                })

        timestamps.sort(key=lambda x: x["timestamp"], reverse=True)
        return timestamps

    except Exception as e:
        print(f"Error reading timestamps: {e}")
        return []


@app.get("/timestamps")
async def get_timestamps():
    timestamps = get_timestamps_from_files()
    if timestamps:
        return {"timestamps": timestamps}
    return {"error": "No timestamps found"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("timestamps:app", host="0.0.0.0", port=8008, reload=False)
