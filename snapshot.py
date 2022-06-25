import asyncio
import csv
import os
from collections import defaultdict

from tqdm import tqdm
from web3 import Web3
from web3.eth import AsyncEth

from config import *
from utils import retrieve_address

TOPICS = [TRANSFER_TOPIC]
TOKENS = (LP_TOKEN, GAUGE) if GAUGE else (LP_TOKEN,)

web3 = Web3(
    provider=Web3.AsyncHTTPProvider(ENDPOINT, {"verify_ssl": False}),
    modules={"eth": (AsyncEth,)},
    middlewares=[],
)
lp = web3.eth.contract(address=LP_TOKEN, abi=ABIS["Plain2Optimized"])
gauge = web3.eth.contract(address=GAUGE, abi=ABIS["LiquidityGauge"]) if GAUGE else None
token = web3.eth.contract(address=TOKEN, abi=ABIS["ERC20"]) if TOKEN else None


def dump(balances: dict, filename: str, decimals: int = 0):
    cleared_balances = {}
    for key, value in balances.items():
        if value > 0:
            cleared_balances[key] = value / 10 ** decimals
    os.makedirs(snapshot_dirname(), exist_ok=True)
    with open(filename, "w+") as f:
        json.dump(cleared_balances, f, sort_keys=True, indent=2)


async def fetch_logs(start, end):
    batch_size = 2048 if NETWORK in ["avalanche"] else 0
    rate = 30  # Max number of requests per second
    entries = []

    if batch_size:
        for i in tqdm(range(start, end, batch_size * rate), desc="Log batches"):
            queries = []
            for j in range(i, min(i + batch_size * rate, end), batch_size):
                queries.append(
                    web3.eth.get_logs(
                        {
                            "fromBlock": j,
                            "toBlock": min(j + batch_size - 1, end),
                            "address": TOKENS,
                            "topics": TOPICS,
                        }
                    )
                )
            entries += await asyncio.gather(*queries, asyncio.sleep(1))
        # flatten
        entries = [log for logs in entries for log in ([] if logs is None else logs)]
    else:
        entries = await web3.eth.get_logs(
            {
                "fromBlock": start,
                "toBlock": end,
                "address": TOKENS,
                "topics": TOPICS,
            }
        )
    return entries


def fetch_balances(balances, entries):
    """Calc balances according to Transfer events"""
    for log in tqdm(entries, desc="Logs"):
        _from = retrieve_address(log["topics"][1])
        to = retrieve_address(log["topics"][2])
        value = int(log["data"].hex(), base=16)
        balances[_from] -= value
        balances[to] += value

    if ZERO_ADDRESS in balances:
        del balances[ZERO_ADDRESS]
    if GAUGE and GAUGE in balances:
        del balances[GAUGE]

    return balances


async def double_check(balances, block_id):
    # asyncio.gather can be used
    for holder, value in tqdm(balances.items(), leave=False, desc="Double check"):
        balance = await lp.functions.balanceOf(holder).call(block_identifier=block_id)
        if gauge:
            balance += await gauge.functions.balanceOf(holder).call(
                block_identifier=block_id
            )
        assert (
            value == balance
        ), f"Incorrect balance for {holder}: {value} instead of {balance}"


async def snapshot():
    if TOKEN:
        token_decimals = await token.functions.decimals().call()
        token_symbol = await token.functions.symbol().call()
        for i in range(4):
            coin = await lp.functions.coins(i).call()
            if coin == TOKEN:
                break
        else:
            raise ValueError("Token is not in the pool")
    if gauge:
        assert (
            LP_TOKEN == await gauge.functions.lp_token().call()
        ), "Invalid gauge address"

    balances = defaultdict(int)
    start = START_BLOCK
    for end, name in tqdm(list(sorted(SNAPSHOT_BLOCKS)), desc="Snapshots"):
        entries = await fetch_logs(start, end)
        balances = fetch_balances(balances, entries)

        # Extra checks
        if DOUBLE_CHECK:  # double check
            await double_check(balances, end)
        for holder, value in tqdm(
            balances.items(), leave=False, desc="Negative balance check"
        ):
            assert value >= 0, f"Negative balance for {holder}: {value}"
        total_supply = await lp.functions.totalSupply().call(block_identifier=end)
        assert sum(balances.values()) == total_supply

        dump(balances, snapshot_filename(name), decimals=18)

        if TOKEN:
            token_amount = await token.functions.balanceOf(LP_TOKEN).call(
                block_identifier=end
            )
            token_balances = {}
            if total_supply:  # Might be zero at snapshot
                for holder, value in tqdm(
                    balances.items(), leave=False, desc="Calc token balances"
                ):
                    token_balances[holder] = value * token_amount / total_supply
            dump(
                token_balances,
                snapshot_filename(name, token_symbol),
                decimals=token_decimals,
            )
        start = end + 1


async def combine():
    """
    Combine pre-attack and post-attack snapshots for token share of the pool.
    """
    token_symbol = await token.functions.symbol().call()

    combined_balances = []
    for end, name in tqdm(list(sorted(SNAPSHOT_BLOCKS)), desc="Snapshots"):
        with open(snapshot_filename(name, token_symbol), "r") as f:
            balances = json.load(f)
        for holder, amount in tqdm(
            balances.items(), leave=False, desc="Merge balances"
        ):
            combined_balances.append(
                {
                    "height": end,
                    "user_address": holder,
                    "token_address": TOKEN,
                    "amount": amount,
                }
            )

    with open(combined_filename(), "w+") as csvfile:
        writer = csv.DictWriter(
            csvfile, fieldnames=["height", "user_address", "token_address", "amount"]
        )
        writer.writeheader()
        writer.writerows(combined_balances)


def merge_combined():
    """
    Merge combined snapshots of all pools in one network.
    """
    balances = defaultdict(int)
    for name in os.listdir(NETWORK):
        if not os.path.isdir(snapshot_dirname(name)):
            continue
        with open(combined_filename(name), "r") as f:
            rows = csv.reader(f)
            for row in list(rows)[1:]:
                balances[(row[0], row[1], row[2])] += float(row[3])

    merged_balances = []
    for key, amount in balances.items():
        merged_balances.append(
            {
                "height": key[0],
                "user_address": key[1],
                "token_address": key[2],
                "amount": amount,
            }
        )
    merged_balances.sort(key=lambda b: (b["height"], b["token_address"], -b["amount"]))

    with open(merged_filename(), "w+") as csvfile:
        writer = csv.DictWriter(
            csvfile, fieldnames=["height", "user_address", "token_address", "amount"]
        )
        writer.writeheader()
        writer.writerows(merged_balances)


async def main():
    await snapshot()
    if TOKEN:
        await combine()


if __name__ == "__main__":
    asyncio.run(main())
    merge_combined()
