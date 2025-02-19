import asyncio
import aiohttp
import json
import os
import csv
from fastapi import FastAPI, Response
import uvicorn
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

TOKEN_MAPPING = {
    "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5": ("WETH", 1e18),
    "0x97a9107c1793bc407d6f527b77e7fff4d812bece": ("AXS", 1e18),
    "0x0b7007c13325c48911f73a2dad5fa5dcbf808adc": ("USDC", 1e6),
    "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4": ("WRON", 1e18)
}

API_URL = "https://api-gateway.skymavis.com/graphql/mavis-marketplace"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": os.getenv("SM_API_KEY_2")
}

GRAPHQL_QUERY = '''
query SoldPacks($tokenAddress: String = "0x0328b534d094b097020b4538230f998027a54db0") {
  recentlySolds(size: 40, tokenAddress: $tokenAddress, from: %d) {
    results {
      maker
      matcher
      paymentToken
      realPrice
      timestamp
      txHash
      orderKind
      quantity
      orderId
      assets {
        id
        token {
          ... on Erc721 {
            numActiveOffers
            name
            cdnImage
            attributes
          }
        }
      }
    }
  }
}
'''

PAGE_SIZE = 40


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


def get_current_filename():
    start_ts, _ = get_week_timestamps()
    os.makedirs("./packs_buyers", exist_ok=True)
    return f"./packs_buyers/packs_buyers_{start_ts}.csv"


def get_download_filename():
    return get_current_filename()


