# analyzer.py

import argparse
import csv
import json
from collections import defaultdict


def load_known_contracts(filepath):
    with open(filepath, "r") as file:
        return json.load(file)


def analyze_wallet(wallet_address, csv_path, known_contracts):
    wallet_address = wallet_address.lower()
    eth_in = 0.0
    eth_out = 0.0
    flagged = []

    with open(csv_path, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            tx_hash = row["Transaction Hash"]
            from_addr = row["From"].lower()
            to_addr = row["To"].lower()
            value = row["Amount"].split(" ")[0]
            label = None

            try:
                eth_val = float(value)
            except ValueError:
                eth_val = 0.0

            if from_addr == wallet_address:
                eth_out += eth_val
            elif to_addr == wallet_address:
                eth_in += eth_val

            # Scam detection
            for category, contracts in known_contracts.items():
                for addr, desc in contracts.items():
                    if from_addr == addr or to_addr == addr:
                        label = desc
                        flagged.append({
                            "tx_hash": tx_hash,
                            "timestamp": row["DateTime (UTC)"],
                            "from": from_addr,
                            "to": to_addr,
                            "desc": desc
                        })

    return eth_in, eth_out, flagged


def main():
    parser = argparse.ArgumentParser(description="Analyze ETH wallet transactions from CSV.")
    parser.add_argument("-w", "--wallet", required=True, help="Wallet address to analyze")
    parser.add_argument("-c", "--csv", required=True, help="Path to wallet CSV file")
    parser.add_argument("-k", "--known", required=True, help="Path to known_contracts.json")
    args = parser.parse_args()

    print("[+] Loading known contracts from {}...".format(args.known))
    known_contracts = load_known_contracts(args.known)

    print("[+] Loading wallet transactions from {}...".format(args.csv))
    eth_in, eth_out, flagged = analyze_wallet(args.wallet, args.csv, known_contracts)

    print("\n=== Summary ===")
    print("[+] ETH In: {:.6f}".format(eth_in))
    print("[+] ETH Out: {:.6f}".format(eth_out))
    print("[+] Net: {:.6f}".format(eth_in - eth_out))

    if flagged:
        print("\n=== Flagged Transactions ===")
        for tx in flagged:
            print("[!] Interaction with {} in TX {} on {}".format(tx["desc"], tx["tx_hash"], tx["timestamp"]))
    else:
        print("\n[+] No flagged transactions found.")


if __name__ == "__main__":
    main()
