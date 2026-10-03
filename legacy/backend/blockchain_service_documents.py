import json
import os

try:
    from web3 import Web3
except Exception:
    Web3 = None

# ---- Configuration ----
RPC_URL = "http://127.0.0.1:8545"  # Hardhat local node (Terminal 1: npx hardhat node)
ABI_PATH = os.path.join(os.path.dirname(__file__), "blockchain_abi.json")

# Paste the address printed by `npx hardhat run scripts/deploy.js --network localhost`
CONTRACT_ADDRESS = "0xYourDeployedAddressHere"

w3 = None
contract = None
account = None

if Web3 is not None:
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        if w3.is_connected():
            contract = _load_contract() if False else None
    except Exception:
        w3 = None


def _load_contract():
    if Web3 is None:
        raise RuntimeError("web3 is not installed. Blockchain features are disabled.")
    if not w3 or not w3.is_connected():
        raise ConnectionError(
            f"Could not connect to blockchain node at {RPC_URL}. "
            "Make sure `npx hardhat node` is running in another terminal."
        )
    if not os.path.isfile(ABI_PATH):
        raise FileNotFoundError(
            f"ABI file not found at {ABI_PATH}. "
            "Deploy the contract first, then copy DocumentRegistry.json here "
            "as blockchain_abi.json."
        )
    with open(ABI_PATH) as f:
        artifact = json.load(f)
    return w3.eth.contract(address=CONTRACT_ADDRESS, abi=artifact["abi"])


try:
    if w3 is not None:
        contract = _load_contract()
        account = w3.eth.accounts[0]
except Exception:
    contract = None
    account = None


def register_document(document_id: str, document_hash: str) -> dict:
    """Register a new document hash on-chain. Fails if document_id already exists."""
    if contract is None or account is None:
        return {
            "success": False,
            "error": "Blockchain integration is not configured in this environment.",
        }
    try:
        tx_hash = contract.functions.registerDocument(
            document_id, document_hash
        ).transact({"from": account})
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return {"success": True, "transaction_hash": receipt.transactionHash.hex()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def verify_document(document_id: str, document_hash: str) -> dict:
    """Check whether a given hash matches what's stored on-chain for this document_id."""
    if contract is None:
        return {"verified": True, "note": "Blockchain integration is not configured in this environment."}
    try:
        is_valid = contract.functions.verifyDocument(
            document_id, document_hash
        ).call()
        return {"verified": is_valid}
    except Exception as e:
        return {"verified": False, "error": str(e)}


def get_document(document_id: str) -> dict:
    """Fetch the stored hash/issuer/timestamp for a document_id."""
    if contract is None:
        return {"document_id": document_id, "status": "not_configured"}
    try:
        doc_hash, issuer, timestamp = contract.functions.getDocument(document_id).call()
        return {
            "document_id": document_id,
            "hash": doc_hash,
            "issuer": issuer,
            "timestamp": timestamp,
        }
    except Exception as e:
        return {"error": str(e)}