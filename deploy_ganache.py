# deploy_ganache.py

import json
import time
from web3 import Web3

GANACHE_URL = "http://127.0.0.1:7545"
COMPILED_CONTRACTS_PATH = "build/contracts/" # Hardhat/Truffle output path

class GanacheDeployer:
    def __init__(self, ganache_url=GANACHE_URL):
        self.w3 = Web3(Web3.HTTPProvider(ganache_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Ganache'ye bağlanılamadı: {ganache_url}")
        self.admin_account = self.w3.eth.accounts[0]
        print(f"✅ Ganache'ye bağlanıldı. Admin: {self.admin_account}")

    def _load_contract_data(self, contract_name):
        """Loads ABI and bytecode from a compiled JSON file."""
        with open(f"{COMPILED_CONTRACTS_PATH}{contract_name}.json") as f:
            data = json.load(f)
        return data['abi'], data['bytecode']

    def deploy_contract(self, contract_name, *constructor_args):
        """Deploys a single contract."""
        abi, bytecode = self._load_contract_data(contract_name)
        contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
        
        tx_hash = contract.constructor(*constructor_args).transact({'from': self.admin_account})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"✅ '{contract_name}' deploy edildi. Adres: {tx_receipt.contractAddress}")
        return tx_receipt.contractAddress

    def full_deployment(self):
        """Deploys all contracts in the correct order."""
        print("\n🚀 Tam sistem deployment süreci başlıyor...")
        
        # 1. ModelVerifier deploy et
        verifier_address = self.deploy_contract("ModelVerifier")

        # 2. PdMSystem'i, verifier adresini alarak deploy et
        pdm_system_address = self.deploy_contract("PdMSystem", verifier_address)

        # 3. Deployment bilgilerini kaydet
        deployment_info = {
            "pdm_system_address": pdm_system_address,
            "verifier_address": verifier_address,
            "deployment_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open("deployment_info.json", "w") as f:
            json.dump(deployment_info, f, indent=2)
        print("💾 Deployment bilgileri 'deployment_info.json' dosyasına kaydedildi.")
        
        return deployment_info

if __name__ == "__main__":
    deployer = GanacheDeployer()
    deployer.full_deployment()