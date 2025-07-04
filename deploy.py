import json
import time
import os
from web3 import Web3
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri yükle
load_dotenv()

# Ortam değişkenlerini al
HOLESKY_RPC_URL = os.getenv("Holesky_RPC_URL")
PRIVATE_KEY = os.getenv("Private_Key")

# Hardhat tarafından oluşturulan artifact'lerin yolu
ARTIFACTS_PATH = "artifacts/contracts/"

class Deployer:
    def __init__(self):
        if not all([HOLESKY_RPC_URL, PRIVATE_KEY]):
            raise Exception("Lütfen .env dosyasında Holesky_RPC_URL ve Private_Key değişkenlerini ayarlayın.")
        
        self.w3 = Web3(Web3.HTTPProvider(HOLESKY_RPC_URL))
        if not self.w3.is_connected():
            raise ConnectionError(f"Holesky ağına bağlanılamadı: {HOLESKY_RPC_URL}")
        
        self.account = self.w3.eth.account.from_key(PRIVATE_KEY)
        self.admin_account = self.account.address
        print(f"✅ Holesky testnet ağına bağlanıldı. Deploy eden hesap: {self.admin_account}")
        print(f"💰 Bakiye: {self.w3.from_wei(self.w3.eth.get_balance(self.admin_account), 'ether')} HolETH")

    def _load_contract_data(self, contract_file_with_sol, contract_name):
        """Derlenmiş kontratın ABI ve Bytecode'unu yükler."""
        full_path = f"{ARTIFACTS_PATH}{contract_file_with_sol}/{contract_name}.json"
        with open(full_path) as f:
            data = json.load(f)
        return data['abi'], data['bytecode']

    def deploy_contract(self, contract_file_with_sol, contract_name, *constructor_args):
        """Bir kontratı imzalar, gönderir ve deploy eder."""
        abi, bytecode = self._load_contract_data(contract_file_with_sol, contract_name)
        contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        
        # Nonce'ı al (bir sonraki işlem numarası)
        nonce = self.w3.eth.get_transaction_count(self.admin_account)
        
        # İşlemi oluştur
        transaction = contract.constructor(*constructor_args).build_transaction({
            'from': self.admin_account,
            'nonce': nonce,
            'gas': 2000000, # Bu değeri artırmanız gerekebilir
            'gasPrice': self.w3.to_wei('10', 'gwei') # Gaz fiyatını ağ yoğunluğuna göre ayarlayın
        })
        
        # İşlemi imzala
        signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key=PRIVATE_KEY)
        
        # İmzalı işlemi gönder
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"⏳ '{contract_name}' deploy işlemi gönderildi. Tx Hash: {tx_hash.hex()}")
        
        # İşlemin onaylanmasını bekle
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"✅ '{contract_name}' deploy edildi. Adres: {tx_receipt.contractAddress}")
        return tx_receipt.contractAddress

    def full_deployment(self):
        """Tüm sistemi Holesky testnet ağına deploy eder."""
        print("\n🚀 Holesky Testnet Deployment Başlıyor...")
        
        # 1. Groth16Verifier'ı deploy et
        verifier_address = self.deploy_contract("PDMVerifier.sol", "Groth16Verifier")

        # 2. PdMSystem'i, verifier adresini alarak deploy et
        pdm_system_address = self.deploy_contract("PdMSystem.sol", "PdMSystem", verifier_address)

        deployment_info = {
            "pdm_system_address": pdm_system_address,
            "groth16_verifier_address": verifier_address,
            "network": "Holesky Testnet",
            "rpc_url": HOLESKY_RPC_URL,
            "deployer_account": self.admin_account,
            "deployment_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "gas_price_gwei": float(self.w3.from_wei(self.w3.eth.gas_price, 'gwei'))
        }
        
        with open("holesky_deployment_info.json", "w") as f:
            json.dump(deployment_info, f, indent=2)
        
        print("\n💾 Deployment bilgileri 'holesky_deployment_info.json' dosyasına kaydedildi.")
        print(f"🔗 Holesky Etherscan'de görüntüle:")
        print(f"   PDM System: https://holesky.etherscan.io/address/{pdm_system_address}")
        print(f"   Groth16 Verifier: https://holesky.etherscan.io/address/{verifier_address}")
        
        return deployment_info

if __name__ == "__main__":
    try:
        deployer = Deployer()
        deployment_info = deployer.full_deployment()
        print("\n✅ Tüm kontratlar başarıyla Holesky testnet'e deploy edildi!")
    except Exception as e:
        print(f"\n❌ Deployment hatası: {e}")
