#!/usr/bin/env node

/*
Basit ZK Setup - Powers of Tau olmadan lokal test için
*/

const snarkjs = require("snarkjs");
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const CIRCUIT_NAME = "pdm_verification";
const BUILD_DIR = "./build";
const CIRCOM_BINARY = "./circom2.exe";

async function simpleSetup() {
    console.log("🔧 Basit PDM ZK Setup Başlıyor...");
    console.log("=" .repeat(50));
    
    try {
        // 1. Build directory kontrol et
        if (!fs.existsSync(BUILD_DIR)) {
            fs.mkdirSync(BUILD_DIR, { recursive: true });
        }
        
        // 2. Test input oluştur (Powers of Tau olmadan)
        console.log("🧪 Test input oluşturuluyor...");
        const testInput = {
            // Public inputs
            modelCommitment: 12345,
            claimedAccuracy: 90,
            timestamp: Math.floor(Date.now() / 1000),
            
            // Private inputs
            modelHash: 54321,
            actualAccuracy: 95,
            nonce: 67890
        };
        
        fs.writeFileSync(`${BUILD_DIR}/test_input.json`, JSON.stringify(testInput, null, 2));
        console.log("✅ Test input oluşturuldu");
        
        // 3. Circuit info göster
        console.log("📊 Circuit Bilgileri:");
        console.log(`   🔐 Circuit: ${CIRCUIT_NAME}`);
        console.log(`   📁 Build: ${BUILD_DIR}`);
        console.log(`   ⚙️  Public inputs: modelCommitment, claimedAccuracy, timestamp`);
        console.log(`   🔒 Private inputs: modelHash, actualAccuracy, nonce`);
        
        // 4. Dosyaları kontrol et
        const wasmFile = `${BUILD_DIR}/${CIRCUIT_NAME}_js/${CIRCUIT_NAME}.wasm`;
        const r1csFile = `${BUILD_DIR}/${CIRCUIT_NAME}.r1cs`;
        
        if (fs.existsSync(wasmFile) && fs.existsSync(r1csFile)) {
            console.log("✅ Circuit dosyaları mevcut");
            
            // 5. Basit proof generation script oluştur
            const proofScript = generateSimpleProofScript();
            fs.writeFileSync(`${BUILD_DIR}/simple_proof.js`, proofScript);
            console.log("✅ simple_proof.js oluşturuldu");
            
            // 6. Blockchain integration script
            const integrationScript = generateIntegrationScript();
            fs.writeFileSync(`${BUILD_DIR}/blockchain_integration.js`, integrationScript);
            console.log("✅ blockchain_integration.js oluşturuldu");
            
        } else {
            console.log("⚠️  Circuit dosyaları eksik, derleme yapılıyor...");
            const compileCmd = `${CIRCOM_BINARY} ${CIRCUIT_NAME}.circom --r1cs --wasm --sym -o ${BUILD_DIR}`;
            execSync(compileCmd, { stdio: 'inherit' });
            console.log("✅ Circuit derlendi");
        }
        
        console.log("\n" + "🎉".repeat(25));
        console.log("🎉 Basit PDM ZK Setup Tamamlandı!");
        console.log("=" .repeat(50));
        console.log("📁 Oluşturulan Dosyalar:");
        console.log(`   🧪 ${BUILD_DIR}/test_input.json (Test input)`);
        console.log(`   📜 ${BUILD_DIR}/simple_proof.js (Basit proof generation)`);
        console.log(`   🔗 ${BUILD_DIR}/blockchain_integration.js (Blockchain entegrasyonu)`);
        console.log("\n💡 Sonraki adımlar:");
        console.log("   1. node build/simple_proof.js - Test proof oluştur");
        console.log("   2. npm install web3 - Blockchain entegrasyonu için");
        console.log("   3. Ganache veya test ağında dene");
        
        return true;
        
    } catch (error) {
        console.error("❌ Setup hatası:", error.message);
        return false;
    }
}

