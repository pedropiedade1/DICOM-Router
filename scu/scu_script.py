#!/usr/bin/env python3
"""
DICOM SCU - Envia arquivos DICOM e organiza por paciente
Monitora pasta raiz, envia ao destino, e organiza em subpastas
"""

import os
import sys
import subprocess
import time
import shutil
from pathlib import Path
from datetime import datetime
import json

# Força flush imediato do output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

try:
    import pydicom
    HAS_PYDICOM = True
except ImportError:
    HAS_PYDICOM = False
    print("⚠ pydicom não disponível - organizando por timestamp apenas", flush=True)

# Configurações do destino
TARGET_HOST = os.getenv("TARGET_HOST", "192.168.10.16")
TARGET_PORT = os.getenv("TARGET_PORT", "4243")
TARGET_AET = os.getenv("TARGET_AET", "ZEROCLICK")

# Diretórios
WATCH_FOLDER = Path(os.getenv("DICOM_ROOT", "/home/dicom"))
METADATA_FILE = WATCH_FOLDER / ".metadata.json"
STATUS_FILE = WATCH_FOLDER / ".send_status.json"
QUARANTINE_FOLDER = WATCH_FOLDER / "_INVALID_NO_PIXELS"

IMAGE_MODALITIES = {
    "CR", "CT", "DX", "IO", "MG", "MR", "NM", "OT", "PT", "RF",
    "RTIMAGE", "US", "XA", "XC",
}

def sanitize_filename(text):
    """Remove caracteres inválidos"""
    if not text:
        return "UNKNOWN"
    # Substitui separadores DICOM de PersonName por espaço
    text = text.replace('^', ' ').replace('=', ' ')
    # Remove caracteres problemáticos para filesystem
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        text = text.replace(char, '_')
    # Colapsa espaços múltiplos e limita tamanho
    text = ' '.join(text.split())
    return text.strip()[:50] or "UNKNOWN"