def load_buyers():
    filename = get_current_filename()
    if os.path.exists(filename):
        try:
            records = []
            with open(filename, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row['timestamp'] = int(row['timestamp'])
                    records.append(row)
            return records
        except Exception as e:
            print(f"Error loading buyers file: {e}")
    return []


def save_buyers(buyer_records):
    try:
        buyer_records.sort(key=lambda x: x["timestamp"], reverse=True)
        filename = get_current_filename()

        with open(filename, "w", newline='') as f:
            fieldnames = ['buyer', 'packs_id & quantity', 'price', 'txHash', 'timestamp']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(buyer_records)
    except Exception as e:
        print("Error saving buyers file:", e)


def format_price(amount, token_symbol):
    if amount.is_integer():
        price_str = str(int(amount))
    else:
        price_str = f"{amount:.10f}".rstrip('0').rstrip('.')

    return f"{price_str} {token_symbol}"


async def fetch_transactions(offset: int, session: aiohttp.ClientSession):
    query_str = GRAPHQL_QUERY % offset
    payload = {"query": query_str}
    try:
        async with session.post(API_URL, headers=HEADERS, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                results = data.get("data", {}).get("recentlySolds", {}).get("results", [])
                return results
            else:
                text = await response.text()
                print("Error fetching data:", response.status, text)
    except Exception as e:
        print("Exception during fetch:", e)
    return []


async def historical_backfill(buyer_records: list, recorded_purchases: set, session: aiohttp.ClientSession):
    print("Starting historical backfill...")
    offset = 0
    start_ts, end_ts = get_week_timestamps()

    while True:
        print(f"Fetching transactions (offset {offset})...")
        transactions = await fetch_transactions(offset, session)
        if not transactions:
            print("No more transactions found.")
            break

        for tx in transactions:
            ts = tx.get("timestamp", 0)
            order_id = tx.get("orderId")

            if not order_id:
                continue

            if ts < start_ts:
                print("Encountered a transaction older than the start timestamp. Backfill complete.")
                return

            if ts > end_ts:
                continue

            tokenSymbol = TOKEN_MAPPING.get(tx.get("paymentToken"))
            amount = int(tx.get("realPrice")) / tokenSymbol[1]

            order_kind = tx.get("orderKind")
            if order_kind == 2 or order_kind == 0:
                buyer = tx.get("maker")
            else:
                buyer = tx.get("matcher")

            assets = tx.get("assets", [])
            for asset in assets:
                asset_id = asset.get("id")
                if not asset_id:
                    continue

                quantity = int(tx.get("quantity", 1))
                purchase_id = f"{order_id}_{asset_id}_{quantity}"

                if purchase_id in recorded_purchases:
                    continue

                record = {
                    "buyer": buyer,
                    "packs_id & quantity": f"{asset_id} {quantity}x",
                    "price": format_price(amount, tokenSymbol[0]),
                    "txHash": tx.get("txHash"),
                    "timestamp": ts
                }
                print(f"Recording historical record: {record}")
                buyer_records.append(record)
                recorded_purchases.add(purchase_id)

        offset += PAGE_SIZE
        await asyncio.sleep(1)


async def poll_new_transactions(buyer_records: list, recorded_purchases: set, last_timestamp: int, session: aiohttp.ClientSession):
    print("Polling for new transactions...")
    offset = 0
    new_last_timestamp = last_timestamp
    new_records = []
    start_ts, end_ts = get_week_timestamps()

    while True:
        transactions = await fetch_transactions(offset, session)
        if not transactions:
            break

        for tx in reversed(transactions):
            ts = tx.get("timestamp", 0)
            order_id = tx.get("orderId")

            if not order_id:
                continue

            if ts <= last_timestamp:
                continue

            if ts < start_ts or ts > end_ts:
                continue

            tokenSymbol = TOKEN_MAPPING.get(tx.get("paymentToken"))
            amount = int(tx.get("realPrice")) / tokenSymbol[1]

            order_kind = tx.get("orderKind")
            if order_kind == 2 or order_kind == 0:
                buyer = tx.get("maker")
            else:
                buyer = tx.get("matcher")

            assets = tx.get("assets", [])
            for asset in assets:
                asset_id = asset.get("id")
                if not asset_id:
                    continue

                quantity = int(tx.get("quantity", 1))
                purchase_id = f"{order_id}_{asset_id}_{quantity}"

                if purchase_id in recorded_purchases:
                    continue

                record = {
                    "buyer": buyer,
                    "packs_id & quantity": f"{asset_id} {quantity}x",
                    "price": format_price(amount, tokenSymbol[0]),
                    "txHash": tx.get("txHash"),
                    "timestamp": ts
                }
                print(f"Found new record: {record}")
                new_records.append(record)
                recorded_purchases.add(purchase_id)
                new_last_timestamp = max(new_last_timestamp, ts)

        if len(transactions) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    if new_records:
        buyer_records.extend(new_records)
        save_buyers(buyer_records)
    else:
        print("No new transactions found.")

    return new_last_timestamp


async def background_task():
    while True:
        current_week_start, current_week_end = get_week_timestamps()
        current_filename = get_current_filename()

        if not os.path.exists(current_filename):
            with open(current_filename, 'w') as f:
                writer = csv.DictWriter(f, fieldnames=['buyer', 'packs_id & quantity', 'price', 'txHash', 'timestamp'])
                writer.writeheader()
            print(f"Created new weekly file: {current_filename}")

        buyer_records = load_buyers()
        recorded_purchases = set()
        for record in buyer_records:
            if "txHash" in record and "packs_id & quantity" in record:
                parts = record["packs_id & quantity"].split()
                asset_id = parts[0]
                quantity = parts[1].rstrip('x')
                recorded_purchases.add(f"{record['txHash']}_{asset_id}_{quantity}")

        async with aiohttp.ClientSession() as session:
            await historical_backfill(buyer_records, recorded_purchases, session)
            save_buyers(buyer_records)

            last_timestamp = current_week_start if not buyer_records else max(r["timestamp"] for r in buyer_records)

            while True:
                try:
                    current_time = datetime.now(timezone.utc).timestamp()
                    if current_time > current_week_end:
                        print("End timestamp reached, starting new week...")
                        await asyncio.sleep(60)
                        break

                    last_timestamp = await poll_new_transactions(
                        buyer_records, recorded_purchases, last_timestamp, session
                    )

                except Exception as e:
                    print(f"Error in polling loop: {str(e)}")

                await asyncio.sleep(60)

        buyer_records.clear()
        recorded_purchases.clear()
        print("Preparing for new weekly cycle...")


app = FastAPI()


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


@app.get("/packs_buyers/{timestamp}")
async def get_buyers_with_timestamp(timestamp: int):
    filename = f"./packs_buyers/packs_buyers_{timestamp}.csv"
    return _serve_csv(filename)


@app.get("/packs_buyers/")
async def get_current_buyers():
    current_ts, _ = get_week_timestamps()
    current_filename = f"./packs_buyers/packs_buyers_{current_ts}.csv"

    if os.path.exists(current_filename):
        return _serve_csv(current_filename)
    else:
        latest_file = find_latest_csv("./packs_buyers", "packs_buyers_")
        if latest_file:
            return _serve_csv(latest_file)
        else:
            raise HTTPException(status_code=404, detail="No buyers data found")


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


if __name__ == "__main__":
    uvicorn.run("packs:app", host="0.0.0.0", port=8002, reload=False)