function generateSimpleProofScript() {
    return `#!/usr/bin/env node

/*
Basit Proof Generation - PDM Test
*/

const fs = require("fs");

async function generateSimpleProof() {
    try {
        console.log("🔐 Basit PDM Proof simülasyonu...");
        
        // Test input'u oku
        const testInput = JSON.parse(fs.readFileSync("./test_input.json", "utf8"));
        console.log("📊 Test Input:", testInput);
        
        // Simulated proof (gerçek ZK proof olmadan)
        const simulatedProof = {
            proof: {
                pi_a: ["0x" + Math.random().toString(16).slice(2), "0x" + Math.random().toString(16).slice(2)],
                pi_b: [["0x" + Math.random().toString(16).slice(2), "0x" + Math.random().toString(16).slice(2)],
                       ["0x" + Math.random().toString(16).slice(2), "0x" + Math.random().toString(16).slice(2)]],
                pi_c: ["0x" + Math.random().toString(16).slice(2), "0x" + Math.random().toString(16).slice(2)],
                protocol: "groth16"
            },
            publicSignals: [
                testInput.modelCommitment.toString(),
                testInput.claimedAccuracy.toString(),
                testInput.timestamp.toString()
            ]
        };
        
        // Simulated verification
        const isValid = testInput.claimedAccuracy <= testInput.actualAccuracy;
        console.log(\`✅ Simulated verification: \${isValid ? 'BAŞARILI ✅' : 'BAŞARISIZ ❌'}\`);
        
        // Proof'u kaydet
        fs.writeFileSync("./simulated_proof.json", JSON.stringify(simulatedProof, null, 2));
        console.log("💾 Simulated proof kaydedildi: simulated_proof.json");
        
        return simulatedProof;
        
    } catch (error) {
        console.error("❌ Proof generation hatası:", error);
        return null;
    }
}

if (require.main === module) {
    generateSimpleProof();
}

module.exports = { generateSimpleProof };
`;
}

function generateIntegrationScript() {
    return `#!/usr/bin/env node

/*
PDM Blockchain Integration Script
*/

const fs = require("fs");

class PDMBlockchainIntegration {
    constructor() {
        console.log("🔗 PDM Blockchain Integration");
        this.web3 = null;
        this.contract = null;
    }
    
    async connect(ganacheUrl = "http://127.0.0.1:7545") {
        try {
            // Web3 bağlantısı kurulacak
            console.log(\`🌐 Connecting to \${ganacheUrl}...\`);
            
            // Bu kısım Web3 kurulumundan sonra aktif olacak
            console.log("ℹ️  Web3 kurulumu için: npm install web3");
            
            return true;
        } catch (error) {
            console.error("❌ Bağlantı hatası:", error);
            return false;
        }
    }
    
    async submitProof(proof, publicSignals) {
        try {
            console.log("📤 Submitting PDM proof to blockchain...");
            console.log("🔐 Proof:", JSON.stringify(proof, null, 2));
            console.log("📊 Public Signals:", publicSignals);
            
            // Simulated blockchain submission
            const txHash = "0x" + Math.random().toString(16).slice(2, 66);
            const modelId = "0x" + Math.random().toString(16).slice(2, 66);
            
            console.log(\`✅ Proof submitted! TX: \${txHash}\`);
            console.log(\`🆔 Model ID: \${modelId}\`);
            
            return { txHash, modelId };
            
        } catch (error) {
            console.error("❌ Proof submission hatası:", error);
            return null;
        }
    }
    
    async getModelStatus(modelId) {
        console.log(\`📋 Model status: \${modelId} - VERIFIED ✅\`);
        return {
            verified: true,
            timestamp: Date.now(),
            accuracy: 90,
            submitter: "0x1234567890123456789012345678901234567890"
        };
    }
}

async function runIntegrationTest() {
    console.log("🧪 PDM Integration Test Başlıyor...");
    
    const pdm = new PDMBlockchainIntegration();
    
    // 1. Blockchain'e bağlan
    await pdm.connect();
    
    // 2. Test proof'u oku
    if (fs.existsSync("./simulated_proof.json")) {
        const { proof, publicSignals } = JSON.parse(fs.readFileSync("./simulated_proof.json", "utf8"));
        
        // 3. Proof'u gönder
        const result = await pdm.submitProof(proof, publicSignals);
        
        if (result) {
            // 4. Model durumunu kontrol et
            await pdm.getModelStatus(result.modelId);
        }
    } else {
        console.log("❌ Simulated proof bulunamadı. Önce node simple_proof.js çalıştırın.");
    }
}

if (require.main === module) {
    runIntegrationTest();
}

module.exports = { PDMBlockchainIntegration };
`;
}

// Script çalıştır
if (require.main === module) {
    simpleSetup()
        .then(success => {
            process.exit(success ? 0 : 1);
        })
        .catch(error => {
            console.error("❌ Fatal error:", error);
            process.exit(1);
        });
}

module.exports = { simpleSetup }; 