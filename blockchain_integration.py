import json
import os
from web3 import Web3
from eth_account import Account
import time

class GanacheBlockchainIntegration:
    def __init__(self):
        """Ganache blockchain entegrasyonu"""
        # Ganache bağlantı bilgileri
        self.web3_url = "http://127.0.0.1:7545"
        self.web3 = Web3(Web3.HTTPProvider(self.web3_url))
        
        # Ganache'deki deploy edilmiş contract adresleri
        self.groth16_verifier_address = "0x98EA576277EBA3F203C61D194E6659B5C4b15377"
        self.pdm_system_address = "0x3099510854Dd3165bdD07bea8410a7Bc0CcfD3fA"
        
        # Ganache test hesapları (Gerçek Address + Private Key)
        self.accounts = {
            'admin': {
                'address': '0x8c26B29aE0Aa34d313Ce3B1891CecbE85d9E68Ae',
                'private_key': '0x23aaa9c52bcad9b5367c8ad7e90c04697e53cf13ea4d6176bffd52f25816bf7b'
            },
            'engineer': {
                'address': '0xf05E6F150227D1aAc28FC57cdAC095f3Ee286D67',
                'private_key': '0x6f36c4acf77342630b509fcdee80129ec5c4b9eef15e68112029300ae25a966c'
            },
            'worker': {
                'address': '0x793BCB1789BE4B14aCCBa18375092FC33F3B23fA',
                'private_key': '0x30effcecffb610c8a05be599979562b708da5f38358b59097c2b92e687247073'
            },
            'user': {
                'address': '0xC687b799bAd7E1716F693dF4798871e5093844E2',
                'private_key': '0x3d90df30e39ee3dade85069b5e5bc52ef9fc9b1e1cf5f6a14672a52dae484098'
            }
        }
        
        # Contracts
        self.pdm_contract = None
        self.verifier_contract = None
        
        self.initialize_contracts()
    
    def initialize_contracts(self):
        """Contract'ları yükle"""
        try:
            # Bağlantıyı test et
            if not self.web3.is_connected():
                print("❌ Ganache bağlantısı kurulamadı!")
                return False
            
            print(f"✅ Ganache'e bağlandı: {self.web3_url}")
            print(f"📦 Block Number: {self.web3.eth.block_number}")
            print(f"🆔 Chain ID: {self.web3.eth.chain_id}")
            
            # Contract ABI'larını yükle
            self.load_contract_abis()
            return True
            
        except Exception as e:
            print(f"❌ Contract initialization hatası: {e}")
            return False
    
    def load_contract_abis(self):
        """Contract ABI'larını artifacts'ten yükle"""
        try:
            # Path'leri current working directory'ye göre ayarla
            import os
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # PDM System ABI
            pdm_abi_path = os.path.join(base_path, 'artifacts', 'contracts', 'PdMSystem.sol', 'PdMSystem.json')
            with open(pdm_abi_path, 'r') as f:
                pdm_artifact = json.load(f)
                pdm_abi = pdm_artifact['abi']
                
            self.pdm_contract = self.web3.eth.contract(
                address=self.pdm_system_address,
                abi=pdm_abi
            )
            
            # Groth16 Verifier ABI  
            verifier_abi_path = os.path.join(base_path, 'artifacts', 'contracts', 'PDMVerifier.sol', 'Groth16Verifier.json')
            with open(verifier_abi_path, 'r') as f:
                verifier_artifact = json.load(f)
                verifier_abi = verifier_artifact['abi']
                
            self.verifier_contract = self.web3.eth.contract(
                address=self.groth16_verifier_address,
                abi=verifier_abi
            )
            
            print("✅ Contract ABI'ları yüklendi")
            return True
            
        except Exception as e:
            print(f"❌ ABI yükleme hatası: {e}")
            print("ℹ️ Artifacts klasörü kontrol ediliyor...")
            return False
    
    def submit_sensor_data(self, data_commitment, metadata_hash, machine_id, account='worker'):
        """Sensor data'yı blockchain'e gönder"""
        try:
            if not self.pdm_contract:
                print("❌ PDM contract yüklenmemiş!")
                return None
            
            # Account seç
            from_account = self.accounts[account]['address']
            
            # Transaction build et
            txn = self.pdm_contract.functions.submitSensorData(
                data_commitment,
                metadata_hash,
                machine_id,
                1  # Role.WORKER minimum access
            ).build_transaction({
                'from': from_account,
                'gas': 300000,
                'gasPrice': self.web3.to_wei('20', 'gwei'),
                'nonce': self.web3.eth.get_transaction_count(from_account)
            })
            
            print(f"🔄 Sensor data transaction hazırlandı...")
            print(f"📍 Machine ID: {machine_id}")
            print(f"👤 From: {from_account}")
            print(f"⛽ Gas: {txn['gas']}")
            
            return txn
            
        except Exception as e:
            print(f"❌ Sensor data transaction hatası: {e}")
            return None
    
    def record_prediction(self, prediction_data, account='engineer'):
        """Model prediction'ını blockchain'e kaydet"""
        try:
            # Prediction data'yı hash'le
            prediction_str = json.dumps(prediction_data, sort_keys=True)
            data_commitment = self.web3.keccak(text=prediction_str)
            
            # Metadata oluştur
            metadata = {
                'timestamp': int(time.time()),
                'model_type': 'GRU-CNN',
                'prediction_prob': prediction_data.get('probability', 0),
                'risk_level': prediction_data.get('risk_level', 'LOW'),
                'features_count': prediction_data.get('features_count', 0)
            }
            metadata_str = json.dumps(metadata, sort_keys=True)
            metadata_hash = self.web3.keccak(text=metadata_str)
            
            # Machine ID (prediction case'e göre unique)
            machine_id = prediction_data.get('machine_id', int(time.time()) % 10000)
            
            # Transaction oluştur
            txn = self.submit_sensor_data(
                data_commitment, 
                metadata_hash, 
                machine_id, 
                account
            )
            
            if txn:
                print(f"✅ Prediction kaydı hazır - Machine ID: {machine_id}")
                return txn, {
                    'data_commitment': data_commitment.hex(),
                    'metadata_hash': metadata_hash.hex(),
                    'machine_id': machine_id,
                    'metadata': metadata
                }
            
            return None, None
            
        except Exception as e:
            print(f"❌ Prediction kayıt hatası: {e}")
            return None, None
    
    def get_account_balance(self, account_name):
        """Hesap bakiyesini göster"""
        try:
            if account_name in self.accounts:
                address = self.accounts[account_name]['address']
                balance_wei = self.web3.eth.get_balance(address)
                balance_eth = self.web3.from_wei(balance_wei, 'ether')
                return float(balance_eth)
            return 0
        except:
            return 0
    
    def get_system_stats(self):
        """Blockchain sistem istatistikleri"""
        try:
            if not self.pdm_contract:
                return None
            
            stats = {
                'block_number': self.web3.eth.block_number,
                'total_users': self.pdm_contract.functions.totalUsers().call(),
                'engineer_count': self.pdm_contract.functions.engineerCount().call(),
                'data_counter': self.pdm_contract.functions.dataCounter().call(),
                'model_counter': self.pdm_contract.functions.modelCounter().call(),
                'admin_balance': self.get_account_balance('admin'),
                'engineer_balance': self.get_account_balance('engineer'),
                'worker_balance': self.get_account_balance('worker')
            }
            
            return stats
            
        except Exception as e:
            print(f"❌ Stats alınamadı: {e}")
            return None
    
    def simulate_transaction(self, txn_data):
        """Transaction'ı simüle et (Ganache'de direkt göndermeden test)"""
        try:
            print("\n🎯 TRANSACTION SİMÜLASYONU")
            print("="*50)
            print(f"📍 Contract: {txn_data['to']}")
            print(f"👤 From: {txn_data['from']}")
            print(f"⛽ Gas: {txn_data['gas']}")
            print(f"💰 Gas Price: {txn_data['gasPrice']} wei")
            print(f"🆔 Nonce: {txn_data['nonce']}")
            print("="*50)
            
            # Gas estimation
            estimated_gas = self.web3.eth.estimate_gas(txn_data)
            print(f"📊 Estimated Gas: {estimated_gas}")
            
            # Gas cost hesabı
            estimated_cost_wei = estimated_gas * txn_data['gasPrice']
            estimated_cost_eth = self.web3.from_wei(estimated_cost_wei, 'ether')
            
            result = {
                'gas_estimate': estimated_gas,
                'estimated_cost_wei': estimated_cost_wei,
                'estimated_cost_eth': float(estimated_cost_eth),
                'is_valid': estimated_gas <= txn_data['gas']
            }
            
            if result['is_valid']:
                print("✅ Transaction geçerli ve gönderilebilir!")
            else:
                print("⚠️ Gas limiti yetersiz!")
                
            return result
                
        except Exception as e:
            print(f"❌ Transaction simülasyon hatası: {e}")
            return None

    def send_transaction(self, txn_data, account='engineer'):
        """Transaction'ı gerçekten Ganache'e gönder"""
        try:
            print("\n🚀 GERÇEK TRANSACTION GÖNDERİMİ")
            print("="*50)
            
            # Account private key al
            private_key = self.accounts[account]['private_key']
            print(f"🔑 Private key alındı: {private_key[:10]}...")
            
            # Transaction'ı imzala
            print(f"✍️ Transaction imzalanıyor...")
            signed_txn = self.web3.eth.account.sign_transaction(txn_data, private_key)
            print(f"✅ Transaction imzalandı")
            
            # Transaction'ı gönder
            print(f"📡 Ganache'e gönderiliyor...")
            # Web3.py version uyumluluğu için rawTransaction yerine raw_transaction
            raw_tx = getattr(signed_txn, 'raw_transaction', getattr(signed_txn, 'rawTransaction', None))
            tx_hash = self.web3.eth.send_raw_transaction(raw_tx)
            print(f"🔗 Transaction Hash: {tx_hash.hex()}")
            
            # Receipt'i bekle
            print(f"⏳ Transaction confirmation bekleniyor...")
            tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            
            print("="*50)
            print(f"✅ TRANSACTION BAŞARILI!")
            print(f"📦 Block Number: {tx_receipt.blockNumber}")
            print(f"🏷️ Transaction Index: {tx_receipt.transactionIndex}")
            print(f"⛽ Gas Used: {tx_receipt.gasUsed}")
            print(f"💰 Status: {'SUCCESS' if tx_receipt.status == 1 else 'FAILED'}")
            print("="*50)
            
            return {
                'tx_hash': tx_hash.hex(),
                'block_number': tx_receipt.blockNumber,
                'gas_used': tx_receipt.gasUsed,
                'status': tx_receipt.status,
                'receipt': tx_receipt
            }
            
        except Exception as e:
            print(f"❌ Transaction gönderim hatası: {e}")
            import traceback
            traceback.print_exc()
            return None

    def record_and_send_prediction(self, prediction_data, account='engineer'):
        """Model prediction'ını blockchain'e kaydet ve gerçekten gönder"""
        try:
            print(f"🔄 Transaction oluşturuluyor...")
            
            # Transaction oluştur
            txn, metadata = self.record_prediction(prediction_data, account)
            
            if txn and metadata:
                print(f"✅ Transaction hazırlandı, şimdi gönderiliyor...")
                
                # Gerçek transaction gönder
                result = self.send_transaction(txn, account)
                
                if result:
                    print(f"🎯 Prediction başarıyla blockchain'e kaydedildi!")
                    return result, metadata
                else:
                    print(f"❌ Transaction gönderim başarısız!")
                    return None, None
            else:
                print(f"❌ Transaction oluşturulamadı!")
                return None, None
            
        except Exception as e:
            print(f"❌ Prediction kayıt ve gönderim hatası: {e}")
            import traceback
            traceback.print_exc()
            return None, None

# Global instance
ganache_integration = None

def initialize_ganache_integration():
    """Ganache entegrasyonunu başlat"""
    global ganache_integration
    try:
        ganache_integration = GanacheBlockchainIntegration()
        return ganache_integration.initialize_contracts()
    except Exception as e:
        print(f"❌ Ganache integration başlatılamadı: {e}")
        return False

def get_ganache_integration():
    """Ganache integration instance'ını al"""
    global ganache_integration
    if ganache_integration is None:
        initialize_ganache_integration()
    return ganache_integration 