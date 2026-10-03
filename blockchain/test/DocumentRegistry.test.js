const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Legacy DocumentRegistry", function () {
  let registry;
  beforeEach(async function () {
    const Factory = await ethers.getContractFactory("DocumentRegistry");
    registry = await Factory.deploy();
    await registry.waitForDeployment();
  });
  it("registers and verifies", async function () {
    await registry.registerDocument("D1", "hash");
    expect(await registry.verifyDocument("D1", "hash")).to.equal(true);
  });
  it("detects mismatch", async function () {
    await registry.registerDocument("D2", "hash");
    expect(await registry.verifyDocument("D2", "other")).to.equal(false);
  });
  it("prevents duplicates", async function () {
    await registry.registerDocument("D3", "hash");
    await expect(registry.registerDocument("D3", "other")).to.be.revertedWith("Document already registered");
  });
});
