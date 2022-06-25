import json

from utils import get_block, load_abis

NETWORK = "avalanche"  # <-- CHANGE
NAME = "usdc-ust"  # <-- CHANGE
DOUBLE_CHECK = True  # Double check of balances

with open("config.json", "r") as f:
    full_config = json.load(f)
config = full_config[NETWORK][NAME]
ENDPOINT = full_config[NETWORK]["endpoint"]

START_BLOCK = config["start_block"]
# pre-attack: May-07-2022 02:59:39 PM +UTC = 1651935579
PRE_ATTACK_TS = 1651935579  # <-- CHANGE
# post-attack: May-26-2022 04:38:08 PM +UTC = 1653583088
POST_ATTACK_TS = 1653583088  # <-- CHANGE

SNAPSHOT_BLOCKS = config.get("snapshot_blocks")
if not SNAPSHOT_BLOCKS:
    pre_block = get_block(PRE_ATTACK_TS, ENDPOINT)
    post_block = get_block(POST_ATTACK_TS, ENDPOINT, left=pre_block)
    SNAPSHOT_BLOCKS = [
        [pre_block, "pre-attack"],
        [post_block, "post-attack"],
    ]
    print(f"Snapshot blocks used: {SNAPSHOT_BLOCKS}")

TOKEN = config.get("token")
LP_TOKEN = config["lp_token"]
GAUGE = config.get("gauge")

ABIS = load_abis()

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def snapshot_dirname(name: str = None):
    return f"{NETWORK}/{name if name else NAME}"


def snapshot_filename(name: str, token: str = None):
    return f"{NETWORK}/{NAME}/{name}" + (f"-{token}" if token else "") + ".json"


def combined_filename(name: str = None):
    return f"{NETWORK}/{name if name else NAME}/combined.csv"


def merged_filename():
    return f"{NETWORK}/merged.csv"
