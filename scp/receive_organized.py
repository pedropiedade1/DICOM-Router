#!/usr/bin/env python3
"""
Script de recepção DICOM com organização por paciente
Recebe imagens via DICOM C-STORE e organiza em pastas estruturadas
"""

import os
import sys
import subprocess
from pathlib import Path
import pydicom
from datetime import datetime
import shutil

# Diretório de destino
DICOM_ROOT = os.getenv("DICOM_ROOT", "/home/dicom")
SCP_PORT = os.getenv("SCP_PORT", "104")
SCP_AET = os.getenv("SCP_AET", "DICOMRS_SCP")
QUARANTINE_DIR = Path(DICOM_ROOT) / "_INVALID_NO_PIXELS"
IMAGE_MODALITIES = {
    "CR", "CT", "DX", "IO", "MG", "MR", "NM", "OT", "PT", "RF",
    "RTIMAGE", "US", "XA", "XC",
}

def sanitize_filename(text):
    """Remove caracteres inválidos de nomes de arquivo/pasta"""
    if not text:
        return "UNKNOWN"
    # Substitui separadores DICOM de PersonName por espaço
    text = text.replace('^', ' ').replace('=', ' ')
    # Remove caracteres problemáticos para filesystem
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        text = text.replace(char, '_')
    # Colapsa espaços múltiplos
    text = ' '.join(text.split())
    return text.strip() or "UNKNOWN"

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
    print(f"✗ Quarentena: {dest.name} ({reason})", file=sys.stderr)

def organize_dicom_file(filepath):
    """
    Lê o arquivo DICOM e move para pasta organizada
    Estrutura: /home/dicom/YYYYMMDD_HHMMSS_PatientID_PatientName/
    """
    try:
        ok_pixels, reason = validate_image_dicom_has_pixels(filepath)
        if not ok_pixels:
            quarantine_invalid_dicom(filepath, reason)
            return False

        # Lê metadados DICOM (sem pixels) para organizar
        ds = pydicom.dcmread(filepath, stop_before_pixels=True)
        
        # Extrai informações do paciente
        patient_id = sanitize_filename(str(getattr(ds, 'PatientID', 'UNKNOWN')))
        patient_name = sanitize_filename(str(getattr(ds, 'PatientName', 'UNKNOWN')))
        
        # Cria timestamp da recepção
        reception_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Nome da pasta: TIMESTAMP_ID_NOME
        folder_name = f"{reception_time}_{patient_id}_{patient_name}"
        dest_folder = Path(DICOM_ROOT) / folder_name
        
        # Cria pasta se não existir
        dest_folder.mkdir(parents=True, exist_ok=True)
        
        # Move arquivo para a pasta
        filename = Path(filepath).name
        dest_path = dest_folder / filename
        shutil.move(filepath, dest_path)
        
        print(f"✓ Organizado: {folder_name}/{filename}")
        return True
        
    except Exception as e:
        print(f"✗ Erro ao organizar {filepath}: {e}", file=sys.stderr)
        # Se falhar, deixa no diretório raiz
        return False

def callback_on_receive(filepath):
    """Callback chamado após receber cada arquivo"""
    organize_dicom_file(filepath)

# Inicia o servidor DICOM SCP
print("=" * 60)
print("DICOM Store SCP - Servidor de Recepção")
print(f"Porta: {SCP_PORT}")
print("Organizando por paciente...")
print("=" * 60)

# storescp com callback para processar cada arquivo recebido
# Nota: storescp não suporta callback direto, então vamos usar o modo exec
subprocess.run([
    "storescp",
    "--verbose",
    "--aetitle", SCP_AET,
    SCP_PORT,
    "--filename-extension", ".dcm",
    "-od", DICOM_ROOT,
    "+uf",  # Unique filenames baseado em SOP Instance UID
])
