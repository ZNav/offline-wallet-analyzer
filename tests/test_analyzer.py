"""Unit tests for analyzer.py."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analyzer import analyze_wallet, load_known_contracts


CSV_HEADER = (
    "Transaction Hash,Status,Method,Blockno,DateTime (UTC),"
    "From,From_Nametag,To,To_Nametag,Amount,Value (USD),Txn Fee"
)


def _write_csv(path: Path, rows: list[tuple[str, ...]]) -> Path:
    """Write a CSV with the standard Etherscan header and the given rows."""
    quoted_rows = [",".join(f'"{cell}"' for cell in row) for row in rows]
    path.write_text("\n".join([CSV_HEADER, *quoted_rows]))
    return path


@pytest.fixture
def known_contracts() -> dict:
    return {
        "mixers": {"0xmixer1": "Tornado Cash"},
        "scams": {"0xscam1": "Bad Token"},
    }


@pytest.fixture
def known_contracts_path(tmp_path: Path, known_contracts: dict) -> Path:
    p = tmp_path / "known.json"
    p.write_text(json.dumps(known_contracts))
    return p


# ── load_known_contracts ────────────────────────────────────────────────────

def test_load_known_contracts(known_contracts_path: Path, known_contracts: dict):
    assert load_known_contracts(known_contracts_path) == known_contracts


def test_load_known_contracts_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_known_contracts(tmp_path / "nope.json")


# ── analyze_wallet: ETH in/out sums ─────────────────────────────────────────

def test_sums_received_and_sent(tmp_path: Path, known_contracts: dict):
    csv_path = _write_csv(tmp_path / "w.csv", [
        ("0xtx1", "Success", "Transfer", "1", "2026-01-01",
         "0xother", "", "0xme", "", "1.5 ETH", "$0", "0"),
        ("0xtx2", "Success", "Transfer", "2", "2026-01-02",
         "0xme", "", "0xother", "", "0.25 ETH", "$0", "0"),
    ])

    eth_in, eth_out, flagged = analyze_wallet("0xme", csv_path, known_contracts)

    assert eth_in == pytest.approx(1.5)
    assert eth_out == pytest.approx(0.25)
    assert flagged == []


def test_zero_eth_safe_transfer(tmp_path: Path, known_contracts: dict):
    """ENS / approve / safe-transfer rows show '0 ETH' — sums shouldn't move."""
    csv_path = _write_csv(tmp_path / "w.csv", [
        ("0xtx1", "Success", "Safe Transfer From", "1", "2026-01-01",
         "0xme", "", "0xother", "", "0 ETH", "$0", "0"),
    ])

    eth_in, eth_out, _ = analyze_wallet("0xme", csv_path, known_contracts)

    assert eth_in == 0.0
    assert eth_out == 0.0


def test_non_numeric_amount_treated_as_zero(tmp_path: Path, known_contracts: dict):
    """Defensive: malformed Amount field shouldn't crash, just count as 0."""
    csv_path = _write_csv(tmp_path / "w.csv", [
        ("0xtx1", "Success", "Transfer", "1", "2026-01-01",
         "0xme", "", "0xother", "", "garbage", "$0", "0"),
    ])

    eth_in, eth_out, _ = analyze_wallet("0xme", csv_path, known_contracts)

    assert eth_in == 0.0
    assert eth_out == 0.0


# ── analyze_wallet: flagging ────────────────────────────────────────────────

def test_flags_known_mixer_recipient(tmp_path: Path, known_contracts: dict):
    csv_path = _write_csv(tmp_path / "w.csv", [
        ("0xtx1", "Success", "Transfer", "1", "2026-01-01",
         "0xme", "", "0xmixer1", "", "0.5 ETH", "$0", "0"),
    ])

    _, _, flagged = analyze_wallet("0xme", csv_path, known_contracts)

    assert len(flagged) == 1
    assert flagged[0]["desc"] == "Tornado Cash"
    assert flagged[0]["tx_hash"] == "0xtx1"
    assert flagged[0]["to"] == "0xmixer1"


def test_flags_known_scam_sender(tmp_path: Path, known_contracts: dict):
    csv_path = _write_csv(tmp_path / "w.csv", [
        ("0xtx1", "Success", "Transfer", "1", "2026-01-01",
         "0xscam1", "", "0xme", "", "100 ETH", "$0", "0"),
    ])

    _, _, flagged = analyze_wallet("0xme", csv_path, known_contracts)

    assert len(flagged) == 1
    assert flagged[0]["desc"] == "Bad Token"


def test_clean_wallet_no_flags(tmp_path: Path, known_contracts: dict):
    csv_path = _write_csv(tmp_path / "w.csv", [
        ("0xtx1", "Success", "Transfer", "1", "2026-01-01",
         "0xme", "", "0xfriend", "", "1 ETH", "$0", "0"),
        ("0xtx2", "Success", "Transfer", "2", "2026-01-02",
         "0xfriend", "", "0xme", "", "0.5 ETH", "$0", "0"),
    ])

    _, _, flagged = analyze_wallet("0xme", csv_path, known_contracts)

    assert flagged == []


def test_address_matching_is_case_insensitive(
    tmp_path: Path, known_contracts: dict
):
    """Etherscan exports preserve checksummed casing — analyzer must lower."""
    csv_path = _write_csv(tmp_path / "w.csv", [
        ("0xtx1", "Success", "Transfer", "1", "2026-01-01",
         "0xMe", "", "0xMIXER1", "", "1 ETH", "$0", "0"),
    ])

    eth_in, eth_out, flagged = analyze_wallet("0xMe", csv_path, known_contracts)

    assert eth_out == pytest.approx(1.0)  # 0xMe is the sender
    assert eth_in == 0.0
    assert len(flagged) == 1
    assert flagged[0]["desc"] == "Tornado Cash"


def test_flags_each_interaction_separately(tmp_path: Path, known_contracts: dict):
    """Multiple interactions with the same flagged address all get logged."""
    csv_path = _write_csv(tmp_path / "w.csv", [
        ("0xtx1", "Success", "Transfer", "1", "2026-01-01",
         "0xme", "", "0xmixer1", "", "0.1 ETH", "$0", "0"),
        ("0xtx2", "Success", "Transfer", "2", "2026-01-02",
         "0xmixer1", "", "0xme", "", "0.1 ETH", "$0", "0"),
        ("0xtx3", "Success", "Transfer", "3", "2026-01-03",
         "0xme", "", "0xother", "", "0.1 ETH", "$0", "0"),
    ])

    _, _, flagged = analyze_wallet("0xme", csv_path, known_contracts)

    assert len(flagged) == 2
    assert {f["tx_hash"] for f in flagged} == {"0xtx1", "0xtx2"}


def test_empty_known_contracts_never_flags(tmp_path: Path):
    csv_path = _write_csv(tmp_path / "w.csv", [
        ("0xtx1", "Success", "Transfer", "1", "2026-01-01",
         "0xme", "", "0xanyone", "", "1 ETH", "$0", "0"),
    ])

    _, _, flagged = analyze_wallet("0xme", csv_path, {})

    assert flagged == []


def test_real_fixtures_smoke():
    """The repo ships a real wallet.csv + known_contracts.json — make sure
    the tool runs against them without crashing."""
    repo_root = Path(__file__).resolve().parents[1]
    eth_in, eth_out, flagged = analyze_wallet(
        "0x8211310a6d22b2098193a68a006fa6b0784df9e3",
        repo_root / "wallet.csv",
        load_known_contracts(repo_root / "known_contracts.json"),
    )
    assert eth_in >= 0
    assert eth_out >= 0
    assert isinstance(flagged, list)
