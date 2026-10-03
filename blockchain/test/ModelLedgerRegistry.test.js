const { expect } = require("chai");
const { ethers } = require("hardhat");

const idHash = (value) => ethers.keccak256(ethers.toUtf8Bytes(value));
const bytes32 = (value) => ethers.keccak256(ethers.toUtf8Bytes(value));

describe("ModelLedgerRegistry", function () {
  let registry, owner, other;

  beforeEach(async function () {
    [owner, other] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("ModelLedgerRegistry");
    registry = await Factory.deploy();
    await registry.waitForDeployment();
  });

  it("registers a model", async function () {
    await expect(registry.registerModel("MDL-1", "a".repeat(64), bytes32("metadata")))
      .to.emit(registry, "ModelRegistered");
    const result = await registry.getModel("MDL-1");
    expect(result[0]).to.equal("a".repeat(64));
    expect(result[2]).to.equal(owner.address);
    expect(result[4]).to.equal(false);
  });

  it("prevents duplicate models", async function () {
    await registry.registerModel("MDL-1", "a".repeat(64), bytes32("metadata"));
    await expect(registry.registerModel("MDL-1", "b".repeat(64), bytes32("metadata2")))
      .to.be.revertedWith("Model already registered");
  });

  it("registers an artifact linked to a model", async function () {
    await registry.registerModel("MDL-1", "a".repeat(64), bytes32("metadata"));
    await expect(registry.registerArtifact("ART-1", "b".repeat(64), "abcd", "MDL-1"))
      .to.emit(registry, "ArtifactRegistered");
    const result = await registry.getArtifact("ART-1");
    expect(result[0]).to.equal("b".repeat(64));
    expect(result[2]).to.equal("MDL-1");
  });

  it("links a parent-child provenance event", async function () {
    await registry.registerModel("MDL-1", "a".repeat(64), bytes32("metadata"));
    await registry.registerArtifact("ART-1", "b".repeat(64), "fp1", "MDL-1");
    await registry.registerArtifact("ART-2", "c".repeat(64), "fp2", "MDL-1");
    await expect(registry.addProvenanceEvent(
      "EVT-1", "ART-1", "ART-2", "MDL-1", "App", "UPSCALED", bytes32("meta"), bytes32("claim")
    )).to.emit(registry, "ProvenanceEventAdded");
    expect(await registry.isProvenanceEventValid("EVT-1", bytes32("claim"))).to.equal(true);
    expect(await registry.getArtifactEventIds("ART-2")).to.deep.equal(["EVT-1"]);
  });

  it("rejects invalid parent references", async function () {
    await registry.registerArtifact("ART-2", "c".repeat(64), "fp2", "");
    await expect(registry.addProvenanceEvent(
      "EVT-1", "ART-NOPE", "ART-2", "", "", "EDITED", bytes32("meta"), bytes32("claim")
    )).to.be.revertedWith("Parent artifact not found");
  });

  it("supports model and claim revocation without deleting history", async function () {
    await registry.registerModel("MDL-1", "a".repeat(64), bytes32("metadata"));
    await registry.registerArtifact("ART-1", "b".repeat(64), "fp", "MDL-1");
    await registry.addProvenanceEvent("EVT-1", "", "ART-1", "MDL-1", "", "GENERATED", bytes32("m"), bytes32("c"));
    await registry.revokeModel("MDL-1");
    expect(await registry.isModelRevoked("MDL-1")).to.equal(true);
    await registry.revokeClaim("EVT-1");
    expect(await registry.isClaimRevoked("EVT-1")).to.equal(true);
    const event = await registry.getProvenanceEvent("EVT-1");
    expect(event[0]).to.equal("EVT-1");
    expect(event[11]).to.equal(true);
  });

  it("blocks unauthorized revocation", async function () {
    await registry.registerModel("MDL-1", "a".repeat(64), bytes32("metadata"));
    await expect(registry.connect(other).revokeModel("MDL-1")).to.be.revertedWith("Not model issuer");
  });

  it("blocks unauthorized claim revocation", async function () {
    await registry.registerModel("MDL-1", "a".repeat(64), bytes32("metadata"));
    await registry.registerArtifact("ART-1", "b".repeat(64), "fp", "MDL-1");
    await registry.addProvenanceEvent("EVT-1", "", "ART-1", "MDL-1", "", "GENERATED", bytes32("m"), bytes32("c"));
    await expect(registry.connect(other).revokeClaim("EVT-1")).to.be.revertedWith("Not claim issuer");
  });

  it("prevents duplicate artifact registrations", async function () {
    await registry.registerArtifact("ART-1", "b".repeat(64), "fp1", "");
    await expect(registry.registerArtifact("ART-1", "c".repeat(64), "fp2", ""))
      .to.be.revertedWith("Artifact already registered");
  });

  it("rejects artifact registration with non-existent model", async function () {
    await expect(registry.registerArtifact("ART-1", "b".repeat(64), "fp1", "MDL-UNKNOWN"))
      .to.be.revertedWith("Model not found");
  });

  it("rejects provenance event with non-existent child, parent or model", async function () {
    await registry.registerModel("MDL-1", "a".repeat(64), bytes32("metadata"));
    await registry.registerArtifact("ART-1", "b".repeat(64), "fp1", "MDL-1");

    // Non-existent child
    await expect(registry.addProvenanceEvent(
      "EVT-1", "", "ART-UNKNOWN", "MDL-1", "", "GENERATED", bytes32("m"), bytes32("c")
    )).to.be.revertedWith("Artifact not found");

    // Non-existent model
    await expect(registry.addProvenanceEvent(
      "EVT-1", "", "ART-1", "MDL-UNKNOWN", "", "GENERATED", bytes32("m"), bytes32("c")
    )).to.be.revertedWith("Model not found");
  });

  it("prevents duplicate provenance events", async function () {
    await registry.registerArtifact("ART-1", "b".repeat(64), "fp1", "");
    await registry.addProvenanceEvent("EVT-1", "", "ART-1", "", "", "GENERATED", bytes32("m"), bytes32("c"));
    await expect(registry.addProvenanceEvent("EVT-1", "", "ART-1", "", "", "GENERATED", bytes32("m"), bytes32("c")))
      .to.be.revertedWith("Provenance event already exists");
  });

  it("supports getArtifactEvents alias and entity lookup reverts", async function () {
    await registry.registerArtifact("ART-1", "b".repeat(64), "fp1", "");
    await registry.addProvenanceEvent("EVT-1", "", "ART-1", "", "", "GENERATED", bytes32("m"), bytes32("c"));

    expect(await registry.getArtifactEvents("ART-1")).to.deep.equal(["EVT-1"]);

    await expect(registry.getModel("MDL-UNKNOWN")).to.be.revertedWith("Model not found");
    await expect(registry.getArtifact("ART-UNKNOWN")).to.be.revertedWith("Artifact not found");
    await expect(registry.getProvenanceEvent("EVT-UNKNOWN")).to.be.revertedWith("Provenance event not found");
  });
});
