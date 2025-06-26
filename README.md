# offline-wallet-analyzer
Blockchain Forensics tool made to view transactions and allow you to monitor wallets against known addresses
# Wallet Analyzer

A lightweight Python tool for analyzing Ethereum wallet transaction histories from CSV exports. It calculates ETH flow and flags interactions with known malicious addresses or services like Tornado Cash.

---

## Features

* Summarizes ETH received, sent, and net balance
* Flags transactions involving known:

  * Scam wallets
  * Mixer services (e.g., Tornado Cash)
  * Suspicious tokens or contracts
* Minimal dependencies, runs offline

---

## Usage

```bash
python3 analyzer.py -w <wallet_address> -c <path_to_csv> -k <known_contracts.json>
```

* `-w`: Ethereum wallet address
* `-c`: CSV file exported from Etherscan
* `-k`: JSON file mapping known addresses to descriptions

Example:

```bash
python3 analyzer.py -w 0xabc...123 -c wallet.csv -k known_contracts.json
```

---

## known\_contracts.json Format

```json
{
  "tornado_cash": {
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b": "Tornado Cash"
  },
  "scam_wallets": {
    "0x6982508145454ce325ddbe47a25d4ec3d2311933": "PEPE Token",
    "0x28561b8a2360f463011c16b6cc0b0cbef8dbbcad": "Moodeng Token"
  }
}
```

---

## Output Example

```
=== Summary ===
[+] ETH In: 1.200000
[+] ETH Out: 3.400000
[+] Net: -2.200000

=== Flagged Transactions ===
[!] Interaction with PEPE Token in TX 0xabc... on 2025-06-06 08:13:47
```

---

## Contributing

Pull requests to expand contract support or improve CSV parsing are welcome.

---

## License

MIT
