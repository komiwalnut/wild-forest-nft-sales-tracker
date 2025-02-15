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
    "X-API-Key": os.getenv("SM_API_KEY")
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
    end_timestamp = start_timestamp + 7 * 24 * 60 * 60
    return start_timestamp, end_timestamp


def get_current_filename():
    start_ts, _ = get_week_timestamps()
    return f"packs_buyers_{start_ts}.csv"


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
            txhash = tx.get("txHash")

            if not txhash:
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
                purchase_id = f"{txhash}_{asset_id}"

                if purchase_id in recorded_purchases:
                    continue

                record = {
                    "buyer": buyer,
                    "packs_id & quantity": f"{asset_id} {quantity}x",
                    "price": format_price(amount, tokenSymbol[0]),
                    "txHash": txhash,
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
            txhash = tx.get("txHash")

            if ts <= last_timestamp:
                continue

            if not txhash:
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
                purchase_id = f"{txhash}_{asset_id}"

                if purchase_id in recorded_purchases:
                    continue

                record = {
                    "buyer": buyer,
                    "packs_id & quantity": f"{asset_id} {quantity}x",
                    "price": format_price(amount, tokenSymbol[0]),
                    "txHash": txhash,
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
        current_filename = get_current_filename()
        if not os.path.exists(current_filename):
            with open(current_filename, 'w') as f:
                writer = csv.DictWriter(f, fieldnames=['buyer', 'packs_id & quantity', 'price', 'txHash', 'timestamp'])
                writer.writeheader()

        buyer_records = load_buyers()
        recorded_purchases = {f"{record['txHash']}_{record['packs_id & quantity'].split()[0]}"
                              for record in buyer_records
                              if "txHash" in record and "packs_id & quantity" in record}

        async with aiohttp.ClientSession() as session:
            start_ts, _ = get_week_timestamps()

            await historical_backfill(buyer_records, recorded_purchases, session)
            save_buyers(buyer_records)

            if buyer_records:
                last_timestamp = max(record["timestamp"] for record in buyer_records)
            else:
                last_timestamp = start_ts

            while True:
                try:
                    current_week_start, current_week_end = get_week_timestamps()
                    if datetime.now(timezone.utc).timestamp() > current_week_end:
                        break  # Exit loop to create new file for new week

                    last_timestamp = await poll_new_transactions(buyer_records, recorded_purchases, last_timestamp, session)
                except Exception as e:
                    print("Error during polling:", e)
                await asyncio.sleep(60)


app = FastAPI()


@app.get("/packs_buyers")
async def get_buyers():
    filename = get_current_filename()
    if os.path.exists(filename):
        try:
            with open(filename, 'rb') as f:
                content = f.read()
                return Response(
                    content=content,
                    media_type="text/csv",
                    headers={
                        'Content-Disposition': f'attachment; filename={os.path.basename(filename)}'
                    }
                )
        except Exception as e:
            return {"error": f"Error reading packs buyers file: {e}"}
    return {"error": f"{filename} not found"}


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_task())


if __name__ == "__main__":
    uvicorn.run("packs:app", host="0.0.0.0", port=8002, reload=False)
