#!/usr/bin/env python3
"""
Monitor e organizador de arquivos DICOM
Monitora a pasta raiz e organiza arquivos por paciente em tempo real
"""

import os
import time
import pydicom
from pathlib import Path
from datetime import datetime
import shutil
import json

DICOM_ROOT = Path("/home/dicom")
METADATA_FILE = DICOM_ROOT / ".metadata.json"

def sanitize_filename(text):
    """Remove caracteres inválidos"""
    if not text:
        return "UNKNOWN"
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        text = text.replace(char, '_')
    return text.strip()[:50] or "UNKNOWN"  # Limita tamanho

def load_metadata():
    """Carrega metadados de estudos conhecidos"""
    if METADATA_FILE.exists():
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    """Salva metadados"""
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

def get_or_create_study_folder(ds):
    """
    Retorna pasta do estudo, criando se necessário
    Agrupa imagens do mesmo estudo na mesma pasta
    """
    # Chave única do estudo
    study_uid = str(getattr(ds, 'StudyInstanceUID', ''))
    patient_id = sanitize_filename(str(getattr(ds, 'PatientID', 'UNKNOWN')))
    patient_name = sanitize_filename(str(getattr(ds, 'PatientName', 'UNKNOWN')))
    
    # Carrega metadados
    metadata = load_metadata()
    
    # Se estudo já conhecido, retorna pasta existente
    if study_uid in metadata:
        folder_name = metadata[study_uid]['folder']
        return DICOM_ROOT / folder_name, metadata[study_uid]
    
    # Novo estudo - cria pasta com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{timestamp}_{patient_id}_{patient_name}"
    
    # Garante nome único
    counter = 1
    original_name = folder_name
    while (DICOM_ROOT / folder_name).exists():
        folder_name = f"{original_name}_{counter}"
        counter += 1
    
    # Cria metadados do estudo
    study_metadata = {
        'folder': folder_name,
        'patient_id': patient_id,
        'patient_name': patient_name,
        'study_uid': study_uid,
        'study_date': str(getattr(ds, 'StudyDate', '')),
        'study_time': str(getattr(ds, 'StudyTime', '')),
        'modality': str(getattr(ds, 'Modality', 'UNKNOWN')),
        'created_at': timestamp,
        'image_count': 0,
        'study_description': str(getattr(ds, 'StudyDescription', ''))
    }
    
    metadata[study_uid] = study_metadata
    save_metadata(metadata)
    
    return DICOM_ROOT / folder_name, study_metadata

def organize_file(filepath):
    """Organiza um arquivo DICOM"""
    try:
        # Lê metadados
        ds = pydicom.dcmread(filepath, stop_before_pixels=True)
        
        # Obtém ou cria pasta do estudo
        dest_folder, study_meta = get_or_create_study_folder(ds)
        dest_folder.mkdir(parents=True, exist_ok=True)
        
        # Move arquivo
        filename = Path(filepath).name
        dest_path = dest_folder / filename
        
        # Evita sobrescrever
        counter = 1
        while dest_path.exists():
            dest_path = dest_folder / f"{Path(filename).stem}_{counter}{Path(filename).suffix}"
            counter += 1
        
        shutil.move(filepath, dest_path)
        
        # Atualiza contador de imagens
        study_uid = str(ds.StudyInstanceUID)
        metadata = load_metadata()
        if study_uid in metadata:
            metadata[study_uid]['image_count'] += 1
            save_metadata(metadata)
        
        print(f"✓ {study_meta['folder']}: {filename}")
        return True
        
    except Exception as e:
        print(f"✗ Erro ao organizar {filepath}: {e}")
        return False

def monitor_and_organize():
    """Monitora pasta raiz e organiza arquivos .dcm soltos"""
    print("=" * 60)
    print("Monitor DICOM - Organizador de Arquivos")
    print(f"Pasta: {DICOM_ROOT}")
    print("=" * 60)
    
    processed = set()
    
    while True:
        try:
            # Procura arquivos .dcm na raiz (não em subpastas)
            root_files = [f for f in DICOM_ROOT.glob("*.dcm") if f.is_file()]
            
            for filepath in root_files:
                if filepath not in processed:
                    if organize_file(filepath):
                        processed.add(filepath)
            
            # Aguarda antes de verificar novamente
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n⚠ Encerrando monitor...")
            break
        except Exception as e:
            print(f"✗ Erro no monitor: {e}")
            time.sleep(5)

if __name__ == "__main__":
    DICOM_ROOT.mkdir(parents=True, exist_ok=True)
    monitor_and_organize()
