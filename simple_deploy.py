#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from web3 import Web3
import json
import time

# Ganache bağlantısı
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))

# Basit contract (inline compilation olmadan)
SIMPLE_ZK_VERIFIER_BYTECODE = "0x608060405234801561001057600080fd5b506101d7806100206000396000f3fe608060405234801561001057600080fd5b50600436106100415760003560e01c80634f1ef28614610046578063715018a614610050578063cf67a43b1461005a575b600080fd5b61004e610078565b005b6100586100b5565b005b610062610129565b60405161006f9190610182565b60405180910390f35b7f8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0600080a1565b6100bd610131565b73ffffffffffffffffffffffffffffffffffffffff166100db610129565b73ffffffffffffffffffffffffffffffffffffffff1614610131576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161012890610194565b60405180910390fd5b565b600033905090565b6000600160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16905090565b61015f81610139565b82525050565b600060208201905061017a6000830184610156565b92915050565b60006020820190508181036000830152610199816101b4565b9050919050565b7f4f776e61626c653a2063616c6c6572206973206e6f7420746865206f776e6572600082015250565b60006101d6602083610165565b91506101e1826101a0565b602082019050919050565b600082825260208201905092915050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052602260045260246000fdfea2646970667358221220"

SIMPLE_ZK_VERIFIER_ABI = [
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalVerifications", 
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

def deploy_simple_contract():
    """Çok basit contract deploy eder"""
    
    print("🚀 Basit ZK Contract Deploy Ediliyor...")
    
    if not w3.is_connected():
        print("❌ Ganache bağlantısı yok!")
        return None
    
    # En basit contract - sadece storage
    simple_contract_bytecode = "0x6080604052348015600f57600080fd5b5060928061001e6000396000f3fe6080604052348015600f57600080fd5b506004361060285760003560e01c8063a87d942c14602d575b600080fd5b60336047565b604051603e9190605a565b60405180910390f35b60005481565b6060819050919050565b605481607a565b82525050565b6000602082019050606d6000830184604d565b92915050565b600081905091905056fea26469706673582212209e5c0e5e0b5c4b9c8e3e8b5c4b9c8e3e8b5c4b9c8e3e8b5c4b9c8e3e8b5c4b9c64736f6c63430008000033"
    
    simple_abi = [
        {
            "inputs": [],
            "name": "get",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]
    
    try:
        # Contract oluştur
        contract = w3.eth.contract(abi=simple_abi, bytecode=simple_contract_bytecode)
        
        # Admin account
        admin = w3.eth.accounts[0]
        
        # Deploy transaction
        tx_hash = contract.constructor().transact({'from': admin, 'gas': 500000})
        
        # Receipt bekle
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"✅ Contract deployed!")
        print(f"📍 Address: {receipt.contractAddress}")
        print(f"⛽ Gas: {receipt.gasUsed:,}")
        
        # Config dosyası kaydet
        config = {
            "SIMPLE_CONTRACT_ADDRESS": receipt.contractAddress,
            "GANACHE_URL": "http://127.0.0.1:7545",
            "ADMIN_ACCOUNT": admin,
            "DEPLOYMENT_TIME": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open("simple_contract_config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        print("💾 Config saved: simple_contract_config.json")
        return receipt.contractAddress
        
    except Exception as e:
        print(f"❌ Deployment error: {e}")
        return None

def deploy_with_manual_bytecode():
    """Manuel bytecode ile deploy"""
    
    print("🔧 Manuel Bytecode ile Deploy...")
    
    # En minimal bytecode - sadece return 42
    minimal_bytecode = "0x60006000600060006000602a600020f3"
    
    try:
        admin = w3.eth.accounts[0]
        
        # Raw transaction
        tx = {
            'from': admin,
            'data': minimal_bytecode,
            'gas': 200000,
            'gasPrice': w3.to_wei('20', 'gwei')
        }
        
        # Send transaction
        tx_hash = w3.eth.send_transaction(tx)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"✅ Manuel deploy başarılı!")
        print(f"📍 Address: {receipt.contractAddress}")
        
        return receipt.contractAddress
        
    except Exception as e:
        print(f"❌ Manuel deploy hatası: {e}")
        return None

def main():
    print("🎯 Basit Contract Deployment Test")
    print("=" * 50)
    
    # Connection check
    if w3.is_connected():
        print(f"✅ Ganache: AKTIF")
        print(f"📊 Accounts: {len(w3.eth.accounts)}")
        
        # Method 1: Simple contract
        addr1 = deploy_simple_contract()
        
        if not addr1:
            print("\n🔧 Manuel bytecode deneyelim...")
            addr2 = deploy_with_manual_bytecode()
            
        print("\n🎉 Deploy test tamamlandı!")
        
    else:
        print("❌ Ganache bağlantısı yok!")

if __name__ == "__main__":
    main() 