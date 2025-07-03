import warnings
import os
import logging

# Tüm warning'leri gizle
warnings.filterwarnings('ignore')

# TensorFlow warning'lerini gizle
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
logging.getLogger('tensorflow').setLevel(logging.ERROR)

# Scikit-learn deprecation warning'lerini gizle
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import time
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix
from imblearn.over_sampling import SMOTE
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Conv1D, MaxPooling1D, LSTM, GRU 
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.optimizers import Adam
import tkinter as tk
from tkinter import ttk, messagebox, font

# Ganache Blockchain entegrasyonu
try:
    from bc.blockchain_integration import initialize_ganache_integration, get_ganache_integration
    BLOCKCHAIN_AVAILABLE = True
    print("🔐 Ganache Blockchain modülü yüklendi")
except ImportError as e:
    BLOCKCHAIN_AVAILABLE = False
    print(f"⚠️ Ganache Blockchain modülü yüklenemedi: {e}")
    print("ℹ️ Web3 kütüphanesini kurmak için: pip install web3")

# TensorFlow için ek ayarlar
tf.get_logger().setLevel('ERROR')
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)

# Global değişkenler
model = None
scaler = None
feature_names = None
optimal_threshold = 0.5  # Cross validation ile hesaplanacak
zk_pdm = None  # ZK Blockchain instance

def setup_zk_blockchain():
    """ZK Blockchain bağlantısını kurar"""
    global zk_pdm
    
    if not BLOCKCHAIN_AVAILABLE:
        return False
    
    try:
        # ZK konfigürasyonu - Ganache bilgileriyle güncellendi
        config = {
            'web3_provider_url': 'http://127.0.0.1:7545',  # Ganache RPC Server
            'contract_address': '0x5f40aCfA7013E773013085f8062b3cA53Ec9291',  # İlk Ganache hesabı
            'zk_verifier_address': '0x446aab1d9877C91cd9C5BbC803718327E02A4590',  # İkinci Ganache hesabı
            'private_key': '0x' + '0'*63 + '1'  # Test için basit key
        }
        
        # ZK instance oluştur - Ganache bağlantısı
        print("🔐 ZK Blockchain bağlantısı test ediliyor...")
        
        # Önce basit Web3 bağlantısını test et
        from web3 import Web3
        try:
            w3 = Web3(Web3.HTTPProvider(config['web3_provider_url']))
            if w3.is_connected():
                print(f"✅ Ganache bağlantısı başarılı: {config['web3_provider_url']}")
                print(f"🆔 Chain ID: {w3.eth.chain_id}")
                print(f"📦 Block Number: {w3.eth.block_number}")
                accounts = w3.eth.accounts
                if accounts:
                    print(f"👤 Hesap Sayısı: {len(accounts)}")
                    print(f"💰 İlk hesap balance: {w3.from_wei(w3.eth.get_balance(accounts[0]), 'ether')} ETH")
                print("ℹ️ ZK entegrasyonu Ganache ile hazır!")
                return True
            else:
                print("❌ Ganache bağlantısı başarısız")
                return False
            
        except Exception as e:
            print(f"❌ Ganache bağlantı hatası: {e}")
            return False
        
    except Exception as e:
        print(f"⚠️ ZK Blockchain bağlantısı kurulamadı: {e}")
        return False

def create_gru_cnn_model(input_shape, learning_rate=0.0005):
    """GRU-CNN modelini oluşturur"""
    model = Sequential()
    
    # Tek CNN Katmanı
    model.add(Conv1D(filters=64, kernel_size=3, 
                     activation='leaky_relu', input_shape=input_shape, padding='same'))
    model.add(MaxPooling1D(pool_size=2))
    model.add(Dropout(0.3))
    
    # Tek GRU Katmanı (LSTM yerine)
    model.add(GRU(units=64, return_sequences=False))
    model.add(Dropout(0.4))
    
    # Dense Katmanlar
    model.add(Dense(16, activation='tanh'))
    model.add(Dropout(0.4))
    model.add(Dense(1, activation='sigmoid'))
    
    # Adam optimizer ile custom learning rate
    optimizer = Adam(learning_rate=learning_rate)
    
    # Modeli derle
    model.compile(
        optimizer=optimizer,
        loss='binary_crossentropy',
        metrics=['binary_accuracy']
    )
    
    return model

