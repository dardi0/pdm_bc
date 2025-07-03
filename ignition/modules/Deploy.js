const { buildModule } = require("@nomicfoundation/hardhat-ignition/modules");

module.exports = buildModule("PDMDeployment", (m) => {
  // 1. ZK Verifier Contract'ını deploy et
  const verifier = m.contract("Groth16Verifier");
  
  // 2. PDM System Contract'ını verifier adresiyle deploy et  
  const pdmSystem = m.contract("PdMSystem", [verifier]);
  
  return { verifier, pdmSystem };
}); 