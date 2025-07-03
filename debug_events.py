#!/usr/bin/env python3
"""
Event Debugging Script - Ganache'de event'lerin neden görünmediğini analiz eder
"""

import json
from web3 import Web3
import sys
import os

def analyze_ganache_events():
    """Ganache'deki transaction'ları ve event'leri analiz et"""
    
    # Ganache bağlantısı
    web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:7545"))
    
    print("🔍 GANACHE EVENT ANALİZİ BAŞLADI")
    print("=" * 50)
    
    # Bağlantı kontrolü
    if not web3.is_connected():
        print("❌ Ganache'e bağlanılamadı!")
        return False
    
    print(f"✅ Ganache Bağlantısı: BAŞARILI")
    print(f"📦 Block Number: {web3.eth.block_number}")
    print(f"🆔 Chain ID: {web3.eth.chain_id}")
    print(f"🌐 Network ID: {web3.net.version}")
    print()
    
    # Contract adresleri
    PDM_ADDRESS = "0x3099510854Dd3165bdD07bea8410a7Bc0CcfD3fA"
    VERIFIER_ADDRESS = "0x98EA576277EBA3F203C61D194E6659B5C4b15377"
    
    # Contract ABI'sını yükle
    try:
        abi_path = os.path.join('artifacts', 'contracts', 'PdMSystem.sol', 'PdMSystem.json')
        with open(abi_path, 'r') as f:
            pdm_artifact = json.load(f)
            pdm_abi = pdm_artifact['abi']
        
        pdm_contract = web3.eth.contract(address=PDM_ADDRESS, abi=pdm_abi)
        print(f"✅ PDM Contract ABI yüklendi: {PDM_ADDRESS}")
    except Exception as e:
        print(f"❌ ABI yüklenemedi: {e}")
        return False
    
    # Son 20 block'u analiz et
    current_block = web3.eth.block_number
    start_block = max(0, current_block - 20)
    
    print(f"\n📊 BLOCK ANALİZİ ({start_block} - {current_block})")
    print("-" * 40)
    
    total_transactions = 0
    contract_transactions = 0
    event_count = 0
    
    for block_num in range(start_block, current_block + 1):
        try:
            block = web3.eth.get_block(block_num, full_transactions=True)
            
            if block.transactions:
                total_transactions += len(block.transactions)
                print(f"Block {block_num}: {len(block.transactions)} transaction(s)")
                
                for tx in block.transactions:
                    # Contract transaction'larını kontrol et
                    if tx['to'] and tx['to'].lower() == PDM_ADDRESS.lower():
                        contract_transactions += 1
                        print(f"  🎯 Contract TX: {tx['hash'].hex()}")
                        
                        # Transaction receipt'ini al
                        try:
                            receipt = web3.eth.get_transaction_receipt(tx['hash'])
                            print(f"    📋 Status: {'✅ SUCCESS' if receipt['status'] == 1 else '❌ FAILED'}")
                            print(f"    ⛽ Gas Used: {receipt['gasUsed']}")
                            print(f"    📝 Logs Count: {len(receipt['logs'])}")
                            
                            # Event'leri decode et
                            if receipt['logs']:
                                event_count += len(receipt['logs'])
                                print(f"    🎪 EVENTS FOUND:")
                                
                                for i, log in enumerate(receipt['logs']):
                                    print(f"      Event #{i+1}:")
                                    print(f"        Address: {log['address']}")
                                    print(f"        Topics: {[t.hex() for t in log['topics']]}")
                                    print(f"        Data: {log['data'].hex()}")
                                    
                                    # Event'i decode etmeye çalış
                                    try:
                                        decoded = pdm_contract.events.DataSubmitted().process_log(log)
                                        print(f"        🎉 DECODED DataSubmitted: {decoded['args']}")
                                    except:
                                        try:
                                            decoded = pdm_contract.events.UserRegistered().process_log(log)
                                            print(f"        👤 DECODED UserRegistered: {decoded['args']}")
                                        except:
                                            try:
                                                decoded = pdm_contract.events.StakeDeposited().process_log(log)
                                                print(f"        💰 DECODED StakeDeposited: {decoded['args']}")
                                            except:
                                                print(f"        ❓ UNKNOWN Event (couldn't decode)")
                            else:
                                print(f"    ⚠️ NO EVENTS in this transaction")
                        
                        except Exception as e:
                            print(f"    ❌ Receipt Error: {e}")
                        
                        print()
        
        except Exception as e:
            print(f"❌ Block {block_num} Error: {e}")
    
    print(f"\n📈 ÖZET RAPOR")
    print("=" * 30)
    print(f"📦 Analiz Edilen Block'lar: {start_block} - {current_block}")
    print(f"🔄 Toplam Transaction: {total_transactions}")
    print(f"🎯 Contract Transaction: {contract_transactions}")
    print(f"🎪 Toplam Event: {event_count}")
    
    # Ganache event filter test
    print(f"\n🔍 EVENT FILTER TESTİ")
    print("-" * 30)
    
    try:
        # Tüm DataSubmitted event'lerini getir
        data_filter = pdm_contract.events.DataSubmitted.create_filter(fromBlock=0)
        data_events = data_filter.get_all_entries()
        print(f"📊 DataSubmitted Events: {len(data_events)}")
        
        for event in data_events:
            print(f"  - Block {event['blockNumber']}: {event['args']}")
    
    except Exception as e:
        print(f"❌ Event Filter Error: {e}")
    
    # Ganache GUI için öneri
    print(f"\n💡 GANACHE GUI ÖNERİLERİ")
    print("-" * 30)
    print("1. Ganache GUI'de 'Logs' sekmesini kontrol edin")
    print("2. 'Events' sekmesi yerine 'Transactions' sekmesindeki detayları inceleyin") 
    print("3. Filter'ları temizleyin ve yeniden yükleyin")
    print("4. Ganache'i restart edip test edin")
    
    return True

if __name__ == "__main__":
    analyze_ganache_events() 