def load_metadata():
    """Carrega metadados de estudos conhecidos"""
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_metadata(metadata):
    """Salva metadados"""
    try:
        with open(METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        print(f"Erro ao salvar metadata: {e}")

def load_send_status():
    """Carrega status de envio"""
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_send_status(status):
    """Salva status de envio"""
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        print(f"Erro ao salvar status: {e}")

def clean_study_description(ds):
    """Limpa caracteres inválidos do campo StudyDescription"""
    if 'StudyDescription' in ds:
        desc = ds.StudyDescription
        # Remove caracteres não imprimíveis ou substitui por espaço
        desc_clean = ''.join(c if c.isprintable() else ' ' for c in desc)
        # Garante UTF-8 válido
        desc_clean = desc_clean.encode('utf-8', errors='replace').decode('utf-8')
        ds.StudyDescription = desc_clean

def read_dicom_metadata_only(filepath):
    """
    Lê apenas metadados e marca o dataset como leitura sem pixels.
    Use safe_save_dicom() se algum dia precisar regravar.
    """
    ds = pydicom.dcmread(filepath, stop_before_pixels=True)
    ds._read_without_pixels = True
    return ds

def dataset_requires_pixel_data(ds):
    """Heurística conservadora: imagens devem ter PixelData."""
    modality = str(getattr(ds, "Modality", "")).upper()
    if modality in IMAGE_MODALITIES:
        return True
    return hasattr(ds, "Rows") and hasattr(ds, "Columns")

def dataset_has_pixel_data(ds):
    return (
        "PixelData" in ds
        or "FloatPixelData" in ds
        or "DoubleFloatPixelData" in ds
    )

def safe_save_dicom(ds, filepath):
    """
    Bloqueia gravação acidental de datasets lidos sem pixels.
    Isso evita corromper arquivos de imagem por save_as() após stop_before_pixels=True.
    """
    if getattr(ds, "_read_without_pixels", False) and dataset_requires_pixel_data(ds):
        raise RuntimeError(
            "Bloqueado: tentativa de salvar DICOM lido com stop_before_pixels=True. "
            "Isso pode remover PixelData."
        )
    ds.save_as(filepath)

def validate_image_dicom_has_pixels(filepath):
    """
    Valida se um DICOM de imagem contém pixel data.
    Retorna (ok, motivo).
    """
    if not HAS_PYDICOM:
        return True, "pydicom indisponível"
    try:
        ds = pydicom.dcmread(filepath, stop_before_pixels=False)
    except Exception as e:
        return False, f"falha ao ler DICOM: {e}"

    if not dataset_requires_pixel_data(ds):
        return True, "não é imagem"
    if not dataset_has_pixel_data(ds):
        return False, "DICOM de imagem sem PixelData"
    return True, "ok"

def quarantine_invalid_dicom(filepath, reason):
    """Move arquivo inválido para quarentena para análise manual."""
    src = Path(filepath)
    QUARANTINE_FOLDER.mkdir(parents=True, exist_ok=True)
    dest = QUARANTINE_FOLDER / src.name
    counter = 1
    while dest.exists():
        dest = QUARANTINE_FOLDER / f"{src.stem}_{counter}{src.suffix}"
        counter += 1
    shutil.move(str(src), str(dest))
    print(f"🚫 DICOM inválido movido para quarentena: {dest.name} ({reason})")
    return dest

def get_or_create_study_folder(filepath):
    """
    Obtém ou cria pasta do estudo baseado nos metadados DICOM
    Retorna (pasta_destino, study_uid)
    """
    study_uid = None
    folder_name = None
    
    if HAS_PYDICOM:
        try:
            ds = read_dicom_metadata_only(filepath)
            clean_study_description(ds)
            # Nao regravar o DICOM apos leitura com stop_before_pixels=True:
            # isso pode salvar o arquivo sem PixelData e corromper a imagem.
            study_uid = str(getattr(ds, 'StudyInstanceUID', ''))
            patient_id = sanitize_filename(str(getattr(ds, 'PatientID', 'UNKNOWN')))
            patient_name = sanitize_filename(str(getattr(ds, 'PatientName', 'UNKNOWN')))
            
            # Verifica se estudo já existe
            metadata = load_metadata()
            if study_uid and study_uid in metadata:
                folder_name = metadata[study_uid]['folder']
            else:
                # Novo estudo - cria pasta
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                folder_name = f"{timestamp}_{patient_id}_{patient_name}"
                
                # Garante nome único
                counter = 1
                original_name = folder_name
                while (WATCH_FOLDER / folder_name).exists():
                    folder_name = f"{original_name}_{counter}"
                    counter += 1
                
                # Salva metadados
                metadata[study_uid] = {
                    'folder': folder_name,
                    'patient_id': patient_id,
                    'patient_name': patient_name,
                    'study_uid': study_uid,
                    'study_date': str(getattr(ds, 'StudyDate', '')),
                    'study_time': str(getattr(ds, 'StudyTime', '')),
                    'modality': str(getattr(ds, 'Modality', 'UNKNOWN')),
                    'study_description': str(getattr(ds, 'StudyDescription', '')),
                    'created_at': timestamp,
                    'image_count': 0,
                    'sent': False
                }
                save_metadata(metadata)
                
        except Exception as e:
            print(f"⚠ Erro ao ler DICOM: {e}")
    
    # Fallback se não conseguir ler metadados
    if not folder_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{timestamp}_UNKNOWN"
        study_uid = folder_name
    
    dest_folder = WATCH_FOLDER / folder_name
    dest_folder.mkdir(parents=True, exist_ok=True)
    
    return dest_folder, study_uid

def update_study_status(folder_name, sent_success):
    """Atualiza status de envio do estudo"""
    status = load_send_status()
    
    if folder_name not in status:
        status[folder_name] = {
            'status': 'pendente',
            'sent_count': 0,
            'failed_count': 0,
            'total_count': 0,
            'last_update': ''
        }
    
    status[folder_name]['total_count'] += 1
    if sent_success:
        status[folder_name]['sent_count'] += 1
        status[folder_name]['status'] = 'enviado'
    else:
        status[folder_name]['failed_count'] += 1
        status[folder_name]['status'] = 'falha'
    
    status[folder_name]['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_send_status(status)

def send_and_organize(file_path):
    """
    Envia arquivo DICOM e depois organiza na pasta correta
    Retorna True se sucesso, False se falha
    """
    filepath = Path(file_path)
    
    if not filepath.exists():
        print(f"⚠ Arquivo não encontrado: {file_path}")
        return False
    
    print(f"📤 Enviando: {filepath.name}")

    # Trava de integridade: nao processa imagem DICOM sem pixels.
    ok_pixels, reason = validate_image_dicom_has_pixels(str(filepath))
    if not ok_pixels:
        print(f"❌ Arquivo DICOM inválido: {filepath.name} ({reason})")
        try:
            quarantine_invalid_dicom(str(filepath), reason)
        except Exception as e:
            print(f"⚠ Falha ao mover para quarentena {filepath.name}: {e}")
        return False
    
    # Primeiro, determina a pasta de destino
    dest_folder, study_uid = get_or_create_study_folder(str(filepath))
    folder_name = dest_folder.name
    
    # Envia para o ZeroClick
    send_success = False
    try:
        result = subprocess.run([
            "gdcmscu", "--store", 
            "-H", TARGET_HOST, 
            "-p", TARGET_PORT, 
            "--call", TARGET_AET, 
            "-i", str(filepath)
        ], check=True, text=True, capture_output=True, timeout=30)
        
        print(f"✅ Enviado: {filepath.name}")
        send_success = True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao enviar {filepath.name}: {e.stderr}")
    except subprocess.TimeoutExpired:
        print(f"⏱ Timeout ao enviar {filepath.name}")
    except Exception as e:
        print(f"❌ Exceção ao enviar {filepath.name}: {e}")
    
    # Move para pasta organizada (mesmo se falhou o envio, para não perder)
    try:
        dest_path = dest_folder / filepath.name
        
        # Evita sobrescrever
        counter = 1
        while dest_path.exists():
            dest_path = dest_folder / f"{filepath.stem}_{counter}{filepath.suffix}"
            counter += 1
        
        shutil.move(str(filepath), str(dest_path))
        print(f"📁 Organizado: {folder_name}/{dest_path.name}")
        
        # Atualiza contador de imagens nos metadados
        if study_uid:
            metadata = load_metadata()
            if study_uid in metadata:
                metadata[study_uid]['image_count'] += 1
                metadata[study_uid]['sent'] = send_success
                save_metadata(metadata)
        
        # Atualiza status de envio
        update_study_status(folder_name, send_success)
        
    except Exception as e:
        print(f"⚠ Erro ao organizar {filepath.name}: {e}")
    
    return send_success

def monitor_folder():
    """Monitora pasta raiz para novos arquivos .dcm"""
    print("=" * 60)
    print("DICOM SCU - Monitor de Envio")
    print(f"Pasta: {WATCH_FOLDER}")
    print(f"Destino: {TARGET_HOST}:{TARGET_PORT} (AET: {TARGET_AET})")
    print("=" * 60)
    
    processing = set()  # Arquivos sendo processados
    
    while True:
        try:
            # Procura arquivos .dcm na raiz (não em subpastas)
            root_files = list(WATCH_FOLDER.glob("*.dcm"))
            
            for filepath in root_files:
                if filepath.is_file() and str(filepath) not in processing:
                    processing.add(str(filepath))
                    
                    # Aguarda um pouco para garantir que o arquivo foi completamente escrito
                    time.sleep(0.5)
                    
                    # Verifica se arquivo ainda existe (pode ter sido movido)
                    if filepath.exists():
                        send_and_organize(str(filepath))
                    
                    processing.discard(str(filepath))
            
            # Aguarda antes de verificar novamente
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n⚠ Encerrando monitor...")
            break
        except Exception as e:
            print(f"❌ Erro no monitor: {e}")
            time.sleep(5)

if __name__ == "__main__":
    WATCH_FOLDER.mkdir(parents=True, exist_ok=True)
    monitor_folder()
