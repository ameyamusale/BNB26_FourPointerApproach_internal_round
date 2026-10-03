"""Real ModelLedgerRegistry blockchain adapter.

The adapter is deliberately optional: the API still runs without a node, but it
never reports blockchain evidence unless a real RPC query succeeds. When the
chain is configured, writes use the configured transaction private key and reads
query the deployed ModelLedgerRegistry contract.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import config

ABI = [
    {"inputs":[{"internalType":"string","name":"modelId","type":"string"},{"internalType":"string","name":"modelHash","type":"string"},{"internalType":"bytes32","name":"metadataHash","type":"bytes32"}],"name":"registerModel","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"string","name":"artifactId","type":"string"},{"internalType":"string","name":"exactHash","type":"string"},{"internalType":"string","name":"robustFingerprint","type":"string"},{"internalType":"string","name":"modelId","type":"string"}],"name":"registerArtifact","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"string","name":"eventId","type":"string"},{"internalType":"string","name":"parentArtifactId","type":"string"},{"internalType":"string","name":"childArtifactId","type":"string"},{"internalType":"string","name":"modelId","type":"string"},{"internalType":"string","name":"applicationId","type":"string"},{"internalType":"string","name":"action","type":"string"},{"internalType":"bytes32","name":"metadataHash","type":"bytes32"},{"internalType":"bytes32","name":"claimHash","type":"bytes32"}],"name":"addProvenanceEvent","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"string","name":"modelId","type":"string"}],"name":"revokeModel","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"string","name":"eventId","type":"string"}],"name":"revokeClaim","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"string","name":"modelId","type":"string"},{"internalType":"string","name":"expectedModelHash","type":"string"}],"name":"isModelRegistered","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"string","name":"artifactId","type":"string"},{"internalType":"string","name":"expectedExactHash","type":"string"}],"name":"isArtifactRegistered","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"string","name":"eventId","type":"string"},{"internalType":"bytes32","name":"expectedClaimHash","type":"bytes32"}],"name":"isProvenanceEventValid","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"string","name":"modelId","type":"string"}],"name":"isModelRevoked","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"string","name":"modelId","type":"string"}],"name":"getModel","outputs":[{"internalType":"string","name":"","type":"string"},{"internalType":"bytes32","name":"","type":"bytes32"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"string","name":"artifactId","type":"string"}],"name":"getArtifact","outputs":[{"internalType":"string","name":"","type":"string"},{"internalType":"string","name":"","type":"string"},{"internalType":"string","name":"","type":"string"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"string","name":"artifactId","type":"string"}],"name":"getArtifactEvents","outputs":[{"internalType":"string[]","name":"","type":"string[]"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"string","name":"eventId","type":"string"}],"name":"getProvenanceEvent","outputs":[{"internalType":"string","name":"","type":"string"},{"internalType":"string","name":"","type":"string"},{"internalType":"string","name":"","type":"string"},{"internalType":"string","name":"","type":"string"},{"internalType":"string","name":"","type":"string"},{"internalType":"string","name":"","type":"string"},{"internalType":"bytes32","name":"","type":"bytes32"},{"internalType":"bytes32","name":"","type":"bytes32"},{"internalType":"address","name":"","type":"address"},{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"bool","name":"","type":"bool"},{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"string","name":"eventId","type":"string"}],"name":"isClaimRevoked","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
]


def _load_web3():
    try:
        from web3 import Web3
    except ImportError:
        return None
    return Web3


def is_configured() -> bool:
    return bool(config.BLOCKCHAIN_RPC_URL and config.CONTRACT_ADDRESS)


def _client():
    Web3 = _load_web3()
    if Web3 is None or not is_configured():
        return None, None
    w3 = Web3(Web3.HTTPProvider(config.BLOCKCHAIN_RPC_URL, request_kwargs={"timeout": 5}))
    if not w3.is_connected():
        return None, None
    return w3, w3.eth.contract(address=Web3.to_checksum_address(config.CONTRACT_ADDRESS), abi=ABI)


def status() -> Dict[str, Any]:
    if not is_configured():
        return {"mode": "offline", "connected": False, "contract_address": None,
                "note": "Blockchain is not configured; no on-chain evidence is claimed."}
    if _load_web3() is None:
        return {"mode": "dependency-missing", "connected": False, "contract_address": config.CONTRACT_ADDRESS,
                "note": "Install requirements-chain.txt to enable the Python blockchain adapter."}
    try:
        w3, _ = _client()
        if w3 is None:
            return {"mode": "rpc-unreachable", "connected": False, "contract_address": config.CONTRACT_ADDRESS,
                    "note": "Configured blockchain RPC could not be reached."}
        return {"mode": "on-chain", "connected": True, "contract_address": config.CONTRACT_ADDRESS,
                "chain_id": w3.eth.chain_id, "block": w3.eth.block_number,
                "note": "ModelLedgerRegistry is reachable and can provide real on-chain evidence."}
    except Exception as exc:
        return {"mode": "error", "connected": False, "contract_address": config.CONTRACT_ADDRESS,
                "note": f"Blockchain connection error: {type(exc).__name__}"}


def _bytes32(w3, value: str) -> bytes:
    if isinstance(value, bytes):
        return value
    return bytes.fromhex(value[2:] if value.startswith("0x") else value) if len(value.replace("0x", "")) == 64 else w3.keccak(text=value)


def _send(function) -> Dict[str, Any]:
    if not config.BLOCKCHAIN_TX_PRIVATE_KEY:
        return {"success": False, "committed": False, "tx_hash": None,
                "reason": "Blockchain writes require MODELLEDGER_TX_PRIVATE_KEY."}
    w3, _ = _client()
    if w3 is None:
        return {"success": False, "committed": False, "tx_hash": None, "reason": status()["note"]}
    try:
        account = w3.eth.account.from_key(config.BLOCKCHAIN_TX_PRIVATE_KEY)
        nonce = w3.eth.get_transaction_count(account.address, "pending")
        gas = function.estimate_gas({"from": account.address})
        tx = function.build_transaction({
            "from": account.address,
            "nonce": nonce,
            "chainId": w3.eth.chain_id,
            "gas": gas + max(20000, gas // 5),
            "maxFeePerGas": w3.to_wei("2", "gwei"),
            "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
        })
        signed = account.sign_transaction(tx)
        raw_tx = getattr(signed, "raw_transaction", None)
        if raw_tx is None:
            raw_tx = getattr(signed, "rawTransaction", None)
        tx_hash = w3.eth.send_raw_transaction(raw_tx)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
        ok = receipt.status == 1
        tx_hex = tx_hash.hex()
        if tx_hex and not tx_hex.startswith("0x"):
            tx_hex = "0x" + tx_hex
        return {"success": ok, "committed": ok, "tx_hash": tx_hex if ok else None,
                "reason": None if ok else "Transaction reverted"}
    except Exception as exc:
        return {"success": False, "committed": False, "tx_hash": None,
                "reason": f"{type(exc).__name__}: {exc}"}


def register_model(model_id: str, model_hash: str, metadata_hash: str) -> Dict[str, Any]:
    w3, contract = _client()
    if w3 is None or contract is None:
        return {"success": False, "committed": False, "tx_hash": None, "reason": status()["note"]}
    return _send(contract.functions.registerModel(model_id, model_hash, _bytes32(w3, metadata_hash)))


def register_artifact(artifact_id: str, exact_hash: str, robust_fingerprint: Optional[str], model_id: Optional[str]) -> Dict[str, Any]:
    w3, contract = _client()
    if w3 is None or contract is None:
        return {"success": False, "committed": False, "tx_hash": None, "reason": status()["note"]}
    return _send(contract.functions.registerArtifact(artifact_id, exact_hash, robust_fingerprint or "", model_id or ""))


def add_provenance_event(event_id: str, parent_artifact_id: Optional[str], child_artifact_id: str,
                         model_id: Optional[str], application_id: Optional[str], action: str,
                         metadata_hash: str, claim_hash: str) -> Dict[str, Any]:
    w3, contract = _client()
    if w3 is None or contract is None:
        return {"success": False, "committed": False, "tx_hash": None, "reason": status()["note"]}
    return _send(contract.functions.addProvenanceEvent(
        event_id, parent_artifact_id or "", child_artifact_id, model_id or "", application_id or "", action,
        _bytes32(w3, metadata_hash), _bytes32(w3, claim_hash)
    ))


def revoke_model(model_id: str) -> Dict[str, Any]:
    _, contract = _client()
    if contract is None:
        return {"success": False, "committed": False, "tx_hash": None, "reason": status()["note"]}
    return _send(contract.functions.revokeModel(model_id))


def revoke_claim(event_id: str) -> Dict[str, Any]:
    _, contract = _client()
    if contract is None:
        return {"success": False, "committed": False, "tx_hash": None, "reason": status()["note"]}
    return _send(contract.functions.revokeClaim(event_id))


def has_record(kind: str, identifier: str, commitment: Optional[str] = None) -> Optional[bool]:
    """Return True/False only after a real chain query; None means unavailable."""
    w3, contract = _client()
    if w3 is None or contract is None:
        return None
    try:
        if kind == "model":
            return bool(contract.functions.isModelRegistered(identifier, commitment or "").call())
        if kind == "artifact":
            return bool(contract.functions.isArtifactRegistered(identifier, commitment or "").call())
        if kind == "provenance":
            return bool(contract.functions.isProvenanceEventValid(identifier, _bytes32(w3, commitment or "")).call())
        return None
    except Exception:
        return False


def is_revoked_model(model_id: str) -> Optional[bool]:
    _, contract = _client()
    if contract is None:
        return None
    try:
        return bool(contract.functions.isModelRevoked(model_id).call())
    except Exception:
        return None


def is_revoked_claim(event_id: str) -> Optional[bool]:
    _, contract = _client()
    if contract is None:
        return None
    try:
        return bool(contract.functions.isClaimRevoked(event_id).call())
    except Exception:
        return None


def get_model(model_id: str) -> Optional[Dict[str, Any]]:
    _, contract = _client()
    if contract is None:
        return None
    try:
        res = contract.functions.getModel(model_id).call()
        return {
            "model_hash": res[0],
            "metadata_hash": res[1].hex() if isinstance(res[1], bytes) else res[1],
            "issuer": res[2],
            "timestamp": res[3],
            "revoked": res[4],
        }
    except Exception:
        return None


def get_artifact(artifact_id: str) -> Optional[Dict[str, Any]]:
    _, contract = _client()
    if contract is None:
        return None
    try:
        res = contract.functions.getArtifact(artifact_id).call()
        return {
            "exact_hash": res[0],
            "robust_fingerprint": res[1],
            "model_id": res[2],
            "issuer": res[3],
            "timestamp": res[4],
            "revoked": res[5],
        }
    except Exception:
        return None


def get_artifact_events(artifact_id: str) -> Optional[List[str]]:
    _, contract = _client()
    if contract is None:
        return None
    try:
        return list(contract.functions.getArtifactEvents(artifact_id).call())
    except Exception:
        return None


def get_provenance_event(event_id: str) -> Optional[Dict[str, Any]]:
    _, contract = _client()
    if contract is None:
        return None
    try:
        res = contract.functions.getProvenanceEvent(event_id).call()
        return {
            "event_id": res[0],
            "parent_artifact_id": res[1],
            "child_artifact_id": res[2],
            "model_id": res[3],
            "application_id": res[4],
            "action": res[5],
            "metadata_hash": res[6].hex() if isinstance(res[6], bytes) else res[6],
            "claim_hash": res[7].hex() if isinstance(res[7], bytes) else res[7],
            "issuer": res[8],
            "timestamp": res[9],
            "exists": res[10],
            "revoked": res[11],
        }
    except Exception:
        return None
