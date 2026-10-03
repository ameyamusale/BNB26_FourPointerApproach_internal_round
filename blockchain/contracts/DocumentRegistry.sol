// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

/// @title DocumentRegistry (LEGACY baseline)
/// @notice Kept only so the Phase 0 deploy/test flow works. It is replaced by
///         ModelLedgerRegistry.sol in Phase 3.
/// @dev The `Dhruv` baseline shipped this file with JavaScript test code inside it
///      (it could not compile). It was reconstructed from DocumentRegistry.test.js.
contract DocumentRegistry {
    struct Document {
        string hash;
        address issuer;
        uint256 timestamp;
        bool exists;
    }

    mapping(string => Document) private documents;

    event DocumentRegistered(string indexed documentIdIndexed, string documentId, string hash, address issuer);

    function registerDocument(string memory documentId, string memory documentHash) public {
        require(!documents[documentId].exists, "Document already registered");
        documents[documentId] = Document(documentHash, msg.sender, block.timestamp, true);
        emit DocumentRegistered(documentId, documentId, documentHash, msg.sender);
    }

    function verifyDocument(string memory documentId, string memory documentHash) public view returns (bool) {
        require(documents[documentId].exists, "Document not found");
        return keccak256(bytes(documents[documentId].hash)) == keccak256(bytes(documentHash));
    }

    function getDocument(string memory documentId)
        public
        view
        returns (string memory, address, uint256)
    {
        require(documents[documentId].exists, "Document not found");
        Document memory d = documents[documentId];
        return (d.hash, d.issuer, d.timestamp);
    }
}
