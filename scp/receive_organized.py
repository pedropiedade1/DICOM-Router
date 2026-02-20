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
DICOM_ROOT = "/home/dicom"

def sanitize_filename(text):
    """Remove caracteres inválidos de nomes de arquivo/pasta"""
    if not text:
        return "UNKNOWN"
    # Remove caracteres problemáticos
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        text = text.replace(char, '_')
    return text.strip() or "UNKNOWN"

def organize_dicom_file(filepath):
    """
    Lê o arquivo DICOM e move para pasta organizada
    Estrutura: /home/dicom/YYYYMMDD_HHMMSS_PatientID_PatientName/
    """
    try:
        # Lê metadados DICOM
        ds = pydicom.dcmread(filepath, stop_before_pixels=True)
        
        # Extrai informações do paciente
        patient_id = sanitize_filename(str(getattr(ds, 'PatientID', 'UNKNOWN')))
        patient_name = sanitize_filename(str(getattr(ds, 'PatientName', 'UNKNOWN')))
        study_date = str(getattr(ds, 'StudyDate', ''))
        study_time = str(getattr(ds, 'StudyTime', ''))
        
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
print("Porta: 104")
print("Organizando por paciente...")
print("=" * 60)

# storescp com callback para processar cada arquivo recebido
# Nota: storescp não suporta callback direto, então vamos usar o modo exec
subprocess.run([
    "storescp",
    "--verbose",
    "104",
    "--filename-extension", ".dcm",
    "-od", DICOM_ROOT,
    "+uf",  # Unique filenames baseado em SOP Instance UID
])
