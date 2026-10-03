"""Cryptographic provenance signatures for Phase 4.

ECDSA/secp256k1 is used so the signing curve matches Ethereum wallets. The
private key is supplied through MODELLEDGER_SIGNATURE_PRIVATE_KEY_PEM and is
never persisted by the application. Each event stores the public key needed to
verify its signature independently.
"""
from __future__ import annotations

import base64
import json
from typing import Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature

import config
from models.provenance import ProvenanceEvent

IMPLEMENTED = True


def canonical_event_payload(event: ProvenanceEvent) -> bytes:
    payload = {
        "event_id": event.event_id,
        "parent_artifact_id": event.parent_artifact_id,
        "child_artifact_id": event.child_artifact_id,
        "model_id": event.model_id,
        "application_id": event.application_id,
        "action": event.action.value,
        "metadata_hash": event.metadata_hash,
        "created_at": event.created_at.isoformat(),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def claim_hash(event: ProvenanceEvent) -> str:
    import hashlib
    return hashlib.sha256(canonical_event_payload(event)).hexdigest()


def _private_key():
    if not config.SIGNATURE_PRIVATE_KEY_PEM:
        return None
    return serialization.load_pem_private_key(config.SIGNATURE_PRIVATE_KEY_PEM.encode(), password=None)


def sign_event(event: ProvenanceEvent) -> Optional[Tuple[str, str]]:
    key = _private_key()
    if key is None:
        return None
    if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(key.curve, ec.SECP256K1):
        raise ValueError("MODELLEDGER_SIGNATURE_PRIVATE_KEY_PEM must be a secp256k1 PEM private key")
    signature = key.sign(canonical_event_payload(event), ec.ECDSA(hashes.SHA256()))
    public_key = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return base64.b64encode(signature).decode(), base64.b64encode(public_key).decode()


def verify_event_signature(event: ProvenanceEvent, public_key_b64: Optional[str] = None) -> Optional[bool]:
    if not event.signature or not public_key_b64:
        return None
    try:
        signature = base64.b64decode(event.signature.encode(), validate=True)
        public_key = serialization.load_pem_public_key(base64.b64decode(public_key_b64.encode()))
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            return False
        public_key.verify(signature, canonical_event_payload(event), ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


def signing_public_key() -> Optional[str]:
    key = _private_key()
    if key is None:
        return None
    public_key = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return base64.b64encode(public_key).decode()
