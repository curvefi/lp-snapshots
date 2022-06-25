import json
import os

from web3 import Web3
from web3.middleware import geth_poa_middleware


def get_block(ts: int, endpoint: str, left: int = 0):
    """Binary search the block with timestamp >= ts"""
    web3 = Web3(provider=Web3.HTTPProvider(endpoint))
    web3.middleware_onion.inject(
        geth_poa_middleware, layer=0
    )  # <-- CHANGE Comment if 'get_block' fails
    right = web3.eth.block_number
    while (right - left) > 1:
        mid = (left + right) // 2
        mid_ts = web3.eth.get_block(mid)["timestamp"]
        if mid_ts >= ts:
            right = mid
        else:
            left = mid

    assert web3.eth.get_block(right - 1)["timestamp"] < ts
    assert web3.eth.get_block(right)["timestamp"] >= ts
    return right


def retrieve_address(data):
    if isinstance(data, str):
        return Web3.toChecksumAddress("0x" + data[-40:])
    else:
        return retrieve_address(data.hex())


def load_abis():
    abis = {}
    for filename in os.listdir("abi"):
        if not filename.endswith(".json"):
            continue
        with open(f"abi/{filename}", "r") as f:
            abis[filename[:-5]] = json.load(f)
    return abis