def train_model():
    """5-Fold Cross Validation ile GRU-CNN modelini eğitir"""
    global model, scaler, feature_names, optimal_threshold
    
    print("🔄 5-Fold Cross Validation ile GRU-CNN Model Eğitimi Başlıyor...")
    print("="*80)
    
    # Veri setini yükle
    df = pd.read_csv('ai4i2020.csv')
    
    # Özellik mühendisliği
    df_encoded = pd.get_dummies(df, columns=['Type'])
    
    # Hedef değişkeni ve özellikleri ayır
    X = df_encoded.drop(['UDI', 'Product ID', 'Machine failure', 'TWF', 'HDF', 'PWF', 'OSF', 'RNF'], axis=1)
    y = df_encoded['Machine failure']
    
    # Özellik isimlerini kaydet
    feature_names = X.columns.tolist()
    
    # Veriyi eğitim ve test setlerine ayır
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    
    # Özellikleri ölçeklendir
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 5-Fold Cross Validation
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    # Cross validation sonuçları
    cv_scores = {
        'accuracy': [],
        'precision': [],
        'recall': [],
        'f1': [],
        'auc': [],
        'accuracy_opt': [],
        'precision_opt': [],
        'recall_opt': [],
        'f1_opt': [],
        'optimal_threshold': []
    }
    
    fold_predictions = []
    fold_probabilities = []
    fold_true_labels = []
    
    print(f"📊 5-Fold Cross Validation Başlıyor...")
    total_start_time = time.time()
    
    for fold, (train_idx, val_idx) in enumerate(skf.split(X_train_scaled, y_train), 1):
        print(f"\n🔸 Fold {fold}/5 işleniyor...")
        fold_start_time = time.time()
        
        # Fold verilerini ayır
        X_fold_train, X_fold_val = X_train_scaled[train_idx], X_train_scaled[val_idx]
        y_fold_train, y_fold_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
        
        # SMOTE uygula (sadece eğitim setine)
        smote = SMOTE(random_state=42)
        X_fold_train_smote, y_fold_train_smote = smote.fit_resample(X_fold_train, y_fold_train)
        
        # Veriyi CNN/GRU için yeniden şekillendirme
        X_fold_train_reshaped = X_fold_train_smote.reshape(X_fold_train_smote.shape[0], X_fold_train_smote.shape[1], 1)
        X_fold_val_reshaped = X_fold_val.reshape(X_fold_val.shape[0], X_fold_val.shape[1], 1)
        
        # Model oluştur
        fold_model = create_gru_cnn_model((X_fold_train_smote.shape[1], 1))
        
        # Early stopping
        early_stopping = EarlyStopping(
            monitor='val_loss',
            patience=30,  # CV için daha kısa patience
            restore_best_weights=True,
            verbose=0
        )
        
        # Model eğitimi
        fold_model.fit(
            X_fold_train_reshaped,
            y_fold_train_smote,
            epochs=100,  # CV için daha az epoch
            batch_size=32,
            validation_data=(X_fold_val_reshaped, y_fold_val),
            callbacks=[early_stopping],
            verbose=0
        )
        
        # Fold tahmini
        y_fold_pred_prob = fold_model.predict(X_fold_val_reshaped, verbose=0)
        y_fold_pred = (y_fold_pred_prob > 0.5).astype("int32").flatten()
        
        # Optimal eşik bulma
        def find_optimal_threshold(y_true, y_prob):
            """F1-Score'u maksimize eden optimal eşiği bulur"""
            thresholds = np.arange(0.1, 0.9, 0.01)
            best_f1 = 0
            best_threshold = 0.5
            
            for threshold in thresholds:
                y_pred_temp = (y_prob.flatten() >= threshold).astype(int)
                try:
                    f1 = f1_score(y_true, y_pred_temp)
                    if f1 > best_f1:
                        best_f1 = f1
                        best_threshold = threshold
                except:
                    continue
            
            return best_threshold, best_f1
        
        # Optimal eşiği bul
        optimal_threshold, optimal_f1 = find_optimal_threshold(y_fold_val, y_fold_pred_prob)
        
        # Optimal eşikle tahmin
        y_fold_pred_opt = (y_fold_pred_prob.flatten() >= optimal_threshold).astype("int32")
        
        # Fold sonuçlarını kaydet
        fold_predictions.extend(y_fold_pred)
        fold_probabilities.extend(y_fold_pred_prob.flatten())
        fold_true_labels.extend(y_fold_val.values)
        
        # Fold performansı (0.5 eşiği)
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        
        fold_accuracy = accuracy_score(y_fold_val, y_fold_pred)
        fold_precision = precision_score(y_fold_val, y_fold_pred, zero_division=0)
        fold_recall = recall_score(y_fold_val, y_fold_pred, zero_division=0)
        fold_f1 = f1_score(y_fold_val, y_fold_pred, zero_division=0)
        fold_auc = roc_auc_score(y_fold_val, y_fold_pred_prob.flatten())
        
        # Fold performansı (Optimal eşiği)
        fold_accuracy_opt = accuracy_score(y_fold_val, y_fold_pred_opt)
        fold_precision_opt = precision_score(y_fold_val, y_fold_pred_opt, zero_division=0)
        fold_recall_opt = recall_score(y_fold_val, y_fold_pred_opt, zero_division=0)
        fold_f1_opt = f1_score(y_fold_val, y_fold_pred_opt, zero_division=0)
        
        # Sonuçları kaydet
        cv_scores['accuracy'].append(fold_accuracy)
        cv_scores['precision'].append(fold_precision)
        cv_scores['recall'].append(fold_recall)
        cv_scores['f1'].append(fold_f1)
        cv_scores['auc'].append(fold_auc)
        cv_scores['accuracy_opt'].append(fold_accuracy_opt)
        cv_scores['precision_opt'].append(fold_precision_opt)
        cv_scores['recall_opt'].append(fold_recall_opt)
        cv_scores['f1_opt'].append(fold_f1_opt)
        cv_scores['optimal_threshold'].append(optimal_threshold)
        
        fold_end_time = time.time()
        
        print(f"   ✅ Fold {fold} tamamlandı - Süre: {(fold_end_time - fold_start_time):.1f}s")
        print(f"   📈 0.5 Eşik → Accuracy: {fold_accuracy:.4f}, F1: {fold_f1:.4f}, AUC: {fold_auc:.4f}")
        print(f"   🎯 Optimal Eşik ({optimal_threshold:.2f}) → Accuracy: {fold_accuracy_opt:.4f}, F1: {fold_f1_opt:.4f}")
        print(f"   ⚡ F1 İyileşme: {((fold_f1_opt - fold_f1) / fold_f1 * 100):+.1f}%")
    
    total_end_time = time.time()
    
    # Cross Validation sonuçları
    print(f"\n{'='*80}")
    print(f"🎯 5-FOLD CROSS VALIDATION SONUÇLARI")
    print(f"{'='*80}")
    print(f"⏱️  Toplam CV Süresi: {(total_end_time - total_start_time)/60:.2f} dakika")
    
    # CV performans metrikleri tablosu (0.5 eşiği)
    print(f"\n📊 CROSS VALIDATION PERFORMANS METRİKLERİ (0.5 EŞİĞİ):")
    print(f"┌{'─'*20}┬{'─'*10}┬{'─'*10}┬{'─'*10}┬{'─'*10}┐")
    print(f"│ {'Metrik':<18} │ {'Ortalama':<8} │ {'Std':<8} │ {'Min':<8} │ {'Max':<8} │")
    print(f"├{'─'*20}┼{'─'*10}┼{'─'*10}┼{'─'*10}┼{'─'*10}┤")
    
    standard_metrics = ['accuracy', 'precision', 'recall', 'f1', 'auc']
    for metric_name in standard_metrics:
        scores = cv_scores[metric_name]
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        min_score = np.min(scores)
        max_score = np.max(scores)
        display_name = metric_name.capitalize().replace('Auc', 'AUC')
        
        print(f"│ {display_name:<18} │ {mean_score:<8.4f} │ {std_score:<8.4f} │ {min_score:<8.4f} │ {max_score:<8.4f} │")
    
    print(f"└{'─'*20}┴{'─'*10}┴{'─'*10}┴{'─'*10}┴{'─'*10}┘")
    
    # CV performans metrikleri tablosu (Optimal eşiği)
    print(f"\n🎯 CROSS VALIDATION PERFORMANS METRİKLERİ (OPTİMAL EŞİK):")
    print(f"┌{'─'*20}┬{'─'*10}┬{'─'*10}┬{'─'*10}┬{'─'*10}┐")
    print(f"│ {'Metrik':<18} │ {'Ortalama':<8} │ {'Std':<8} │ {'Min':<8} │ {'Max':<8} │")
    print(f"├{'─'*20}┼{'─'*10}┼{'─'*10}┼{'─'*10}┼{'─'*10}┤")
    
    optimal_metrics = ['accuracy_opt', 'precision_opt', 'recall_opt', 'f1_opt', 'optimal_threshold']
    for metric_name in optimal_metrics:
        scores = cv_scores[metric_name]
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        min_score = np.min(scores)
        max_score = np.max(scores)
        
        if metric_name == 'optimal_threshold':
            display_name = 'Optimal Threshold'
        else:
            display_name = metric_name.replace('_opt', '').capitalize()
        
        print(f"│ {display_name:<18} │ {mean_score:<8.4f} │ {std_score:<8.4f} │ {min_score:<8.4f} │ {max_score:<8.4f} │")
    
    print(f"└{'─'*20}┴{'─'*10}┴{'─'*10}┴{'─'*10}┴{'─'*10}┘")
    
    # İyileşme analizi
    f1_improvement = ((np.mean(cv_scores['f1_opt']) - np.mean(cv_scores['f1'])) / np.mean(cv_scores['f1'])) * 100
    print(f"\n⚡ OPTİMAL EŞİK İYİLEŞMESİ:")
    print(f"   • F1-Score İyileşme: %{f1_improvement:+.2f}")
    print(f"   • Ortalama Optimal Eşik: {np.mean(cv_scores['optimal_threshold']):.3f}")
    print(f"   • Eşik Standart Sapma: {np.std(cv_scores['optimal_threshold']):.3f}")
    
    # Her fold için detay (0.5 eşiği)
    print(f"\n📋 FOLD DETAYLARI (0.5 EŞİĞİ):")
    print(f"┌{'─'*6}┬{'─'*10}┬{'─'*10}┬{'─'*10}┬{'─'*10}┬{'─'*10}┐")
    print(f"│ {'Fold':<4} │ {'Accuracy':<8} │ {'Precision':<8} │ {'Recall':<8} │ {'F1':<8} │ {'AUC':<8} │")
    print(f"├{'─'*6}┼{'─'*10}┼{'─'*10}┼{'─'*10}┼{'─'*10}┼{'─'*10}┤")
    
    for i in range(5):
        print(f"│ {i+1:<4} │ {cv_scores['accuracy'][i]:<8.4f} │ {cv_scores['precision'][i]:<8.4f} │ {cv_scores['recall'][i]:<8.4f} │ {cv_scores['f1'][i]:<8.4f} │ {cv_scores['auc'][i]:<8.4f} │")
    
    print(f"└{'─'*6}┴{'─'*10}┴{'─'*10}┴{'─'*10}┴{'─'*10}┴{'─'*10}┘")
    
    # Her fold için detay (Optimal eşiği)
    print(f"\n🎯 FOLD DETAYLARI (OPTİMAL EŞİK):")
    print(f"┌{'─'*6}┬{'─'*10}┬{'─'*10}┬{'─'*10}┬{'─'*10}┬{'─'*10}┐")
    print(f"│ {'Fold':<4} │ {'Accuracy':<8} │ {'Precision':<8} │ {'Recall':<8} │ {'F1':<8} │ {'Eşik':<8} │")
    print(f"├{'─'*6}┼{'─'*10}┼{'─'*10}┼{'─'*10}┼{'─'*10}┼{'─'*10}┤")
    
    for i in range(5):
        print(f"│ {i+1:<4} │ {cv_scores['accuracy_opt'][i]:<8.4f} │ {cv_scores['precision_opt'][i]:<8.4f} │ {cv_scores['recall_opt'][i]:<8.4f} │ {cv_scores['f1_opt'][i]:<8.4f} │ {cv_scores['optimal_threshold'][i]:<8.3f} │")
    
    print(f"└{'─'*6}┴{'─'*10}┴{'─'*10}┴{'─'*10}┴{'─'*10}┴{'─'*10}┘")
    
    # Nihai model eğitimi (tüm eğitim verisiyle)
    print(f"\n🚀 Nihai Model Eğitimi (Tüm Eğitim Verisiyle)...")
    final_start_time = time.time()
    
    # SMOTE uygula
    smote = SMOTE(random_state=42)
    X_train_smote, y_train_smote = smote.fit_resample(X_train_scaled, y_train)
    
    # Veriyi CNN/LSTM için yeniden şekillendirme
    X_train_reshaped = X_train_smote.reshape(X_train_smote.shape[0], X_train_smote.shape[1], 1)
    X_test_reshaped = X_test_scaled.reshape(X_test_scaled.shape[0], X_test_scaled.shape[1], 1)
    
    # Nihai model oluştur
    model = create_gru_cnn_model((X_train_smote.shape[1], 1))
    
    # Early stopping
    early_stopping = EarlyStopping(
        monitor='val_loss',
        patience=60,
        restore_best_weights=True
    )
    
    # Nihai model eğitimi
    history = model.fit(
        X_train_reshaped,
        y_train_smote,
        epochs=500,
        batch_size=32,
        validation_split=0.2,
        callbacks=[early_stopping],
        verbose=1
    )
    
    final_end_time = time.time()
    
    # Test performansı
    y_pred_prob = model.predict(X_test_reshaped, verbose=0)
    y_pred = (y_pred_prob > 0.5).astype("int32")
    
    # Nihai model için optimal eşik hesapla (CV ortalaması)
    optimal_threshold = np.mean(cv_scores['optimal_threshold'])
    y_pred_opt = (y_pred_prob.flatten() >= optimal_threshold).astype("int32")
    
    # Detaylı performans metrikleri (0.5 eşiği)
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
    
    test_accuracy = accuracy_score(y_test, y_pred.flatten())
    test_precision = precision_score(y_test, y_pred.flatten(), zero_division=0)
    test_recall = recall_score(y_test, y_pred.flatten(), zero_division=0)
    test_f1 = f1_score(y_test, y_pred.flatten(), zero_division=0)
    test_auc = roc_auc_score(y_test, y_pred_prob.flatten())
    
    # Detaylı performans metrikleri (Optimal eşiği)
    test_accuracy_opt = accuracy_score(y_test, y_pred_opt)
    test_precision_opt = precision_score(y_test, y_pred_opt, zero_division=0)
    test_recall_opt = recall_score(y_test, y_pred_opt, zero_division=0)
    test_f1_opt = f1_score(y_test, y_pred_opt, zero_division=0)
    
    # Confusion Matrix
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(y_test, y_pred.flatten())
    tn, fp, fn, tp = cm.ravel()
    
    print(f"\n🎯 NİHAİ MODEL TEST PERFORMANSI (0.5 EŞİĞİ):")
    print(f"┌{'─'*25}┬{'─'*10}┬{'─'*10}┬{'─'*15}┐")
    print(f"│ {'Metrik':<23} │ {'Test':<8} │ {'CV Ort.':<8} │ {'Fark':<13} │")
    print(f"├{'─'*25}┼{'─'*10}┼{'─'*10}┼{'─'*15}┤")
    print(f"│ {'Doğruluk (Accuracy)':<23} │ {test_accuracy:<8.4f} │ {np.mean(cv_scores['accuracy']):<8.4f} │ {test_accuracy - np.mean(cv_scores['accuracy']):+8.4f} │")
    print(f"│ {'Kesinlik (Precision)':<23} │ {test_precision:<8.4f} │ {np.mean(cv_scores['precision']):<8.4f} │ {test_precision - np.mean(cv_scores['precision']):+8.4f} │")
    print(f"│ {'Duyarlılık (Recall)':<23} │ {test_recall:<8.4f} │ {np.mean(cv_scores['recall']):<8.4f} │ {test_recall - np.mean(cv_scores['recall']):+8.4f} │")
    print(f"│ {'F1-Score':<23} │ {test_f1:<8.4f} │ {np.mean(cv_scores['f1']):<8.4f} │ {test_f1 - np.mean(cv_scores['f1']):+8.4f} │")
    print(f"│ {'AUC-ROC':<23} │ {test_auc:<8.4f} │ {np.mean(cv_scores['auc']):<8.4f} │ {test_auc - np.mean(cv_scores['auc']):+8.4f} │")
    print(f"└{'─'*25}┴{'─'*10}┴{'─'*10}┴{'─'*15}┘")
    
    print(f"\n🚀 NİHAİ MODEL TEST PERFORMANSI (OPTİMAL EŞİK: {optimal_threshold:.3f}):")
    print(f"┌{'─'*25}┬{'─'*10}┬{'─'*10}┬{'─'*15}┐")
    print(f"│ {'Metrik':<23} │ {'Test':<8} │ {'CV Ort.':<8} │ {'Fark':<13} │")
    print(f"├{'─'*25}┼{'─'*10}┼{'─'*10}┼{'─'*15}┤")
    print(f"│ {'Doğruluk (Accuracy)':<23} │ {test_accuracy_opt:<8.4f} │ {np.mean(cv_scores['accuracy_opt']):<8.4f} │ {test_accuracy_opt - np.mean(cv_scores['accuracy_opt']):+8.4f} │")
    print(f"│ {'Kesinlik (Precision)':<23} │ {test_precision_opt:<8.4f} │ {np.mean(cv_scores['precision_opt']):<8.4f} │ {test_precision_opt - np.mean(cv_scores['precision_opt']):+8.4f} │")
    print(f"│ {'Duyarlılık (Recall)':<23} │ {test_recall_opt:<8.4f} │ {np.mean(cv_scores['recall_opt']):<8.4f} │ {test_recall_opt - np.mean(cv_scores['recall_opt']):+8.4f} │")
    print(f"│ {'F1-Score':<23} │ {test_f1_opt:<8.4f} │ {np.mean(cv_scores['f1_opt']):<8.4f} │ {test_f1_opt - np.mean(cv_scores['f1_opt']):+8.4f} │")
    print(f"│ {'AUC-ROC':<23} │ {test_auc:<8.4f} │ {np.mean(cv_scores['auc']):<8.4f} │ {test_auc - np.mean(cv_scores['auc']):+8.4f} │")
    print(f"└{'─'*25}┴{'─'*10}┴{'─'*10}┴{'─'*15}┘")
    
    # Optimal eşik iyileşme analizi
    test_f1_improvement = ((test_f1_opt - test_f1) / test_f1) * 100
    print(f"\n⚡ TEST SETİ OPTİMAL EŞİK İYİLEŞMESİ:")
    print(f"   • F1-Score İyileşme: %{test_f1_improvement:+.2f}")
    print(f"   • Recall İyileşme: %{((test_recall_opt - test_recall) / test_recall * 100):+.2f}")
    print(f"   • Precision Değişim: %{((test_precision_opt - test_precision) / test_precision * 100):+.2f}")
    
    # Confusion Matrix tablosu
    print(f"\n🔍 TEST SETİ CONFUSION MATRIX:")
    print(f"┌{'─'*20}┬{'─'*12}┬{'─'*12}┐")
    header_text = "Tahmin \\ Gerçek"
    print(f"│ {header_text:<18} │ {'Normal':<10} │ {'Arızalı':<10} │")
    print(f"├{'─'*20}┼{'─'*12}┼{'─'*12}┤")
    print(f"│ {'Arıza Yok (0)':<18} │ {tn:<10,} │ {fp:<10,} │")
    print(f"│ {'Arıza Var (1)':<18} │ {fn:<10,} │ {tp:<10,} │")
    print(f"└{'─'*20}┴{'─'*12}┴{'─'*12}┘")
    
    print(f"\n⏱️  Toplam Eğitim Süresi: {(final_end_time - total_start_time)/60:.2f} dakika")
    print(f"{'='*80}")
    
    # Görselleştirmeler - Her grafik ayrı ayrı
    plt.style.use('default')
    
    # 1. Training/Validation Loss Grafikleri
    _, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Loss grafiği
    epochs_range = range(1, len(history.history['loss']) + 1)
    ax1.plot(epochs_range, history.history['loss'], 'b-', linewidth=2, label='Training Loss')
    ax1.plot(epochs_range, history.history['val_loss'], 'r-', linewidth=2, label='Validation Loss')
    ax1.set_title('Model Loss Grafikleri', fontweight='bold', fontsize=14, pad=20)
    ax1.set_xlabel('Epoch', fontweight='bold', fontsize=12)
    ax1.set_ylabel('Loss', fontweight='bold', fontsize=12)
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    
    # Accuracy grafiği
    ax2.plot(epochs_range, history.history['binary_accuracy'], 'b-', linewidth=2, label='Training Accuracy')
    ax2.plot(epochs_range, history.history['val_binary_accuracy'], 'r-', linewidth=2, label='Validation Accuracy')
    ax2.set_title('Model Accuracy Grafikleri', fontweight='bold', fontsize=14, pad=20)
    ax2.set_xlabel('Epoch', fontweight='bold', fontsize=12)
    ax2.set_ylabel('Accuracy', fontweight='bold', fontsize=12)
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    
    # Early stopping noktasını işaretle
    if len(history.history['loss']) < 200:
        stopped_epoch = len(history.history['loss'])
        ax1.axvline(x=stopped_epoch, color='green', linestyle='--', alpha=0.7, 
                   label=f'Early Stop (Epoch {stopped_epoch})')
        ax2.axvline(x=stopped_epoch, color='green', linestyle='--', alpha=0.7,
                   label=f'Early Stop (Epoch {stopped_epoch})')
        ax1.legend(fontsize=11)
        ax2.legend(fontsize=11)
    
    plt.tight_layout()
    plt.show()
    
    # 2. Fold Bazında Performans Trendi
    _, ax2 = plt.subplots(figsize=(12, 8))
    folds = range(1, 6)
    ax2.plot(folds, cv_scores['accuracy'], 'o-', label='Accuracy', linewidth=3, markersize=8, color='#E74C3C')  # Kırmızı
    ax2.plot(folds, cv_scores['f1'], 's-', label='F1-Score', linewidth=3, markersize=8, color='#3498DB')  # Mavi
    ax2.plot(folds, cv_scores['auc'], '^-', label='AUC', linewidth=3, markersize=8, color='#1ABC9C')  # Turkuaz
    ax2.plot(folds, cv_scores['precision'], 'd-', label='Precision', linewidth=3, markersize=8, color='#9B59B6')  # Mor
    ax2.plot(folds, cv_scores['recall'], 'v-', label='Recall', linewidth=3, markersize=8, color='#F39C12')  # Turuncu
    
    ax2.set_title('Fold Bazında Performans Trendi', fontweight='bold', fontsize=16, pad=20)
    ax2.set_xlabel('Fold Numarası', fontweight='bold', fontsize=14)
    ax2.set_ylabel('Skor', fontweight='bold', fontsize=14)
    ax2.legend(fontsize=12, loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(folds)
    ax2.set_ylim(0, 1)
    
    plt.tight_layout()
    plt.show()
    
    # 3. Test Seti Confusion Matrix
    _, ax3 = plt.subplots(figsize=(10, 8))
    cm_display = np.array([[tn, fp], [fn, tp]])
    

    
    # Hücre açıklamaları için özel annotasyon 
    cell_labels = np.array([
        [f'{tn}\n(True Negative)', 
         f'{fp}\n(False Positive)'],
        [f'{fn}\n(False Negative)', 
         f'{tp}\n(True Positive)']
    ])
    
    sns.heatmap(cm_display, annot=cell_labels, fmt='', cmap='Blues', 
                xticklabels=['Arıza Yok (0)', 'Arıza Var (1)'], 
                yticklabels=['Arıza Yok (0)', 'Arıza Var (1)'], ax=ax3, 
                cbar_kws={'label': 'Sayı'}, annot_kws={'size': 12, 'weight': 'bold'})
    ax3.set_title('Test Seti Confusion Matrix', fontweight='bold', fontsize=16, pad=20)
    ax3.set_xlabel('Gerçek Sınıf', fontweight='bold', fontsize=14)
    ax3.set_ylabel('Tahmin Edilen Sınıf', fontweight='bold', fontsize=14)
    
    plt.tight_layout()
    plt.show()
    
    # 4. CV vs Test Performans Karşılaştırması
    _, ax4 = plt.subplots(figsize=(12, 8))
    metrics = ['Accuracy', 'Precision', 'Recall', 'F1', 'AUC']
    cv_means = [np.mean(cv_scores['accuracy']), np.mean(cv_scores['precision']), 
                np.mean(cv_scores['recall']), np.mean(cv_scores['f1']), np.mean(cv_scores['auc'])]
    test_scores = [test_accuracy, test_precision, test_recall, test_f1, test_auc]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    ax4.bar(x - width/2, cv_means, width, label='CV Ortalama', alpha=0.8, color='#E67E22')  # Turuncu
    ax4.bar(x + width/2, test_scores, width, label='Test Sonucu', alpha=0.8, color='#2ECC71')  # Yeşil
    
    # Değerleri bar'ların üstüne yaz
    for i, (cv_val, test_val) in enumerate(zip(cv_means, test_scores)):
        ax4.text(i - width/2, cv_val + 0.01, f'{cv_val:.3f}', ha='center', va='bottom', fontweight='bold')
        ax4.text(i + width/2, test_val + 0.01, f'{test_val:.3f}', ha='center', va='bottom', fontweight='bold')
    
    ax4.set_title('Cross Validation vs Test Performansı', fontweight='bold', fontsize=16, pad=20)
    ax4.set_xlabel('Metrikler', fontweight='bold', fontsize=14)
    ax4.set_ylabel('Skor', fontweight='bold', fontsize=14)
    ax4.set_xticks(x)
    ax4.set_xticklabels(metrics)
    ax4.legend(fontsize=12)
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.set_ylim(0, 1)
    
    plt.tight_layout()
    plt.show()
    
    # 2. ROC Eğrisi
    from sklearn.metrics import roc_curve
    
    _, ax = plt.subplots(figsize=(8, 6))
    
    fpr, tpr, thresholds = roc_curve(y_test, y_pred_prob.flatten())
    
    ax.plot(fpr, tpr, color='#8E44AD', linewidth=3, label=f'ROC Eğrisi (AUC = {test_auc:.3f})')  # Mor
    ax.plot([0, 1], [0, 1], color='#95A5A6', linestyle='--', linewidth=2, label='Rastgele Sınıflandırma')  # Gri
    
    # Optimal threshold'u işaretle (Youden's J statistic)
    optimal_idx = np.argmax(tpr - fpr)
    optimal_threshold_roc = thresholds[optimal_idx]
    ax.scatter(fpr[optimal_idx], tpr[optimal_idx], color='red', s=100, zorder=5,
              label=f'Optimal Eşik ({optimal_threshold_roc:.3f})')
    
    # 0.5 eşiğini de işaretle
    threshold_05_idx = np.argmin(np.abs(thresholds - 0.5))
    ax.scatter(fpr[threshold_05_idx], tpr[threshold_05_idx], color='orange', s=100, zorder=5,
              label=f'0.5 Eşiği')
    
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel('False Positive Rate', fontsize=14, fontweight='bold')
    ax.set_ylabel('True Positive Rate', fontsize=14, fontweight='bold')
    ax.set_title('ROC Curve', fontsize=16, fontweight='bold')
    ax.legend(loc="lower right", fontsize=12)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()
    
    print(f"✅ 5-Fold Cross Validation ile Model Eğitimi Tamamlandı!")
    print(f"🖥️ GUI arayüzü başlatılıyor...")
    print(f"{'='*80}")
    
    return True

class PredictiveMaintenance:
    def __init__(self, root):
        self.root = root
        self.root.title("🔧 GRU-CNN Arıza Tespit Sistemi")
        self.root.geometry("1000x700")
        self.root.configure(bg='#f0f0f0')
        
        # Font ayarları
        self.title_font = font.Font(family="Arial", size=16, weight="bold")
        self.label_font = font.Font(family="Arial", size=10)
        self.button_font = font.Font(family="Arial", size=12, weight="bold")
        
        self.create_widgets()
        
    def create_widgets(self):
        # Ana başlık
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=80)
        title_frame.pack(fill='x', padx=0, pady=0)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, 
                              text="🔧 ARIZA TESPİT SİSTEMİ", 
                              font=self.title_font, 
                              bg='#2c3e50', 
                              fg='white')
        title_label.pack(expand=True)
        
        # Ana container
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Sol panel - Sensör girişleri
        left_frame = tk.LabelFrame(main_frame, 
                                  text="📊 SENSÖR VERİLERİ", 
                                  font=self.label_font, 
                                  bg='#ecf0f1', 
                                  padx=10, 
                                  pady=10)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Sensör giriş alanları
        self.create_sensor_inputs(left_frame)
        
        # Sağ panel - Sonuçlar
        right_frame = tk.LabelFrame(main_frame, 
                                   text="🎯 ARIZA TESPİT SONUÇLARI", 
                                   font=self.label_font, 
                                   bg='#ecf0f1', 
                                   padx=10, 
                                   pady=10)
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        # Sonuç alanları
        self.create_result_area(right_frame)
        
    def create_sensor_inputs(self, parent):
        # Sensör girişleri için ana frame
        main_input_frame = tk.Frame(parent, bg='#ecf0f1')
        main_input_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.sensor_vars = {}
        
        # İlk satır: Hava sıcaklığı, İşlem sıcaklığı, Dönme hızı
        row1_frame = tk.Frame(main_input_frame, bg='#ecf0f1')
        row1_frame.pack(fill='x', pady=5)
        
        row1_configs = [
            ("🌡️ Hava Sıcaklığı [K]", "Air temperature [K]", 298.1, (295, 305)),
            ("🔥 İşlem Sıcaklığı [K]", "Process temperature [K]", 308.6, (305, 315)),
            ("⚡ Dönme Hızı [rpm]", "Rotational speed [rpm]", 1551, (1000, 3000)),
        ]
        
        for i, (display_name, var_name, default_val, range_val) in enumerate(row1_configs):
            col_frame = tk.Frame(row1_frame, bg='#ecf0f1')
            col_frame.pack(side='left', fill='both', expand=True, padx=5)
            
            # Label
            label = tk.Label(col_frame, text=display_name, font=self.label_font, bg='#ecf0f1')
            label.pack()
            
            # Entry
            var = tk.DoubleVar(value=default_val)
            self.sensor_vars[var_name] = var
            
            entry = tk.Entry(col_frame, textvariable=var, font=self.label_font, width=12, justify='center')
            entry.pack(pady=2)
            
            range_label = tk.Label(col_frame, 
                                  text=f"({range_val[0]}-{range_val[1]})", 
                                  font=('Arial', 8), 
                                  bg='#ecf0f1', 
                                  fg='#7f8c8d')
            range_label.pack()
        
        # İkinci satır: Tork, Takım aşınması, Makine tipi
        row2_frame = tk.Frame(main_input_frame, bg='#ecf0f1')
        row2_frame.pack(fill='x', pady=15)
        
        # Tork
        tork_frame = tk.Frame(row2_frame, bg='#ecf0f1')
        tork_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        tork_label = tk.Label(tork_frame, text="🔧 Tork [Nm]", font=self.label_font, bg='#ecf0f1')
        tork_label.pack()
        
        tork_var = tk.DoubleVar(value=42.8)
        self.sensor_vars["Torque [Nm]"] = tork_var
        
        tork_entry = tk.Entry(tork_frame, textvariable=tork_var, font=self.label_font, width=12, justify='center')
        tork_entry.pack(pady=2)
        
        tork_range = tk.Label(tork_frame, text="(3-77)", font=('Arial', 8), bg='#ecf0f1', fg='#7f8c8d')
        tork_range.pack()
        
        # Takım aşınması
        wear_frame = tk.Frame(row2_frame, bg='#ecf0f1')
        wear_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        wear_label = tk.Label(wear_frame, text="⏱️ Takım Aşınması [dk]", font=self.label_font, bg='#ecf0f1')
        wear_label.pack()
        
        wear_var = tk.DoubleVar(value=0)
        self.sensor_vars["Tool wear [min]"] = wear_var
        
        wear_entry = tk.Entry(wear_frame, textvariable=wear_var, font=self.label_font, width=12, justify='center')
        wear_entry.pack(pady=2)
        
        wear_range = tk.Label(wear_frame, text="(0-300)", font=('Arial', 8), bg='#ecf0f1', fg='#7f8c8d')
        wear_range.pack()
        
        # Makine tipi
        type_frame = tk.Frame(row2_frame, bg='#ecf0f1')
        type_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        type_label = tk.Label(type_frame, text="🏭 Makine Tipi", font=self.label_font, bg='#ecf0f1')
        type_label.pack()
        
        self.machine_type = tk.StringVar(value="M")
        type_combo = ttk.Combobox(type_frame, textvariable=self.machine_type, 
                                 values=["L (Low - %50)", "M (Medium - %30)", "H (High - %20)"], 
                                 state="readonly", width=15, justify='center')
        type_combo.pack(pady=2)
        
        # Butonlar - yan yana
        button_frame = tk.Frame(main_input_frame, bg='#ecf0f1')
        button_frame.pack(fill='x', pady=20)
        
        predict_button = tk.Button(button_frame, 
                                  text="🔍 ARIZA ANALİZİ YAP", 
                                  command=self.predict_failure,
                                  font=self.button_font, 
                                  bg='#3498db', 
                                  fg='white', 
                                  height=2)
        predict_button.pack(side='left', fill='both', expand=True, padx=2)
        
        random_button = tk.Button(button_frame, 
                                 text="🎲 RASTGELE VERİ", 
                                 command=self.set_random_data,
                                 font=self.label_font, 
                                 bg='#95a5a6', 
                                 fg='white',
                                 height=2)
        random_button.pack(side='left', fill='both', expand=True, padx=2)
        
        reset_button = tk.Button(button_frame, 
                                text="🔄 SIFIRLA", 
                                command=self.reset_data,
                                font=self.label_font, 
                                bg='#e74c3c', 
                                fg='white',
                                height=2)
        reset_button.pack(side='left', fill='both', expand=True, padx=2)
        
        blockchain_button = tk.Button(button_frame, 
                                     text="🔗 BLOCKCHAIN", 
                                     command=self.show_blockchain_stats,
                                     font=self.label_font, 
                                     bg='#9C27B0', 
                                     fg='white',
                                     height=2)
        blockchain_button.pack(side='left', fill='both', expand=True, padx=2)
        
        # Ayırıcı çizgi
        separator = tk.Frame(main_input_frame, height=2, bg='#bdc3c7')
        separator.pack(fill='x', pady=20)
        
        # Arıza tipi analizi ve hesaplanan değerler alanı
        analysis_frame = tk.LabelFrame(main_input_frame, 
                                      text="🔍 ARıZA TİPİ ANALİZİ & HESAPLANAN DEĞERLER", 
                                      font=('Arial', 11, 'bold'), 
                                      bg='#ecf0f1')
        analysis_frame.pack(fill='both', expand=True, pady=10)
        
        self.analysis_result_frame = tk.Frame(analysis_frame, bg='#ecf0f1')
        self.analysis_result_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Başlangıç mesajı
        analysis_welcome = tk.Label(self.analysis_result_frame, 
                                   text="📊 Arıza analizi yaptıktan sonra burada detaylı bilgiler görünecek", 
                                   font=('Arial', 12, 'normal'), 
                                   bg='#ecf0f1', 
                                   fg='#7f8c8d')
        analysis_welcome.pack(expand=True)
        
    def create_result_area(self, parent):
        # Sonuç gösterimi
        self.result_frame = tk.Frame(parent, bg='#ecf0f1')
        self.result_frame.pack(fill='both', expand=True)
        
        # Başlangıç mesajı
        welcome_label = tk.Label(self.result_frame, 
                                text="👋 Arıza tespiti için sensör verilerini girin ve\n'ARIZA ANALİZİ YAP' butonuna tıklayın", 
                                font=self.label_font, 
                                bg='#ecf0f1', 
                                fg='#7f8c8d',
                                justify='center')
        welcome_label.pack(expand=True)
        
    def predict_failure(self):
        """Arıza tahminini yapar"""
        if model is None or scaler is None:
            messagebox.showerror("Hata", "Model henüz eğitilmedi!")
            return
            
        try:
            # Kullanıcı verilerini al
            user_data = []
            
            # Sensör verileri
            for feature in ['Air temperature [K]', 'Process temperature [K]', 
                           'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']:
                user_data.append(self.sensor_vars[feature].get())
            
            # Makine tipi one-hot encoding
            machine_type = self.machine_type.get()[0]  # L, M, H'den ilk harfi al
            user_data.extend([1 if machine_type == 'H' else 0,  # Type_H
                             1 if machine_type == 'L' else 0,   # Type_L  
                             1 if machine_type == 'M' else 0])  # Type_M
            
            # Veriyi numpy array'e çevir
            user_data = np.array(user_data).reshape(1, -1)
            
            # Veriyi ölçeklendir
            user_data_scaled = scaler.transform(user_data)
            
            # LSTM-CNN için yeniden şekillendir
            user_data_reshaped = user_data_scaled.reshape(1, user_data_scaled.shape[1], 1)
            
            # Model tahminini yap
            prediction_prob = model.predict(user_data_reshaped, verbose=0)[0][0]
            model_prediction_05 = 1 if prediction_prob > 0.5 else 0
            model_prediction_opt = 1 if prediction_prob > optimal_threshold else 0
            
            # Arıza tipi analizini yap
            failure_risks, power, temp_diff, overstrain_product, has_definite_failure = self.analyze_failure_type(user_data[0])
            
            # Nihai karar: Eğer arıza tipine uyuyorsa kesin arıza var
            if has_definite_failure:
                final_prediction = 1
                prediction_reason = "Arıza Tipi Kuralları"
            else:
                final_prediction = model_prediction_opt  # Optimal eşik kullan
                prediction_reason = f"LSTM-CNN Model (Optimal Eşik: {optimal_threshold:.2f})"
            
            # ZK Blockchain'e kaydet (eğer aktifse)
            self.record_prediction_to_zk(user_data[0], prediction_prob, final_prediction, prediction_reason)
            
            # Sonucu göster
            self.show_prediction_result(final_prediction, prediction_prob, user_data[0], prediction_reason, model_prediction_05, model_prediction_opt)
            
            # Arıza tipi analizini sol panelde göster
            self.show_failure_analysis(user_data[0])
            
        except Exception as e:
            messagebox.showerror("Hata", f"Tahmin hatası: {str(e)}")
    
    def record_prediction_to_zk(self, input_data, prediction_prob, final_prediction, prediction_reason):
        """Prediction'ı Ganache Blockchain'e kaydeder"""
        
        if not BLOCKCHAIN_AVAILABLE:
            print("⚠️ Blockchain entegrasyonu mevcut değil")
            return
        
        print("🔐 Ganache Blockchain kaydı başlıyor...")
        
        try:
            # Ganache integration'ı al
            ganache = get_ganache_integration()
            if not ganache:
                print("❌ Ganache bağlantısı kurulamadı")
                return
            
            # 1. Prediction data formatı
            prediction_data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "air_temperature": float(input_data[0]),
                "process_temperature": float(input_data[1]),
                "rotational_speed": int(input_data[2]),
                "torque": float(input_data[3]),
                "tool_wear": int(input_data[4]),
                "machine_type": self.machine_type.get()[0],
                "failure_probability": float(prediction_prob),
                "prediction": int(final_prediction),
                "model_type": "GRU-CNN",
                "prediction_reason": prediction_reason,
                "risk_level": "HIGH" if prediction_prob > 0.7 else "MEDIUM" if prediction_prob > 0.3 else "LOW",
                "features_count": len(input_data),
                "machine_id": int(time.time()) % 10000  # Unique machine ID
            }
            
            print("⛓️ Transaction oluşturuluyor ve Ganache'e gönderiliyor...")
            
            # 2. Blockchain transaction oluştur ve GERÇEKTEN GÖNDER
            tx_result, blockchain_data = ganache.record_and_send_prediction(prediction_data, 'engineer')
            
            if tx_result and blockchain_data:
                print("🎯 BAŞARI! Ganache Blockchain'e kaydedildi!")
                print(f"🔗 TX Hash: {tx_result['tx_hash']}")
                print(f"📦 Block Number: {tx_result['block_number']}")
                print(f"⛽ Gas Used: {tx_result['gas_used']}")
                print(f"💰 Status: {'SUCCESS' if tx_result['status'] == 1 else 'FAILED'}")
                print(f"📋 Machine ID: {blockchain_data['machine_id']}")
                print(f"🎯 Data Commitment: {blockchain_data['data_commitment'][:18]}...")
                print(f"🎯 Metadata Hash: {blockchain_data['metadata_hash'][:18]}...")
                print(f"📊 Probability: {prediction_prob:.4f}")
                print(f"🔒 Risk Level: {prediction_data['risk_level']}")
                print(f"📍 Contract: {ganache.pdm_system_address}")
                print("\n✅ Ganache GUI'de bu transaction'ı şimdi görebilirsiniz!")
                print(f"   TX Hash: {tx_result['tx_hash']}")
                print(f"   Block: {tx_result['block_number']}")
            else:
                print("❌ Transaction oluşturulamadı veya gönderilemedi")
                
        except Exception as e:
            print(f"❌ Blockchain kayıt hatası: {e}")
            print("⚠️ Blockchain kaydedilemedi - sadece local prediction yapıldı")
    
    def initialize_blockchain_system(self):
        """Ganache Blockchain sistemini başlatır"""
        if not BLOCKCHAIN_AVAILABLE:
            print("⚠️ Blockchain modülü mevcut değil")
            return False
            
        try:
            # Ganache integration'ı başlat
            success = initialize_ganache_integration()
            if success:
                print("✅ Ganache Blockchain sistemi başlatıldı")
                return True
            else:
                print("❌ Ganache bağlantısı kurulamadı")
                return False
                
        except Exception as e:
            print(f"❌ Blockchain başlatma hatası: {e}")
            return False
    
    # JSON log fonksiyonları kaldırıldı - Blockchain yeterli! 🔗
    def analyze_failure_type(self, input_data):
        """Girilen verilere göre potansiyel arıza tipini analiz eder"""
        import random
        
        air_temp = input_data[0]
        process_temp = input_data[1] 
        rotational_speed = input_data[2]
        torque = input_data[3]
        tool_wear = input_data[4]
        machine_type = self.machine_type.get()[0]
        
        failure_risks = []
        has_definite_failure = False  # Kesin arıza var mı?
        
        # TWF - Tool Wear Failure (200+ dakika kesin arıza)
        if tool_wear >= 200:
            failure_risks.append(f"🔧 TWF (Takım Aşınması): {tool_wear:.0f} dk - Kritik seviye aşıldı")
            has_definite_failure = True
        elif tool_wear >= 150:
            # 150-200 arası uyarı seviyesi ama arıza değil
            failure_risks.append(f"⚠️ TWF Riski: {tool_wear:.0f} dk - Yakın takip gerekli (200+ kritik)")
        
        # HDF - Heat Dissipation Failure  
        temp_diff = process_temp - air_temp
        if temp_diff < 8.6 and rotational_speed < 1380:
            failure_risks.append("🌡️ HDF (Isı Dağılımı): Sıcaklık farkı <8.6K ve hız <1380rpm")
            has_definite_failure = True
        
        # PWF - Power Failure
        power = torque * (rotational_speed * 2 * 3.14159 / 60)  # Watt hesabı
        if power < 3500 or power > 9000:
            failure_risks.append(f"⚡ PWF (Güç): Güç {power:.0f}W (3500-9000W dışında)")
            has_definite_failure = True
        
        # OSF - Overstrain Failure
        overstrain_product = tool_wear * torque
        overstrain_limits = {'L': 11000, 'M': 12000, 'H': 13000}
        limit = overstrain_limits.get(machine_type, 12000)
        if overstrain_product > limit:
            failure_risks.append(f"💪 OSF (Aşırı Yük): {overstrain_product:.0f} > {limit} minNm")
            has_definite_failure = True
        
        return failure_risks, power, temp_diff, overstrain_product, has_definite_failure
    
    def calculate_fuzzy_risk(self, probability):
        """Bulanık mantık ile risk seviyesi hesaplar"""
        if probability >= 0.8:
            return "ÇOK YÜKSEK", "#8B0000", "🔴"  # Koyu kırmızı
        elif probability >= 0.6:
            return "YÜKSEK", "#DC143C", "🟠"     # Kırmızı
        elif probability >= 0.4:
            return "ORTA", "#FF8C00", "🟡"       # Turuncu
        elif probability >= 0.2:
            return "DÜŞÜK", "#32CD32", "🟢"     # Yeşil
        elif probability >= 0.05:
            return "ÇOK DÜŞÜK", "#228B22", "🟢" # Koyu yeşil
        else:
            return "MİNİMAL", "#006400", "✅"    # En koyu yeşil
    
    def get_fuzzy_bar_value(self, fuzzy_risk):
        """Bulanık risk seviyesine göre progress bar değeri"""
        fuzzy_values = {
            "ÇOK YÜKSEK": 100,
            "YÜKSEK": 80,
            "ORTA": 60,
            "DÜŞÜK": 40,
            "ÇOK DÜŞÜK": 20,
            "MİNİMAL": 10
        }
        return fuzzy_values.get(fuzzy_risk, 50)
    
    def get_risk_description(self, fuzzy_risk):
        """Risk seviyesi açıklaması"""
        descriptions = {
            "ÇOK YÜKSEK": "🚨 Acil müdahale gerekebilir! Sistem durumu kritik.",
            "YÜKSEK": "⚠️ Yakın takip ve hızlı müdahale önerilir.",
            "ORTA": "🔍 Dikkatli izleme ve planlı bakım gerekli.",
            "DÜŞÜK": "👀 Düzenli kontrol yeterli, normal çalışma.",
            "ÇOK DÜŞÜK": "✨ Sistem stabil, rutin bakım planında.",
            "MİNİMAL": "💚 Mükemmel durum, arıza riski çok düşük."
        }
        return descriptions.get(fuzzy_risk, "Bilinmeyen risk seviyesi")
    
    def get_fuzzy_advice(self, prediction, fuzzy_risk, prediction_reason):
        """Bulanık risk seviyesine göre öneri"""
        if prediction == 1:  # Arıza tespit edildi
            if fuzzy_risk in ["ÇOK YÜKSEK", "YÜKSEK"]:
                return """
🚨 ACİL MÜDAHALE GEREKLİ
🔧 Makineyi derhal durdurun
⚠️ Güvenlik protokollerini uygulayın  
📞 Bakım ekibini acil arayın
🛠️ Arızalı parçaları değiştirin
🔍 Kök neden analizini yapın
                """.strip()
            elif fuzzy_risk == "ORTA":
                return """
⚠️ PLANLI MÜDAHALE ÖNERÍLÍR
🔧 En kısa sürede bakım planlayın
📋 Operasyon ekibini bilgilendirin
🛠️ Yedek parça tedarikini hazırlayın
📊 Parametreleri yakından izleyin
                """.strip()
            else:  # Fiziksel kural devrede, model düşük risk
                return """
🔍 DİKKATLİ TAKİP GEREKLİ
🔧 Fiziksel arıza belirtisi mevcut
📊 Model düşük risk, ama kurallar aktif
🛠️ Önleyici bakım düşünün
📅 Takip programı oluşturun
                """.strip()
        else:  # Arıza yok
            if fuzzy_risk in ["ÇOK DÜŞÜK", "MİNİMAL"]:
                return """
💚 SİSTEM MÜKEMMEL DURUMDA
✅ Normal operasyona devam edin
📅 Rutin bakım planını sürdürün
📊 Periyodik veri kontrolü yapın
🔄 Mevcut ayarları koruyun
                """.strip()
            elif fuzzy_risk == "DÜŞÜK":
                return """
✅ SİSTEM NORMAL ÇALIŞIYOR
📊 Düzenli izleme yapın
📅 Planlı bakımları aksatmayın
🔍 Haftalık kontrolleri sürdürün
                """.strip()
            else:  # ORTA risk ama arıza yok
                return """
👀 DİKKATLİ İZLEME ÖNERİLİR
📊 Parametreleri yakından takip edin
🔧 Önleyici bakım düşünün
📋 Veri trendlerini analiz edin
⚠️ Eşik değerleri gözden geçirin
                """.strip()
    
    def show_failure_analysis(self, input_data):
        """Sol panelde arıza tipi analizini gösterir"""
        # Önceki analiz sonuçlarını temizle
        for widget in self.analysis_result_frame.winfo_children():
            widget.destroy()
        
        # Arıza tipi analizini yap
        failure_risks, power, temp_diff, overstrain_product, has_definite_failure = self.analyze_failure_type(input_data)
        
        # Kesin arıza durumu kontrolü
        definite_failures = [risk for risk in failure_risks if "Kritik seviye aşıldı" in risk or "HDF" in risk or "PWF" in risk or "OSF" in risk]
        warning_risks = [risk for risk in failure_risks if "TWF Riski" in risk]
        
        # Arıza tipi analizi
        if len(definite_failures) > 0:
            risk_text = "⚠️ Tespit Edilen Arıza Tipi:\n\n"
            for risk in definite_failures:
                risk_text += f"• {risk}\n"
        else:
            risk_text = "✅ Belirgin arıza tipi tespit edilmedi\n• Tüm parametreler normal aralıkta."
        
        risk_label = tk.Label(self.analysis_result_frame, 
                             text=risk_text, 
                             font=('Arial', 12, 'normal'), 
                             bg='#ecf0f1', 
                             justify='left',
                             wraplength=500)
        risk_label.pack(anchor='w', pady=(0, 15))
        
        # Risk uyarıları (TWF vs gibi) - eğer varsa
        if len(warning_risks) > 0:
            warning_text = "🔍 Risk Analizi:\n\n"
            for warning in warning_risks:
                warning_text += f"• {warning}\n"
            
            warning_label = tk.Label(self.analysis_result_frame, 
                                   text=warning_text, 
                                   font=('Arial', 12, 'normal'), 
                                   bg='#ecf0f1', 
                                   fg='#E67E22',  # Turuncu renk
                                   justify='left',
                                   wraplength=500)
            warning_label.pack(anchor='w', pady=(0, 15))
        
        # Hesaplanan değerler
        machine_type = self.machine_type.get()[0]
        overstrain_limits = {'L': 11000, 'M': 12000, 'H': 13000}
        limit = overstrain_limits.get(machine_type, 12000)
        
        calc_text = f"""📊 Hesaplanan Değerler:
        
⚡ Güç: {power:.0f} W (Normal: 3500-9000W)
🌡️ Sıcaklık Farkı: {temp_diff:.1f} K (Kritik: <8.6K)  
💪 Aşırı Yük: {overstrain_product:.0f} minNm (Limit: {limit:,})"""
        
        calc_label = tk.Label(self.analysis_result_frame, 
                             text=calc_text, 
                             font=('Arial', 12, 'normal'), 
                             bg='#ecf0f1', 
                             justify='left')
        calc_label.pack(anchor='w')
    
    def show_prediction_result(self, prediction, probability, input_data, prediction_reason, model_prediction_05, model_prediction_opt):
        """Tahmin sonuçlarını gösterir"""
        # Önceki sonuçları temizle
        for widget in self.result_frame.winfo_children():
            widget.destroy()
        
        # Arıza tipi analizini yap
        failure_risks, power, temp_diff, overstrain_product, has_definite_failure = self.analyze_failure_type(input_data)
        
        # Ana sonuç container
        result_container = tk.Frame(self.result_frame, bg='#ecf0f1')
        result_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Sonuç başlığı
        if prediction == 1:
            result_color = '#e74c3c'  # Kırmızı
            result_text = " ARIZA TESPİTİ!"
            result_icon = "🚨"
        else:
            result_color = '#27ae60'  # Yeşil
            result_text = "ARIZA YOK!"
            result_icon = "✅"
        
        # Büyük sonuç etiketi
        result_label = tk.Label(result_container, 
                               text=f"{result_icon} {result_text}", 
                               font=('Arial', 18, 'bold'), 
                               bg=result_color, 
                               fg='white', 
                               pady=20)
        result_label.pack(fill='x', pady=(0, 20))
        
        # Arıza durumuna göre farklı analiz
        if prediction == 1:  # ARIZA TESPİT EDİLDİ
            # Sadece kontrol uyarısı, risk yüzdesi yok
            control_frame = tk.Frame(result_container, bg='#ecf0f1')
            control_frame.pack(fill='x', pady=10)
            
            control_text = """🔍 ARIZA TESPİTİ KONTROL EDİLMELİ
            
📋 Tespit edilen arıza kontrol sonrası aksiyon belirlenecektir:
• Kontrol yapın ve gerçek durumu belirleyin
• Eğer arıza varsa → Onarım/değişim yapın  
• Eğer arıza yoksa → Hiçbir aksiyon gerekmez
• Düşük riskli kontrol süreci"""
            
            control_label = tk.Label(control_frame, 
                                   text=control_text, 
                                   font=('Arial', 12), 
                                   fg='#2c3e50',
                                   bg='#ecf0f1',
                                   justify='left')
            control_label.pack(pady=10)
            
        else:  # ARIZA YOK - Yakınlık analizi göster
            # Arızaya yakınlık analizi
            proximity_frame = tk.Frame(result_container, bg='#ecf0f1')
            proximity_frame.pack(fill='x', pady=10)
            
            # Yakınlık yüzdesi
            proximity_percent = probability * 100
            
            proximity_title = tk.Label(proximity_frame, 
                                     text="📊 ARIZA YAKINLIK ANALİZİ", 
                                     font=('Arial', 14, 'bold'), 
                                     fg='#2980b9',
                                     bg='#ecf0f1')
            proximity_title.pack(pady=(0, 10))
            
            # Yakınlık bilgileri
            proximity_info = f"""🎯 Arızaya Yakınlık: %{proximity_percent:.1f}
⚖️ Arıza Eşiği: %{optimal_threshold*100:.1f}"""
            
            proximity_label = tk.Label(proximity_frame, 
                                     text=proximity_info, 
                                     font=('Arial', 12), 
                                     fg='#2c3e50',
                                     bg='#ecf0f1',
                                     justify='left')
            proximity_label.pack()
            
            # Yakınlık gösterge çubuğu
            proximity_bar = ttk.Progressbar(proximity_frame, length=300, mode='determinate')
            proximity_bar['value'] = proximity_percent
            proximity_bar.pack(pady=10)
            
            # Yakınlık seviyesine göre öneri
            if proximity_percent > 30:
                warning_color = '#e67e22'  # Turuncu
                warning_text = "⚠️ ARIZA EŞİĞİNE YAKLAŞIYORSUNUZ\n🔧 Planlı bakım düşünün - önleyici aksiyon önerilir"
            elif proximity_percent > 20:
                warning_color = '#f39c12'  # Sarı
                warning_text = "👀 NORMAL İZLEME SEVİYESİ\n📅 Haftalık kontrol yeterli - rutin takip yapın"
            else:
                warning_color = '#27ae60'  # Yeşil
                warning_text = "💚 GÜVENLİ SEVİYE\n✅ Rutin bakım planında - endişe edilecek durum yok"
            
            warning_label = tk.Label(proximity_frame, 
                                   text=warning_text, 
                                   font=('Arial', 11, 'bold'), 
                                   fg=warning_color,
                                   bg='#ecf0f1',
                                   justify='center')
            warning_label.pack(pady=10)
        
        # Öneriler
        advice_frame = tk.LabelFrame(result_container, 
                                    text="💡 ÖNERİLER", 
                                    font=('Arial', 11, 'bold'), 
                                    bg='#ecf0f1')
        advice_frame.pack(fill='x', pady=20)
        
        # Öneriler arıza durumuna göre
        if prediction == 1:  # ARIZA TESPİT EDİLDİ - Kontrol odaklı öneriler
            advice_text = """
🔍 KONTROL SÜRECİ
🔧 Makineyi kontrol edin ve durumu belirleyin
📋 Kontrol sonrası uygun aksiyonu belirleyin
⚠️ Güvenlik protokollerini unutmayın
🛠️ Gerekirse teknik ekibi çağırın
📊 Kontrol sonuçlarını kaydedin
            """.strip()
        else:  # ARIZA YOK - Yakınlık odaklı öneriler
            proximity_percent = probability * 100
            if proximity_percent > 30:
                advice_text = """
⚠️ ÖNLEYİCİ BAKIM ÖNERİLİR
🔧 Planlı bakım zamanlaması yapın
📅 1-2 hafta içinde kontrol edin
🛠️ Yedek parça durumunu gözden geçirin
📊 Parametreleri daha sık izleyin
                """.strip()
            elif proximity_percent > 20:
                advice_text = """
👀 NORMAL İZLEME
📅 Haftalık rutin kontrolleri sürdürün
🔍 Trend analizini takip edin
📊 Veri kayıtlarını düzenli tutun
🛠️ Planlı bakım takvimini koruyun
                """.strip()
            else:
                advice_text = """
💚 MÜKEMMEL DURUM
✅ Normal operasyona devam edin
📅 Rutin bakım planını sürdürün
📊 Periyodik veri kontrolü yapın
🔄 Mevcut ayarları koruyun
                """.strip()
        
        advice_label = tk.Label(advice_frame, 
                               text=advice_text, 
                               font=('Arial', 12, 'normal'), 
                               bg='#ecf0f1', 
                               justify='left')
        advice_label.pack(anchor='w', padx=10, pady=10)
        

        
        # Giriş verilerinin özeti
        data_frame = tk.LabelFrame(result_container, 
                                  text="📋 GİRİLEN VERİLER", 
                                  font=('Arial', 11, 'bold'), 
                                  bg='#ecf0f1')
        data_frame.pack(fill='x', pady=10)
        
        data_text = f"""
🌡️ Hava Sıcaklığı: {input_data[0]:.1f} K
🔥 İşlem Sıcaklığı: {input_data[1]:.1f} K  
⚡ Dönme Hızı: {input_data[2]:.0f} rpm
🔧 Tork: {input_data[3]:.1f} Nm
⏱️ Takım Aşınması: {input_data[4]:.0f} dakika
🏭 Makine Tipi: {self.machine_type.get()}
        """.strip()
        
        data_label = tk.Label(data_frame, 
                             text=data_text, 
                             font=('Arial', 12, 'normal'), 
                             bg='#ecf0f1', 
                             justify='left')
        data_label.pack(anchor='w', padx=10, pady=10)
        
    def set_random_data(self):
        """Rastgele sensör verileri oluşturur"""
        # Tam rastgele değerler - veri setindeki min/max aralıkları
        self.sensor_vars['Air temperature [K]'].set(round(np.random.uniform(295, 305), 1))
        self.sensor_vars['Process temperature [K]'].set(round(np.random.uniform(305, 315), 1))
        self.sensor_vars['Rotational speed [rpm]'].set(round(np.random.uniform(1000, 3000), 0))
        self.sensor_vars['Torque [Nm]'].set(round(np.random.uniform(3, 77), 1))
        self.sensor_vars['Tool wear [min]'].set(round(np.random.uniform(0, 300), 0))
        
    def reset_data(self):
        """Verileri varsayılan değerlere sıfırlar"""
        self.sensor_vars['Air temperature [K]'].set(298.1)
        self.sensor_vars['Process temperature [K]'].set(308.6)
        self.sensor_vars['Rotational speed [rpm]'].set(1551)
        self.sensor_vars['Torque [Nm]'].set(42.8)
        self.sensor_vars['Tool wear [min]'].set(0)
        self.machine_type.set("M (Medium - %30)")
        
        # Sonuç alanını temizle
        for widget in self.result_frame.winfo_children():
            widget.destroy()
            
        welcome_label = tk.Label(self.result_frame, 
                                text="👋 Arıza tespiti için sensör verilerini girin ve\n'ARIZA ANALİZİ YAP' butonuna tıklayın", 
                                font=self.label_font, 
                                bg='#ecf0f1', 
                                fg='#7f8c8d',
                                justify='center')
        welcome_label.pack(expand=True)
        
        # Analiz alanını da temizle
        for widget in self.analysis_result_frame.winfo_children():
            widget.destroy()
            
        analysis_welcome = tk.Label(self.analysis_result_frame, 
                                   text="📊 Arıza analizi yaptıktan sonra burada detaylı bilgiler görünecek", 
                                   font=('Arial', 12, 'normal'), 
                                   bg='#ecf0f1', 
                                   fg='#7f8c8d')
        analysis_welcome.pack(expand=True)
    
    def show_blockchain_stats(self):
        """Ganache Blockchain istatistiklerini gösterir"""
        if not BLOCKCHAIN_AVAILABLE:
            messagebox.showinfo("Bilgi", "⚠️ Blockchain entegrasyonu mevcut değil!\n\nWeb3 kütüphanesini kurmak için:\npip install web3")
            return
            
        try:
            # Ganache integration'dan stats al
            ganache = get_ganache_integration()
            if not ganache:
                messagebox.showerror("Hata", "❌ Ganache bağlantısı kurulamadı!\n\nGanache'in çalıştığından emin olun.")
                return
            
            stats = ganache.get_system_stats()
            if not stats:
                messagebox.showerror("Hata", "❌ Blockchain istatistikleri alınamadı!")
                return
                
            # Popup pencere oluştur
            stats_window = tk.Toplevel(self.root)
            stats_window.title("🔗 Ganache Blockchain İstatistikleri")
            stats_window.geometry("650x550")
            stats_window.configure(bg='#2c3e50')
            
            # Başlık
            title_label = tk.Label(stats_window, 
                                  text="🔐 GANACHE BLOCKCHAIN İSTATİSTİKLERİ", 
                                  font=('Arial', 16, 'bold'), 
                                  bg='#2c3e50', 
                                  fg='white')
            title_label.pack(pady=20)
            
            # Network bilgileri
            network_frame = tk.LabelFrame(stats_window, 
                                        text="🌐 Network Bilgileri", 
                                        font=('Arial', 12, 'bold'), 
                                        bg='#34495e', 
                                        fg='white')
            network_frame.pack(fill='x', padx=20, pady=10)
            
            tk.Label(network_frame, 
                    text=f"📦 Block Number: {stats['block_number']}", 
                    font=('Arial', 10), bg='#34495e', fg='white').pack(anchor='w', padx=10, pady=2)
            
            tk.Label(network_frame, 
                    text=f"🌐 Network: Ganache (Local)", 
                    font=('Arial', 10), bg='#34495e', fg='white').pack(anchor='w', padx=10, pady=2)
            
            tk.Label(network_frame, 
                    text=f"📍 PDM Contract: {ganache.pdm_system_address}", 
                    font=('Arial', 10), bg='#34495e', fg='white').pack(anchor='w', padx=10, pady=2)
            
            tk.Label(network_frame, 
                    text=f"🔐 Verifier Contract: {ganache.groth16_verifier_address}", 
                    font=('Arial', 10), bg='#34495e', fg='white').pack(anchor='w', padx=10, pady=2)
            
            # PDM System istatistikleri
            pdm_frame = tk.LabelFrame(stats_window, 
                                    text="📊 PDM System İstatistikleri", 
                                    font=('Arial', 12, 'bold'), 
                                    bg='#34495e', 
                                    fg='white')
            pdm_frame.pack(fill='x', padx=20, pady=10)
            
            tk.Label(pdm_frame, 
                    text=f"👥 Toplam Kullanıcı: {stats['total_users']}", 
                    font=('Arial', 10), bg='#34495e', fg='white').pack(anchor='w', padx=10, pady=2)
            
            tk.Label(pdm_frame, 
                    text=f"👷 Mühendis Sayısı: {stats['engineer_count']}", 
                    font=('Arial', 10), bg='#34495e', fg='white').pack(anchor='w', padx=10, pady=2)
            
            tk.Label(pdm_frame, 
                    text=f"📊 Sensor Data Sayısı: {stats['data_counter']}", 
                    font=('Arial', 10), bg='#34495e', fg='white').pack(anchor='w', padx=10, pady=2)
            
            tk.Label(pdm_frame, 
                    text=f"🤖 Kayıtlı Model Sayısı: {stats['model_counter']}", 
                    font=('Arial', 10), bg='#34495e', fg='white').pack(anchor='w', padx=10, pady=2)
            
            # Account bilgileri
            accounts_frame = tk.LabelFrame(stats_window, 
                                         text="💰 Account Bakiyeleri", 
                                         font=('Arial', 12, 'bold'), 
                                         bg='#34495e', 
                                         fg='white')
            accounts_frame.pack(fill='x', padx=20, pady=10)
            
            tk.Label(accounts_frame, 
                    text=f"👤 Admin: {stats['admin_balance']:.4f} ETH", 
                    font=('Arial', 10), bg='#34495e', fg='white').pack(anchor='w', padx=10, pady=2)
            
            tk.Label(accounts_frame, 
                    text=f"👷 Engineer: {stats['engineer_balance']:.4f} ETH", 
                    font=('Arial', 10), bg='#34495e', fg='white').pack(anchor='w', padx=10, pady=2)
            
            tk.Label(accounts_frame, 
                    text=f"🔨 Worker: {stats['worker_balance']:.4f} ETH", 
                    font=('Arial', 10), bg='#34495e', fg='white').pack(anchor='w', padx=10, pady=2)
            
            # Prediction info
            info_frame = tk.LabelFrame(stats_window, 
                                     text="ℹ️ Prediction Bilgisi", 
                                     font=('Arial', 12, 'bold'), 
                                     bg='#34495e', 
                                     fg='white')
            info_frame.pack(fill='x', padx=20, pady=10)
            
            info_text = """💡 Her arıza tahmini yaptığınızda:
• Prediction data'sı blockchain'e kaydedilir
• Engineer account'undan transaction gönderilir
• Ganache GUI'de transaction'ı görebilirsiniz
• Gas fee otomatik hesaplanır"""
            
            tk.Label(info_frame, 
                    text=info_text,
                    font=('Arial', 9), 
                    bg='#34495e', 
                    fg='#ecf0f1',
                    justify='left').pack(anchor='w', padx=10, pady=5)
            
            # Butonlar
            button_frame = tk.Frame(stats_window, bg='#2c3e50')
            button_frame.pack(pady=20)
            
            # Initialize blockchain butonu
            init_button = tk.Button(button_frame, 
                                   text="🔄 Blockchain'i Yeniden Başlat", 
                                   command=lambda: self.initialize_blockchain_system(),
                                   font=('Arial', 10, 'bold'), 
                                   bg='#3498db', 
                                   fg='white')
            init_button.pack(side='left', padx=10)
            
            # Kapat butonu
            close_button = tk.Button(button_frame, 
                                    text="❌ Kapat", 
                                    command=stats_window.destroy,
                                    font=('Arial', 10, 'bold'), 
                                    bg='#e74c3c', 
                                    fg='white')
            close_button.pack(side='left', padx=10)
                
        except Exception as e:
            messagebox.showerror("Hata", f"❌ Blockchain istatistikleri gösterilirken hata:\n{e}")

def main():
    """Ana fonksiyon"""
    print("🚀 Arıza Tespit Sistemi - ZK Blockchain Entegrasyonlu")
    print("=" * 60)
    
    # ZK Blockchain setup
    print("🔐 ZK Blockchain sistemi kontrol ediliyor...")
    zk_ready = setup_zk_blockchain()
    if zk_ready:
        print("✅ ZK modülü hazır")
    else:
        print("⚠️ ZK modülü kapalı - sadece local log aktif")
    
    print("📊 Model eğitimi başlatılıyor, lütfen bekleyin...")
    
    # Modeli eğit
    try:
        success = train_model()
        if not success:
            print("❌ Model eğitimi başarısız!")
            return
    except Exception as e:
        print(f"❌ Model eğitimi hatası: {e}")
        return
    
    print("🖥️ GUI Arayüzü açılıyor...")
    
    # GUI başlat
    root = tk.Tk()
    app = PredictiveMaintenance(root)
    
    print("🎯 Arayüz hazır! Sensör verilerini girin ve arıza tespiti yapın.")
    print("🔐 ZK Kayıt: Her tahmin otomatik olarak blockchain/log'a kaydedilecek")
    root.mainloop()

if __name__ == "__main__":
    main() 