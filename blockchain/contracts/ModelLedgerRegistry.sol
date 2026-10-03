// SPDX-License-Identifier: MIT
pragma solidity ^0.8.27;

/// @title ModelLedgerRegistry
/// @notice Compact on-chain registry for AI model/artifact provenance commitments.
/// @dev Private prompts, source files, model binaries and biometric data never belong on-chain.
contract ModelLedgerRegistry {
    struct Model {
        string modelHash;
        bytes32 metadataHash;
        address issuer;
        uint256 timestamp;
        bool exists;
        bool revoked;
    }

    struct Artifact {
        string exactHash;
        string robustFingerprint;
        string modelId;
        address issuer;
        uint256 timestamp;
        bool exists;
        bool revoked;
    }

    struct ProvenanceEvent {
        string eventId;
        string parentArtifactId;
        string childArtifactId;
        string modelId;
        string applicationId;
        string action;
        bytes32 metadataHash;
        bytes32 claimHash;
        address issuer;
        uint256 timestamp;
        bool exists;
        bool revoked;
    }

    mapping(bytes32 => Model) private models;
    mapping(bytes32 => Artifact) private artifacts;
    mapping(bytes32 => ProvenanceEvent) private eventsById;
    mapping(bytes32 => bytes32[]) private eventIdsByChild;

    event ModelRegistered(string indexed modelId, string modelHash, bytes32 metadataHash, address indexed issuer);
    event ArtifactRegistered(string indexed artifactId, string exactHash, string modelId, address indexed issuer);
    event ProvenanceEventAdded(
        string indexed eventId,
        string indexed childArtifactId,
        string parentArtifactId,
        string modelId,
        string action,
        bytes32 claimHash,
        address indexed issuer
    );
    event ModelRevoked(string indexed modelId, address indexed issuer, uint256 timestamp);
    event ClaimRevoked(string indexed eventId, address indexed issuer, uint256 timestamp);

    modifier existingModel(string memory modelId) {
        require(models[_key(modelId)].exists, "Model not found");
        _;
    }

    modifier existingArtifact(string memory artifactId) {
        require(artifacts[_key(artifactId)].exists, "Artifact not found");
        _;
    }

    function _key(string memory value) internal pure returns (bytes32) {
        return keccak256(bytes(value));
    }

    function registerModel(
        string calldata modelId,
        string calldata modelHash,
        bytes32 metadataHash
    ) external {
        bytes32 key = _key(modelId);
        require(!models[key].exists, "Model already registered");
        models[key] = Model(modelHash, metadataHash, msg.sender, block.timestamp, true, false);
        emit ModelRegistered(modelId, modelHash, metadataHash, msg.sender);
    }

    function registerArtifact(
        string calldata artifactId,
        string calldata exactHash,
        string calldata robustFingerprint,
        string calldata modelId
    ) external {
        bytes32 key = _key(artifactId);
        require(!artifacts[key].exists, "Artifact already registered");
        if (bytes(modelId).length > 0) {
            require(models[_key(modelId)].exists, "Model not found");
        }
        artifacts[key] = Artifact(exactHash, robustFingerprint, modelId, msg.sender, block.timestamp, true, false);
        emit ArtifactRegistered(artifactId, exactHash, modelId, msg.sender);
    }

    function addProvenanceEvent(
        string calldata eventId,
        string calldata parentArtifactId,
        string calldata childArtifactId,
        string calldata modelId,
        string calldata applicationId,
        string calldata action,
        bytes32 metadataHash,
        bytes32 claimHash
    ) external existingArtifact(childArtifactId) {
        bytes32 key = _key(eventId);
        require(!eventsById[key].exists, "Provenance event already exists");
        if (bytes(parentArtifactId).length > 0) {
            require(artifacts[_key(parentArtifactId)].exists, "Parent artifact not found");
        }
        if (bytes(modelId).length > 0) {
            require(models[_key(modelId)].exists, "Model not found");
        }
        eventsById[key] = ProvenanceEvent(
            eventId,
            parentArtifactId,
            childArtifactId,
            modelId,
            applicationId,
            action,
            metadataHash,
            claimHash,
            msg.sender,
            block.timestamp,
            true,
            false
        );
        eventIdsByChild[_key(childArtifactId)].push(key);
        emit ProvenanceEventAdded(eventId, childArtifactId, parentArtifactId, modelId, action, claimHash, msg.sender);
    }

    function revokeModel(string calldata modelId) external existingModel(modelId) {
        Model storage model = models[_key(modelId)];
        require(msg.sender == model.issuer, "Not model issuer");
        model.revoked = true;
        emit ModelRevoked(modelId, msg.sender, block.timestamp);
    }

    function revokeClaim(string calldata eventId) external {
        ProvenanceEvent storage item = eventsById[_key(eventId)];
        require(item.exists, "Provenance event not found");
        require(msg.sender == item.issuer, "Not claim issuer");
        item.revoked = true;
        emit ClaimRevoked(eventId, msg.sender, block.timestamp);
    }

    function getModel(string calldata modelId)
        external
        view
        existingModel(modelId)
        returns (string memory, bytes32, address, uint256, bool)
    {
        Model memory m = models[_key(modelId)];
        return (m.modelHash, m.metadataHash, m.issuer, m.timestamp, m.revoked);
    }

    function getArtifact(string calldata artifactId)
        external
        view
        existingArtifact(artifactId)
        returns (string memory, string memory, string memory, address, uint256, bool)
    {
        Artifact memory a = artifacts[_key(artifactId)];
        return (a.exactHash, a.robustFingerprint, a.modelId, a.issuer, a.timestamp, a.revoked);
    }

    function getProvenanceEvent(string calldata eventId)
        external
        view
        returns (
            string memory,
            string memory,
            string memory,
            string memory,
            string memory,
            string memory,
            bytes32,
            bytes32,
            address,
            uint256,
            bool,
            bool
        )
    {
        ProvenanceEvent memory item = eventsById[_key(eventId)];
        require(item.exists, "Provenance event not found");
        return (
            item.eventId,
            item.parentArtifactId,
            item.childArtifactId,
            item.modelId,
            item.applicationId,
            item.action,
            item.metadataHash,
            item.claimHash,
            item.issuer,
            item.timestamp,
            item.exists,
            item.revoked
        );
    }

    function getArtifactEventIds(string calldata artifactId) public view existingArtifact(artifactId) returns (string[] memory) {
        bytes32[] memory keys = eventIdsByChild[_key(artifactId)];
        string[] memory ids = new string[](keys.length);
        for (uint256 i = 0; i < keys.length; i++) {
            ids[i] = eventsById[keys[i]].eventId;
        }
        return ids;
    }

    function getArtifactEvents(string calldata artifactId) external view returns (string[] memory) {
        return getArtifactEventIds(artifactId);
    }

    function isModelRegistered(string calldata modelId, string calldata expectedModelHash) external view returns (bool) {
        Model memory m = models[_key(modelId)];
        return m.exists && !m.revoked && keccak256(bytes(m.modelHash)) == keccak256(bytes(expectedModelHash));
    }

    function isArtifactRegistered(string calldata artifactId, string calldata expectedExactHash) external view returns (bool) {
        Artifact memory a = artifacts[_key(artifactId)];
        return a.exists && keccak256(bytes(a.exactHash)) == keccak256(bytes(expectedExactHash));
    }

    function isProvenanceEventValid(string calldata eventId, bytes32 expectedClaimHash) external view returns (bool) {
        ProvenanceEvent memory item = eventsById[_key(eventId)];
        return item.exists && !item.revoked && item.claimHash == expectedClaimHash;
    }

    function isModelRevoked(string calldata modelId) external view returns (bool) {
        Model memory m = models[_key(modelId)];
        require(m.exists, "Model not found");
        return m.revoked;
    }

    function isClaimRevoked(string calldata eventId) external view returns (bool) {
        ProvenanceEvent memory item = eventsById[_key(eventId)];
        require(item.exists, "Provenance event not found");
        return item.revoked;
    }
}
