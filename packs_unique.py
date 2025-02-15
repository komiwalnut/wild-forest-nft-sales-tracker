import os
import asyncio
from collections import defaultdict
from fastapi import FastAPI, Response
import uvicorn
from datetime import datetime, timedelta, timezone
import csv

app = FastAPI()


def get_week_timestamps():
    now = datetime.now(timezone.utc)
    start_of_week = now - timedelta(days=now.weekday())
    start_timestamp = int(datetime(
        start_of_week.year,
        start_of_week.month,
        start_of_week.day,
        13,
        0,
        0,
        tzinfo=timezone.utc
    ).timestamp())
    return start_timestamp, start_timestamp + 7 * 24 * 60 * 60


def get_current_buyers_filename():
    start_ts, _ = get_week_timestamps()
    return f"packs_buyers_{start_ts}.csv"


def get_current_unique_filename():
    start_ts, _ = get_week_timestamps()
    return f"packs_unique_{start_ts}.csv"


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


@app.get("/packs_unique")
async def get_unique_buyers():
    filename = get_current_unique_filename()
    if os.path.exists(filename):
        try:
            with open(filename, 'rb') as f:
                return Response(
                    content=f.read(),
                    media_type="text/csv",
                    headers={'Content-Disposition': f'attachment; filename={os.path.basename(filename)}'}
                )
        except Exception as e:
            return {"error": str(e)}
    return {"error": "File not found"}


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_task())


async def background_task():
    while True:
        update_unique_buyers()
        await asyncio.sleep(60)

if __name__ == "__main__":
    uvicorn.run("packs_unique:app", host="0.0.0.0", port=8003, reload=False)
