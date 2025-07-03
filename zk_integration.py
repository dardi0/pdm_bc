"""
Zero-Knowledge Predictive Maintenance Integration
IPFS yerine ZK teknolojisi kullanarak veri gizliliği sağlar
"""

import json
import hashlib
import numpy as np
from web3 import Web3
from eth_account import Account
import joblib
import pickle
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import os
import subprocess
from pathlib import Path

class ZKPredictiveMaintenance:
    def __init__(self, web3_provider_url: str, contract_address: str, 
                 zk_verifier_address: str, private_key: str):
        """
        ZK tabanlı Predictive Maintenance sistemi
        
        Args:
            web3_provider_url: Ethereum node URL
            contract_address: ZKPredictiveMaintenance contract adresi
            zk_verifier_address: ZKVerifier contract adresi
            private_key: İşlem yapacak cüzdanın private key'i
        """
        # Web3 setup
        self.w3 = Web3(Web3.HTTPProvider(web3_provider_url))
        if not self.w3.is_connected():
            raise ConnectionError("Ethereum node'a bağlanılamadı!")
        
        # Account setup
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        
        # Contract setup
        self.contract_address = Web3.to_checksum_address(contract_address)
        self.zk_verifier_address = Web3.to_checksum_address(zk_verifier_address)
        
        # Load contract ABIs (simplified)
        self.contract_abi = self._load_contract_abi()
        self.verifier_abi = self._load_verifier_abi()
        
        # Contract instances
        self.contract = self.w3.eth.contract(
            address=self.contract_address,
            abi=self.contract_abi
        )
        self.verifier = self.w3.eth.contract(
            address=self.zk_verifier_address,
            abi=self.verifier_abi
        )
        
        # ZK setup
        self.circuits_path = Path("circuits/")
        self.circuits_path.mkdir(exist_ok=True)
        
        # Local data storage
        self.local_data = {}
        self.commitments = {}
        
        print(f"🔐 ZK Predictive Maintenance sistemi başlatıldı")
        print(f"📍 Contract: {self.contract_address}")
        print(f"🔒 ZK Verifier: {self.zk_verifier_address}")
        print(f"👤 Address: {self.address}")
        print(f"💰 Balance: {self.w3.from_wei(self.w3.eth.get_balance(self.address), 'ether')} ETH")
    
    def _load_contract_abi(self) -> List:
        """Contract ABI'sini yükler"""
        return [
            {
                "inputs": [
                    {"name": "_modelCommitment", "type": "bytes32"},
                    {"name": "_modelType", "type": "string"},
                    {"name": "_domainType", "type": "string"},
                    {"name": "_claimedAccuracy", "type": "uint256"},
                    {"name": "_claimedRmse", "type": "uint256"},
                    {"name": "_zkProofId", "type": "uint256"}
                ],
                "name": "registerZKModel",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "_dataCommitment", "type": "bytes32"},
                    {"name": "_machineType", "type": "string"},
                    {"name": "_dataCount", "type": "uint256"},
                    {"name": "_metadataHash", "type": "bytes32"},
                    {"name": "_zkProofId", "type": "uint256"}
                ],
                "name": "submitZKSensorData",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }
        ]
    
    def _load_verifier_abi(self) -> List:
        """ZK Verifier ABI'sini yükler"""
        return [
            {
                "inputs": [
                    {"name": "_modelCommitment", "type": "bytes32"},
                    {"name": "_a_acc", "type": "uint256[2]"},
                    {"name": "_b_acc", "type": "uint256[2][2]"},
                    {"name": "_c_acc", "type": "uint256[2]"},
                    {"name": "_inputs_acc", "type": "uint256[]"},
                    {"name": "_a_rmse", "type": "uint256[2]"},
                    {"name": "_b_rmse", "type": "uint256[2][2]"},
                    {"name": "_c_rmse", "type": "uint256[2]"},
                    {"name": "_inputs_rmse", "type": "uint256[]"}
                ],
                "name": "submitModelProof",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }
        ]
    
    # === COMMITMENT FUNCTIONS ===
    def generate_commitment(self, data: Any, nonce: int = None) -> Tuple[bytes, int]:
        """
        Veri için ZK commitment oluşturur
        
        Args:
            data: Commit edilecek veri
            nonce: Random nonce (opsiyonel)
            
        Returns:
            (commitment_bytes, nonce)
        """
        if nonce is None:
            nonce = int.from_bytes(os.urandom(32), 'big')
        
        # Veriyi serialize et
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        elif hasattr(data, 'get_weights'):  # TensorFlow model
            # Model weights'ini hash'le
            weights = data.get_weights()
            weight_bytes = pickle.dumps(weights)
            data_str = hashlib.sha256(weight_bytes).hexdigest()
        else:
            data_str = str(data)
        
        # Commitment = hash(data || nonce)
        commitment = hashlib.sha256(
            data_str.encode() + nonce.to_bytes(32, 'big')
        ).digest()
        
        return commitment, nonce
    
    def store_data_locally(self, data: Any, commitment: bytes) -> str:
        """
        Veriyi local olarak saklar
        
        Args:
            data: Saklanacak veri
            commitment: Veri commitment'ı
            
        Returns:
            Storage path
        """
        commitment_hex = commitment.hex()
        storage_path = f"local_storage/{commitment_hex[:16]}.pkl"
        
        os.makedirs("local_storage", exist_ok=True)
        
        with open(storage_path, 'wb') as f:
            pickle.dump(data, f)
        
        self.local_data[commitment_hex] = storage_path
        return storage_path
    
    def load_data_locally(self, commitment: bytes) -> Any:
        """
        Local'den veriyi yükler
        
        Args:
            commitment: Veri commitment'ı
            
        Returns:
            Yüklenen veri
        """
        commitment_hex = commitment.hex()
        if commitment_hex not in self.local_data:
            raise ValueError(f"Commitment bulunamadı: {commitment_hex}")
        
        storage_path = self.local_data[commitment_hex]
        
        with open(storage_path, 'rb') as f:
            return pickle.load(f)
    
    # === ZK PROOF GENERATION ===
    def generate_model_proof(self, model, accuracy: float, rmse: float) -> Dict:
        """
        Model için ZK proof oluşturur
        
        Args:
            model: TensorFlow/Keras modeli
            accuracy: Model accuracy
            rmse: Model RMSE
            
        Returns:
            ZK proof dictionary
        """
        try:
            # Model commitment oluştur
            commitment, nonce = self.generate_commitment(model)
            commitment_hex = f"0x{commitment.hex()}"
            
            # Model'i local'de sakla
            self.store_data_locally(model, commitment)
            
            # Circom circuit ile proof oluştur (simplified)
            proof_data = self._generate_circom_proof(
                "model_accuracy",
                {
                    "model_commitment": commitment_hex,
                    "accuracy": int(accuracy * 10000),
                    "rmse": int(rmse * 10000),
                    "nonce": nonce
                }
            )
            
            return {
                "commitment": commitment_hex,
                "nonce": nonce,
                "accuracy_proof": proof_data["accuracy_proof"],
                "rmse_proof": proof_data["rmse_proof"],
                "public_inputs": proof_data["public_inputs"]
            }
            
        except Exception as e:
            print(f"❌ Model proof oluşturma hatası: {e}")
            return None
    
    def generate_sensor_proof(self, sensor_data: Dict) -> Dict:
        """
        Sensor data için ZK proof oluşturur
        
        Args:
            sensor_data: Sensor verileri
            
        Returns:
            ZK proof dictionary
        """
        try:
            # Data commitment oluştur
            commitment, nonce = self.generate_commitment(sensor_data)
            commitment_hex = f"0x{commitment.hex()}"
            
            # Veriyi local'de sakla
            self.store_data_locally(sensor_data, commitment)
            
            # Metadata hash (public bilgiler)
            metadata = {
                "timestamp": sensor_data.get("timestamp", datetime.now().isoformat()),
                "machine_type": sensor_data.get("machine_type", "M"),
                "data_count": len(sensor_data)
            }
            metadata_hash = hashlib.sha256(
                json.dumps(metadata, sort_keys=True).encode()
            ).digest()
            
            # Circom proof oluştur
            proof_data = self._generate_circom_proof(
                "sensor_validity",
                {
                    "data_commitment": commitment_hex,
                    "air_temp": int(sensor_data.get("air_temperature", 298.1) * 100),
                    "process_temp": int(sensor_data.get("process_temperature", 308.6) * 100),
                    "rotational_speed": sensor_data.get("rotational_speed", 1551),
                    "torque": int(sensor_data.get("torque", 42.8) * 100),
                    "tool_wear": sensor_data.get("tool_wear", 0),
                    "nonce": nonce
                }
            )
            
            return {
                "commitment": commitment_hex,
                "nonce": nonce,
                "metadata_hash": f"0x{metadata_hash.hex()}",
                "validity_proof": proof_data["validity_proof"],
                "range_proof": proof_data["range_proof"],
                "public_inputs": proof_data["public_inputs"]
            }
            
        except Exception as e:
            print(f"❌ Sensor proof oluşturma hatası: {e}")
            return None
    
    def generate_prediction_proof(self, input_data: Dict, prediction_result: Dict, 
                                model_commitment: str) -> Dict:
        """
        Prediction için ZK proof oluşturur
        
        Args:
            input_data: Input sensor data
            prediction_result: Prediction sonuçları
            model_commitment: Kullanılan model commitment'ı
            
        Returns:
            ZK proof dictionary
        """
        try:
            # Input ve output commitment'ları oluştur
            input_commitment, input_nonce = self.generate_commitment(input_data)
            output_commitment, output_nonce = self.generate_commitment(prediction_result)
            
            input_commitment_hex = f"0x{input_commitment.hex()}"
            output_commitment_hex = f"0x{output_commitment.hex()}"
            
            # Veriyi local'de sakla
            self.store_data_locally(input_data, input_commitment)
            self.store_data_locally(prediction_result, output_commitment)
            
            # Circom proof oluştur
            proof_data = self._generate_circom_proof(
                "prediction_computation",
                {
                    "input_commitment": input_commitment_hex,
                    "output_commitment": output_commitment_hex,
                    "model_commitment": model_commitment,
                    "rul_prediction": prediction_result.get("rul", 1000),
                    "failure_probability": int(prediction_result.get("failure_probability", 0.1) * 10000),
                    "input_nonce": input_nonce,
                    "output_nonce": output_nonce
                }
            )
            
            return {
                "input_commitment": input_commitment_hex,
                "output_commitment": output_commitment_hex,
                "input_nonce": input_nonce,
                "output_nonce": output_nonce,
                "computation_proof": proof_data["computation_proof"],
                "consistency_proof": proof_data["consistency_proof"],
                "public_inputs": proof_data["public_inputs"]
            }
            
        except Exception as e:
            print(f"❌ Prediction proof oluşturma hatası: {e}")
            return None
    
    def _generate_circom_proof(self, circuit_type: str, inputs: Dict) -> Dict:
        """
        Circom circuit ile ZK proof oluşturur (simplified implementation)
        
        Args:
            circuit_type: Circuit tipi
            inputs: Circuit input'ları
            
        Returns:
            Proof data
        """
        # Bu basit bir implementasyon - gerçekte circom ve snarkjs kullanılır
        # Örnek: circomlib kullanarak gerçek ZK proof oluşturma
        
        # Fake proof generation for demo
        fake_proof = {
            "accuracy_proof": {
                "a": [123456, 789012],
                "b": [[111111, 222222], [333333, 444444]],
                "c": [555555, 666666],
                "inputs": [inputs.get("accuracy", 9000)]
            },
            "rmse_proof": {
                "a": [777777, 888888],
                "b": [[999999, 101010], [121212, 131313]],
                "c": [141414, 151515],
                "inputs": [inputs.get("rmse", 1000)]
            },
            "validity_proof": {
                "a": [161616, 171717],
                "b": [[181818, 191919], [202020, 212121]],
                "c": [222222, 232323],
                "inputs": [1]  # Valid data flag
            },
            "range_proof": {
                "a": [242424, 252525],
                "b": [[262626, 272727], [282828, 292929]],
                "c": [303030, 313131],
                "inputs": [1]  # In range flag
            },
            "computation_proof": {
                "a": [323232, 333333],
                "b": [[343434, 353535], [363636, 373737]],
                "c": [383838, 393939],
                "inputs": [inputs.get("rul_prediction", 1000)]
            },
            "consistency_proof": {
                "a": [404040, 414141],
                "b": [[424242, 434343], [444444, 454545]],
                "c": [464646, 474747],
                "inputs": [1]  # Consistent flag
            },
            "public_inputs": [1, 2, 3]  # Public inputs
        }
        
        return fake_proof
    
    # === BLOCKCHAIN INTEGRATION ===
    def register_model_on_blockchain(self, model, model_type: str, domain_type: str,
                                   accuracy: float, rmse: float) -> Optional[int]:
        """
        Modeli ZK proof ile blockchain'e kaydeder
        
        Args:
            model: TensorFlow model
            model_type: Model tipi
            domain_type: Domain tipi
            accuracy: Model accuracy
            rmse: Model RMSE
            
        Returns:
            Model ID veya None
        """
        try:
            # 1. ZK proof oluştur
            proof_data = self.generate_model_proof(model, accuracy, rmse)
            if not proof_data:
                return None
            
            # 2. ZK Verifier'a proof submit et
            zk_proof_id = self._submit_model_proof_to_verifier(proof_data)
            if zk_proof_id is None:
                return None
            
            # 3. Ana contract'a model kaydet
            model_id = self._register_model_in_contract(
                proof_data["commitment"],
                model_type,
                domain_type,
                int(accuracy * 10000),
                int(rmse * 10000),
                zk_proof_id
            )
            
            if model_id is not None:
                print(f"✅ Model blockchain'e kaydedildi: ID {model_id}")
                self.commitments[proof_data["commitment"]] = {
                    "type": "model",
                    "data": model,
                    "nonce": proof_data["nonce"]
                }
            
            return model_id
            
        except Exception as e:
            print(f"❌ Model kayıt hatası: {e}")
            return None
    
    def submit_sensor_data_to_blockchain(self, sensor_data: Dict) -> Optional[int]:
        """
        Sensor verisini ZK proof ile blockchain'e gönderir
        
        Args:
            sensor_data: Sensor verileri
            
        Returns:
            Data ID veya None
        """
        try:
            # 1. ZK proof oluştur
            proof_data = self.generate_sensor_proof(sensor_data)
            if not proof_data:
                return None
            
            # 2. ZK Verifier'a proof submit et
            zk_proof_id = self._submit_sensor_proof_to_verifier(proof_data)
            if zk_proof_id is None:
                return None
            
            # 3. Ana contract'a data kaydet
            data_id = self._submit_sensor_data_to_contract(
                proof_data["commitment"],
                sensor_data.get("machine_type", "M"),
                len(sensor_data),
                proof_data["metadata_hash"],
                zk_proof_id
            )
            
            if data_id is not None:
                print(f"✅ Sensor data blockchain'e kaydedildi: ID {data_id}")
                self.commitments[proof_data["commitment"]] = {
                    "type": "sensor",
                    "data": sensor_data,
                    "nonce": proof_data["nonce"]
                }
            
            return data_id
            
        except Exception as e:
            print(f"❌ Sensor data kayıt hatası: {e}")
            return None
    
    def make_prediction_on_blockchain(self, model_id: int, sensor_data_id: int,
                                    input_data: Dict, prediction_result: Dict,
                                    confidence_score: int) -> Optional[int]:
        """
        Prediction'ı ZK proof ile blockchain'e kaydeder
        
        Args:
            model_id: Kullanılan model ID
            sensor_data_id: Kullanılan sensor data ID
            input_data: Input verileri
            prediction_result: Prediction sonuçları
            confidence_score: Güven skoru (0-10000)
            
        Returns:
            Prediction ID veya None
        """
        try:
            # Model commitment'ını al
            model_commitment = self._get_model_commitment(model_id)
            if not model_commitment:
                return None
            
            # 1. ZK proof oluştur
            proof_data = self.generate_prediction_proof(
                input_data, prediction_result, model_commitment
            )
            if not proof_data:
                return None
            
            # 2. ZK Verifier'a proof submit et
            zk_proof_id = self._submit_prediction_proof_to_verifier(proof_data)
            if zk_proof_id is None:
                return None
            
            # 3. Ana contract'a prediction kaydet
            prediction_id = self._make_prediction_in_contract(
                model_id,
                sensor_data_id,
                proof_data["input_commitment"],
                proof_data["output_commitment"],
                confidence_score,
                zk_proof_id
            )
            
            if prediction_id is not None:
                print(f"✅ Prediction blockchain'e kaydedildi: ID {prediction_id}")
            
            return prediction_id
            
        except Exception as e:
            print(f"❌ Prediction kayıt hatası: {e}")
            return None
    
    # === INTERNAL BLOCKCHAIN FUNCTIONS ===
    def _submit_model_proof_to_verifier(self, proof_data: Dict) -> Optional[int]:
        """ZK Verifier'a model proof submit eder"""
        try:
            # Transaction build
            function = self.verifier.functions.submitModelProof(
                proof_data["commitment"],
                proof_data["accuracy_proof"]["a"],
                proof_data["accuracy_proof"]["b"],
                proof_data["accuracy_proof"]["c"],
                proof_data["accuracy_proof"]["inputs"],
                proof_data["rmse_proof"]["a"],
                proof_data["rmse_proof"]["b"],
                proof_data["rmse_proof"]["c"],
                proof_data["rmse_proof"]["inputs"]
            )
            
            tx_hash = self._send_transaction(function)
            if tx_hash:
                # Event'ten proof ID'sini çıkar
                return self._get_proof_id_from_tx(tx_hash)
            
        except Exception as e:
            print(f"❌ Model proof submit hatası: {e}")
            return None
    
    def _register_model_in_contract(self, commitment: str, model_type: str, 
                                  domain_type: str, accuracy: int, rmse: int,
                                  zk_proof_id: int) -> Optional[int]:
        """Ana contract'a model kaydeder"""
        try:
            function = self.contract.functions.registerZKModel(
                commitment,
                model_type,
                domain_type,
                accuracy,
                rmse,
                zk_proof_id
            )
            
            tx_hash = self._send_transaction(function)
            if tx_hash:
                return self._get_model_id_from_tx(tx_hash)
            
        except Exception as e:
            print(f"❌ Model contract kayıt hatası: {e}")
            return None
    
    def _send_transaction(self, function) -> Optional[str]:
        """Smart contract transaction gönderir"""
        try:
            # Gas estimation
            gas_estimate = function.estimate_gas({'from': self.address})
            
            # Transaction build
            transaction = function.build_transaction({
                'from': self.address,
                'gas': gas_estimate,
                'gasPrice': self.w3.to_wei('20', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(self.address),
            })
            
            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                return receipt.transactionHash.hex()
            else:
                print(f"❌ Transaction başarısız: {receipt}")
                return None
                
        except Exception as e:
            print(f"❌ Transaction hatası: {e}")
            return None
    
    def _get_proof_id_from_tx(self, tx_hash: str) -> Optional[int]:
        """Transaction'dan proof ID çıkarır"""
        # Simplified - gerçekte event logs parse edilir
        return int(tx_hash[-6:], 16) % 1000
    
    def _get_model_id_from_tx(self, tx_hash: str) -> Optional[int]:
        """Transaction'dan model ID çıkarır"""
        # Simplified - gerçekte event logs parse edilir
        return int(tx_hash[-8:], 16) % 10000
    
    # === UTILITY FUNCTIONS ===
    def get_system_stats(self) -> Dict:
        """Sistem istatistiklerini döndürür"""
        try:
            stats = self.contract.functions.getSystemStats().call()
            
            return {
                'total_models': stats[0],
                'total_sensor_data': stats[1],
                'total_predictions': stats[2],
                'active_models': stats[3],
                'total_participants': stats[4],
                'reward_pool': self.w3.from_wei(stats[5], 'ether'),
                'local_commitments': len(self.commitments)
            }
        except Exception as e:
            print(f"❌ Stats alma hatası: {e}")
            return {}
    
    def stake_for_training(self, amount_eth: float) -> bool:
        """Training için stake yatırır"""
        try:
            amount_wei = self.w3.to_wei(amount_eth, 'ether')
            
            transaction = self.contract.functions.depositTrainerStake().build_transaction({
                'from': self.address,
                'value': amount_wei,
                'gas': 100000,
                'gasPrice': self.w3.to_wei('20', 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(self.address),
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                print(f"✅ {amount_eth} ETH trainer stake yapıldı")
                return True
            else:
                print(f"❌ Stake işlemi başarısız")
                return False
                
        except Exception as e:
            print(f"❌ Stake hatası: {e}")
            return False
    
    def reveal_commitment(self, commitment: str, recipient: str = None) -> bool:
        """
        Commitment'ı reveal eder (opsiyonel - sadece yetkili kişilere)
        
        Args:
            commitment: Reveal edilecek commitment
            recipient: Veriyi alacak kişi (opsiyonel)
            
        Returns:
            Başarı durumu
        """
        try:
            if commitment not in self.commitments:
                print(f"❌ Commitment bulunamadı: {commitment}")
                return False
            
            commitment_data = self.commitments[commitment]
            
            if recipient:
                print(f"🔓 Commitment reveal edildi: {recipient} adresine")
                # Gerçek implementasyonda şifrelenmiş data transfer
            else:
                print(f"🔓 Commitment reveal edildi")
            
            return True
            
        except Exception as e:
            print(f"❌ Commitment reveal hatası: {e}")
            return False


# Örnek kullanım fonksiyonları
def integrate_zk_with_existing_pdm(model, sensor_data: Dict, prediction_result: Dict,
                                 zk_pdm: ZKPredictiveMaintenance) -> Dict:
    """
    Mevcut PDM sistemini ZK ile entegre eder
    
    Args:
        model: Eğitilmiş model
        sensor_data: Sensor verileri
        prediction_result: Prediction sonuçları
        zk_pdm: ZK PDM instance
        
    Returns:
        Entegrasyon sonuçları
    """
    results = {
        'model_id': None,
        'sensor_data_id': None,
        'prediction_id': None,
        'success': False
    }
    
    try:
        # 1. Modeli ZK ile kaydet
        model_id = zk_pdm.register_model_on_blockchain(
            model=model,
            model_type="LSTM-CNN",
            domain_type="industrial_machinery",
            accuracy=prediction_result.get('accuracy', 0.95),
            rmse=prediction_result.get('rmse', 0.1)
        )
        
        if model_id:
            results['model_id'] = model_id
            
            # 2. Sensor verisini ZK ile kaydet
            sensor_data_id = zk_pdm.submit_sensor_data_to_blockchain(sensor_data)
            
            if sensor_data_id:
                results['sensor_data_id'] = sensor_data_id
                
                # 3. Prediction'ı ZK ile kaydet
                prediction_id = zk_pdm.make_prediction_on_blockchain(
                    model_id=model_id,
                    sensor_data_id=sensor_data_id,
                    input_data=sensor_data,
                    prediction_result=prediction_result,
                    confidence_score=int(prediction_result.get('confidence', 8000))
                )
                
                if prediction_id:
                    results['prediction_id'] = prediction_id
                    results['success'] = True
    
    except Exception as e:
        print(f"❌ ZK entegrasyon hatası: {e}")
    
    return results


def setup_zk_config() -> Dict:
    """ZK konfigürasyonunu döndürür"""
    return {
        'web3_provider_url': 'http://127.0.0.1:7545',  # Ganache
        'contract_address': '0x...',  # ZKPredictiveMaintenance contract
        'zk_verifier_address': '0x...',  # ZKVerifier contract
        'private_key': '0x...'  # Cüzdan private key
    }


if __name__ == "__main__":
    # Test için örnek kullanım
    config = setup_zk_config()
    
    try:
        zk_pdm = ZKPredictiveMaintenance(
            web3_provider_url=config['web3_provider_url'],
            contract_address=config['contract_address'],
            zk_verifier_address=config['zk_verifier_address'],
            private_key=config['private_key']
        )
        
        # Sistem durumunu kontrol et
        stats = zk_pdm.get_system_stats()
        print(f"📊 ZK Sistem İstatistikleri: {stats}")
        
        # Training stake yap
        zk_pdm.stake_for_training(0.1)
        
    except Exception as e:
        print(f"❌ ZK bağlantı hatası: {e}")
        print("ℹ️ Ganache ve ZK contract'larının deploy edildiğinden emin olun") 