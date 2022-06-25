## About
Snapshot of Curve LP holders.

### Structure
For each pool pre-attack and post-attack snapshot of LP tokens and corresponding share of UST tokens is generated.
All token shares are combined in `combined.csv` and then merged through all pools into `merged.csv`.

### Run
Set [config](config.json):
```json
{
  "network name": {
    "endpoint": "https://endpoint.for.web3",
    "name of pool": {
      "network": "RPC endpoint for web3 queries",
      "start_block": 0,
      "snapshot_blocks": [
        [
          123,
          "name of snapshot"
        ]
      ],
      "token": "0xAddressOfTokenToSnapshot",
      "lp_token": "0xAddressOfLPToken",
      "gauge": "<Address of gauge or empty if does not exist>"
    }
  }
}
```
`start_block` can be set to the pool creation block to minimize made queries.  
`snapshot_blocks` if not set will be set at execution time, e.g. find block with specific timestamp(see [SNAPSHOT_BLOCKS](config.py)).  
Set network and name in [config.py](config.py), all `<-- CHANGE` if necessary and run
```shell
python3 snapshot.py
```
