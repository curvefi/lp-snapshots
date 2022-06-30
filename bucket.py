import csv
import json
from collections import defaultdict

from config import merged_filename

networks = ["arbitrum", "avalanche", "fantom", "optimism", "polygon"]
BUCKETS = [1_000, 1_500, 2_000, 2_500, 3_000, 3_500, 4_000, 4_500, 5_000, 10 ** 18]


def bucket():
    users = defaultdict(dict)
    for network in networks:
        with open(merged_filename(network), 'r') as f:
            rows = list(csv.reader(f))
            for row in rows[1:]:
                height, user_address, token_address, amount = int(row[0]), row[1], row[2], float(row[3])
                users[user_address][network] = amount

    buckets = [{} for _ in BUCKETS]
    for user, amounts in sorted(users.items()):
        overall_balance = sum(amounts.values())
        for i, b in enumerate(BUCKETS):
            if overall_balance <= b:
                buckets[i][user] = overall_balance
                break

    # Sort by overall balance
    for i in range(len(BUCKETS)):
        buckets[i] = dict(sorted(buckets[i].items(), key=lambda item: (item[1], item[0])))

    with open("buckets.json", 'w+') as f:
        json.dump(buckets, f, indent=2)


if __name__ == '__main__':
    bucket()
