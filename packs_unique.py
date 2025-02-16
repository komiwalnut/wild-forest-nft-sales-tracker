import os
import asyncio
from collections import defaultdict
from fastapi import FastAPI, Response
import uvicorn
from datetime import datetime, timedelta, timezone
import csv

app = FastAPI()


def get_week_timestamps():
    initial_start = datetime(
        2025, 2, 10,
        13, 0, 0,
        tzinfo=timezone.utc
    )

    now = datetime.now(timezone.utc)

    if now < initial_start:
        start_time = initial_start
    else:
        delta = now - initial_start
        intervals = int(delta.total_seconds() // (7 * 24 * 60 * 60))
        start_time = initial_start + timedelta(days=7 * intervals)

    end_time = start_time + timedelta(days=7)

    return int(start_time.timestamp()), int(end_time.timestamp())


def get_current_buyers_filename():
    start_ts, _ = get_week_timestamps()
    return f"./packs_buyers/packs_buyers_{start_ts}.csv"


def get_current_unique_filename():
    start_ts, _ = get_week_timestamps()
    os.makedirs("./packs_unique", exist_ok=True)
    return f"./packs_unique/packs_unique_{start_ts}.csv"


def load_buyers():
    filename = get_current_buyers_filename()
    if os.path.exists(filename):
        try:
            records = []
            with open(filename, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if isinstance(row.get('timestamp'), str):
                        row['timestamp'] = int(row['timestamp'])
                    records.append(row)
            return records
        except Exception as e:
            print(f"Error loading buyers file: {e}")
    return []


def update_unique_buyers():
    try:
        buyer_records = load_buyers()
        if not buyer_records:
            return

        unique_buyers = defaultdict(lambda: defaultdict(float))
        for record in buyer_records:
            buyer = record["buyer"]
            amount_str, token = record["price"].split()
            unique_buyers[buyer][token] += float(amount_str)

        csv_data = []
        for buyer, tokens in unique_buyers.items():
            row = {"Address": buyer}
            for token, amount in tokens.items():
                row[token] = f"{amount:.2f}".rstrip('0').rstrip('.') if not amount.is_integer() else str(int(amount))
            csv_data.append(row)

        csv_data.sort(key=lambda x: x["Address"].lower())
        filename = get_current_unique_filename()

        with open(filename, 'w', newline='') as f:
            fieldnames = ["Address"] + sorted(list({token for row in csv_data for token in row.keys() if token != "Address"}))
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)

    except Exception as e:
        print(f"Error updating packs unique buyers: {e}")


def find_latest_csv(directory: str, prefix: str) -> str:
    try:
        files = os.listdir(directory)
        matching_files = [f for f in files if f.startswith(prefix) and f.endswith(".csv")]
        if not matching_files:
            return None
        latest_file = max(
            matching_files,
            key=lambda x: int(x.split("_")[-1].replace(".csv", ""))
        )
        return os.path.join(directory, latest_file)
    except Exception as e:
        print(f"Error finding latest CSV: {e}")
        return None


@app.get("/packs_unique/{timestamp}")
async def get_unique_with_timestamp(timestamp: int):
    filename = f"./packs_unique/packs_unique_{timestamp}.csv"
    return _serve_csv(filename)


@app.get("/packs_unique/")
async def get_current_unique():
    current_ts, _ = get_week_timestamps()
    current_filename = f"./packs_unique/packs_unique_{current_ts}.csv"

    if os.path.exists(current_filename):
        return _serve_csv(current_filename)
    else:
        latest_file = find_latest_csv("./packs_unique", "packs_unique_")
        if latest_file:
            return _serve_csv(latest_file)
        else:
            raise HTTPException(status_code=404, detail="No unique data found")


def _serve_csv(filename: str) -> Response:
    try:
        with open(filename, 'rb') as f:
            content = f.read()
            return Response(
                content=content,
                media_type="text/csv",
                headers={'Content-Disposition': f'attachment; filename={os.path.basename(filename)}'}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_task())


async def background_task():
    while True:
        os.makedirs("./packs_unique", exist_ok=True)
        update_unique_buyers()
        await asyncio.sleep(60)


if __name__ == "__main__":
    uvicorn.run("packs_unique:app", host="0.0.0.0", port=8003, reload=False)
