#!/usr/bin/env python3
"""
Yeni Event Test - Ganache'de yeni event oluşturup monitoring test eder
"""

import sys
import os
sys.path.append('bc')

from blockchain_integration import GanacheBlockchainIntegration
import time

def test_new_event():
    """Yeni event oluştur ve test et"""
    
    print("🧪 YENİ EVENT TEST BAŞLADI")
    print("=" * 40)
    
    # Blockchain integration başlat
    blockchain = GanacheBlockchainIntegration()
    
    if not blockchain.pdm_contract:
        print("❌ Contract bağlantısı yok!")
        return False
    
    # Test prediction data
    test_prediction = {
        'machine_id': int(time.time()) % 10000,
        'probability': 0.789,
        'risk_level': 'HIGH',
        'features_count': 24,
        'model_accuracy': 95.4,
        'timestamp': int(time.time())
    }
    
    print(f"📊 Test Prediction Data:")
    print(f"   Machine ID: {test_prediction['machine_id']}")
    print(f"   Risk Level: {test_prediction['risk_level']}")
    print(f"   Probability: {test_prediction['probability']}")
    
    try:
        # Transaction oluştur ve gönder
        result = blockchain.record_and_send_prediction(test_prediction, 'engineer')
        
        if result:
            print("✅ Event başarıyla oluşturuldu!")
            print(f"📦 Transaction Hash: {result.get('transaction_hash', 'N/A')}")
            print(f"🆔 Block Number: {result.get('block_number', 'N/A')}")
            
            # Event detaylarını yazdır
            if 'event_details' in result:
                details = result['event_details']
                print(f"\n🎪 EVENT DETAYLARI:")
                print(f"   Data Commitment: {details['data_commitment']}")
                print(f"   Machine ID: {details['machine_id']}")
                print(f"   Metadata Hash: {details['metadata_hash']}")
            
            return True
        else:
            print("❌ Event oluşturulamadı!")
            return False
    
    except Exception as e:
        print(f"❌ Test hatası: {e}")
        return False

def main():
    """Ana test fonksiyonu"""
    print("🎛️ EVENT TEST MENÜSÜ")
    print("1. Yeni event oluştur")
    print("2. Event debug analizi")
    
    choice = input("\nSeçiminiz (1/2): ").strip()
    
    if choice == "1":
        success = test_new_event()
        if success:
            print("\n✅ Test başarılı! Şimdi Ganache GUI'de kontrol edin:")
            print("   - Transactions sekmesi → Son transaction → Event Logs")
            print("   - Logs sekmesi → Contract filter")
    elif choice == "2":
        import subprocess
        subprocess.run(["python", "debug_events.py"])
    else:
        print("Geçersiz seçim!")

if __name__ == "__main__":
    main() 