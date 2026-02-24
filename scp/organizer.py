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

DICOM_ROOT = Path(os.getenv("DICOM_ROOT", "/home/dicom"))
METADATA_FILE = DICOM_ROOT / ".metadata.json"
QUARANTINE_DIR = DICOM_ROOT / "_INVALID_NO_PIXELS"
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

def dataset_requires_pixel_data(ds):
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

def validate_image_dicom_has_pixels(filepath):
    ds = pydicom.dcmread(filepath, stop_before_pixels=False)
    if not dataset_requires_pixel_data(ds):
        return True, "nao e imagem"
    if not dataset_has_pixel_data(ds):
        return False, "DICOM de imagem sem PixelData"
    return True, "ok"

def quarantine_invalid_dicom(filepath, reason):
    src = Path(filepath)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    dest = QUARANTINE_DIR / src.name
    counter = 1
    while dest.exists():
        dest = QUARANTINE_DIR / f"{src.stem}_{counter}{src.suffix}"
        counter += 1
    shutil.move(str(src), str(dest))
    print(f"✗ Quarentena: {dest.name} ({reason})")

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
        ok_pixels, reason = validate_image_dicom_has_pixels(filepath)
        if not ok_pixels:
            quarantine_invalid_dicom(filepath, reason)
            return False

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
