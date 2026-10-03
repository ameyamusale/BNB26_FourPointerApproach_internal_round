const hre = require("hardhat");

async function main() {
  const Factory = await hre.ethers.getContractFactory("ModelLedgerRegistry");
  const registry = await Factory.deploy();
  await registry.waitForDeployment();
  const address = await registry.getAddress();

  console.log(`ModelLedgerRegistry deployed to: ${address}`);
  console.log("\nBackend configuration:");
  console.log("MODELLEDGER_RPC_URL=http://127.0.0.1:8545");
  console.log(`MODELLEDGER_CONTRACT_ADDRESS=${address}`);
  console.log("MODELLEDGER_TX_PRIVATE_KEY=<private key of an authorized Hardhat account>");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
