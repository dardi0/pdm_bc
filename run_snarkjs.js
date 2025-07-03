const snarkjs = require("snarkjs");
snarkjs.fastFile.engine = "mem";
const fs = require("fs");
const path = require("path");
const logger = {
    info: (...args) => console.log(...args),
    debug: (...args) => console.log(...args),
};

const BUILD_DIR = "./build";
const CIRCUIT_NAME = "pdm_verification";

async function main() {
    try {
        console.log("--- SNARKJS Fonksiyonlarıyla ZK Kurulumu Başlatılıyor ---");

        // Adım 1: Powers of Tau
        const ptau_0 = path.join(BUILD_DIR, "pot12_0000.ptau");
        const ptau_1 = path.join(BUILD_DIR, "pot12_0001.ptau");
        const ptau_final = path.join(BUILD_DIR, "pot12_final.ptau");

        if (!fs.existsSync(ptau_0)) {
            console.log("1.1. Yeni Powers of Tau seremonisi başlatılıyor...");
            await snarkjs.powersOfTau.newAccumulator(12, ptau_0, logger);
            console.log("✅ pot12_0000.ptau oluşturuldu.");
        } else {
            console.log("-> pot12_0000.ptau zaten mevcut.");
        }

        if (!fs.existsSync(ptau_1)) {
            console.log("1.2. Katkı yapılıyor...");
            await snarkjs.powersOfTau.contribute(ptau_0, ptau_1, "Ilk Katki", "biraz rastgelelik", logger);
            console.log("✅ pot12_0001.ptau oluşturuldu.");
        } else {
            console.log("-> pot12_0001.ptau zaten mevcut.");
        }

        if (!fs.existsSync(ptau_final)) {
            console.log("1.3. 2. Faz için hazırlık yapılıyor...");
            const ptau_beacon = await snarkjs.powersOfTau.beacon(ptau_1, ptau_final, "Beacon", "0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f", 10, logger);
            await snarkjs.powersOfTau.preparePhase2(ptau_beacon, ptau_final, logger);
            console.log("✅ pot12_final.ptau oluşturuldu.");
        } else {
            console.log("-> pot12_final.ptau zaten mevcut.");
        }

        // Adım 2: Groth16 Setup
        const r1csFile = path.join(BUILD_DIR, `${CIRCUIT_NAME}.r1cs`);
        const zkey_0 = path.join(BUILD_DIR, `${CIRCUIT_NAME}_0000.zkey`);
        const zkey_1 = path.join(BUILD_DIR, `${CIRCUIT_NAME}_0001.zkey`);
        const zkey_final = path.join(BUILD_DIR, `${CIRCUIT_NAME}_final.zkey`);

        console.log("2.1. Groth16 setup başlatılıyor...");
        await snarkjs.zKey.newZKey(r1csFile, ptau_final, zkey_0, logger);
        console.log("✅ pdm_verification_0000.zkey oluşturuldu.");

        console.log("2.2. zKey'e katkı yapılıyor...");
        await snarkjs.zKey.contribute(zkey_0, zkey_1, "Pdm Katki 1", "rastgele sifre", logger);
        console.log("✅ pdm_verification_0001.zkey oluşturuldu.");

        console.log("2.3. İkinci zKey'e katkı (beacon)...");
        await snarkjs.zKey.beacon(zkey_1, zkey_final, "Final Beacon", "0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f", 10, logger);
        console.log("✅ pdm_verification_final.zkey oluşturuldu.");

        // Adım 3: Verification Key Export
        const vKeyFile = path.join(BUILD_DIR, "verification_key.json");
        console.log("3.1. Verification key dışa aktarılıyor...");
        const verificationKey = await snarkjs.zKey.exportVerificationKey(zkey_final, logger);
        fs.writeFileSync(vKeyFile, JSON.stringify(verificationKey, null, 2));
        console.log("✅ verification_key.json oluşturuldu.");

        // Adım 4: Verifier Kontratı Oluşturma
        const verifierFile = path.join(BUILD_DIR, "Verifier.sol");
        console.log("4.1. Solidity verifier oluşturuluyor...");
        const templates = {
            groth16: await fs.promises.readFile(path.join(__dirname, "node_modules", "snarkjs", "templates", "verifier_groth16.sol.ejs"), "utf8")
        };
        const solidityCode = await snarkjs.zKey.exportSolidityVerifier(zkey_final, templates, logger);
        fs.writeFileSync(verifierFile, solidityCode);
        console.log("✅ Verifier.sol oluşturuldu.");


        console.log("\n--- ZK Kurulumu Başarıyla Tamamlandı! ---");

    } catch (err) {
        console.error("HATA:", err);
    }
}

main(); 