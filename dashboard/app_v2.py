import streamlit as st
import docker
import pandas as pd
import time
from datetime import datetime
from pathlib import Path
import json
import subprocess
import socket
import os
import shutil
import io

# Tenta importar dependências do visualizador CT
try:
    import pydicom
    import numpy as np
    from PIL import Image
    VIEWER_AVAILABLE = True
except ImportError:
    VIEWER_AVAILABLE = False

# Configuração da Página
st.set_page_config(
    page_title="DICOM Router Manager",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("#### 🏥 DICOM Router - Painel de Controle")

# CSS compacto para Full HD widescreen (1920x1080)
st.markdown("""<style>
    .block-container {padding-top: 0.75rem; padding-bottom: 0;}
    h1 {font-size: 1.3rem !important;}
    h2, [data-testid="stHeadingWithActionElements"] {font-size: 1.05rem !important;}
    h3 {font-size: 0.95rem !important;}
    h4 {font-size: 1.1rem !important; margin-bottom: 0.25rem !important;}
    p, li, .stMarkdown span, .stText {font-size: 0.82rem !important;}
    [data-testid="stMetricLabel"] p {font-size: 0.7rem !important;}
    [data-testid="stMetricValue"] {font-size: 1rem !important;}
    [data-baseweb="tab"] {font-size: 0.8rem !important; padding: 0.35rem 0.6rem !important;}
    .stExpander {margin-bottom: 0.2rem !important;}
    div[data-testid="stExpander"] details summary p {font-size: 0.82rem !important;}
    .stSelectbox label, .stNumberInput label, .stSlider label {font-size: 0.78rem !important;}
    .stSelectbox, .stNumberInput {margin-bottom: 0.25rem !important;}
    .stDivider {margin: 0.4rem 0 !important;}
    [data-testid="stSidebar"] .stMarkdown p {font-size: 0.78rem !important;}
    [data-testid="stSidebar"] .stAlert p {font-size: 0.75rem !important;}
    [data-testid="stImage"] {margin-bottom: 0 !important;}
    .stCaption, [data-testid="stCaptionContainer"] p {font-size: 0.72rem !important;}
</style>""", unsafe_allow_html=True)

# Constantes
DICOM_ROOT = Path(os.getenv("DICOM_ROOT", "/home/dicom"))
METADATA_FILE = DICOM_ROOT / ".metadata.json"
STATUS_FILE = DICOM_ROOT / ".send_status.json"
ENV_FILE = Path("/home/prowess/dicomrs/.env")
DICOM_ARCHIVE_ROOT = Path(os.getenv("DICOM_ROOT", "/home/dicom"))  # Pasta com estudos organizados

# --- Funções Auxiliares ---

def load_env():
    """Carrega variáveis do .env"""
    env_vars = {}
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    return env_vars

def load_metadata():
    """Carrega metadados dos estudos"""
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def load_send_status():
    """Carrega status de envio dos estudos"""
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_send_status(status_data):
    """Salva status de envio dos estudos"""
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(status_data, f, indent=2)
        return True
    except Exception as e:
        return False

def update_study_status(study_name: str, status: str, message: str = "", sent_count: int = 0, total_count: int = 0):
    """Atualiza o status de um estudo específico"""
    status_data = load_send_status()
    status_data[study_name] = {
        'status': status,  # 'enviado', 'falha', 'pendente', 'enviando'
        'message': message,
        'sent_count': sent_count,
        'total_count': total_count,
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    save_send_status(status_data)

def save_metadata(metadata):
    """Salva metadados dos estudos"""
    try:
        with open(METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar metadados: {e}")
        return False

def get_study_folders():
    """Lista pastas de estudos no disco com status de envio, mais recentes primeiro"""
    folders = []
    status_data = load_send_status()
    try:
        for d in DICOM_ARCHIVE_ROOT.iterdir():
            if d.is_dir() and not d.name.startswith('.'):
                dcm_files = list(d.glob("*.dcm"))
                if dcm_files:
                    study_status = status_data.get(d.name, {})
                    # Extrai nome do paciente e data do nome da pasta: YYYYMMDD_HHMMSS_ID_NOME
                    parts = d.name.split('_', 3)
                    if len(parts) >= 4:
                        patient_name = parts[3]
                        date_str = parts[0]
                        display_date = f"{date_str[6:8]}/{date_str[4:6]}/{date_str[:4]}" if len(date_str) == 8 else date_str
                        display_name = f"{patient_name} ({display_date})"
                    else:
                        display_name = d.name
                    folders.append({
                        'path': d,
                        'name': d.name,
                        'display_name': display_name,
                        'file_count': len(dcm_files),
                        'size_mb': sum(f.stat().st_size for f in dcm_files) / (1024*1024),
                        'status': study_status.get('status', 'pendente'),
                        'status_message': study_status.get('message', ''),
                        'last_update': study_status.get('last_update', ''),
                        'sent_count': study_status.get('sent_count', 0),
                        'total_count': study_status.get('total_count', 0)
                    })
    except Exception as e:
        st.error(f"Erro ao listar pastas: {e}")
    # Ordena por nome da pasta decrescente (mais recentes primeiro)
    folders.sort(key=lambda f: f['name'], reverse=True)
    return folders

def resend_study(folder_path: Path, target_host: str, target_port: str, target_aet: str):
    """Reenvia um estudo DICOM para o destino usando gdcmscu dentro do container storescu"""
    dcm_files = list(folder_path.glob("*.dcm"))
    if not dcm_files:
        update_study_status(folder_path.name, 'falha', 'Nenhum arquivo DICOM encontrado')
        return False, "Nenhum arquivo DICOM encontrado na pasta"
    
    total_files = len(dcm_files)
    
    # Atualiza status para "enviando"
    update_study_status(folder_path.name, 'enviando', f'Enviando {total_files} arquivos...', 0, total_files)
    
    container = get_container("storescu")
    if not container:
        update_study_status(folder_path.name, 'falha', 'Container storescu não encontrado')
        return False, "Container storescu não encontrado"
    
    # Caminho dentro do container
    container_path = f"/home/dicom/{folder_path.name}"
    
    try:
        # Envia todos os arquivos da pasta de uma vez usando sintaxe correta do gdcmscu
        # gdcmscu --store -H host -p port --call AET -r -i "pasta"
        cmd = f'gdcmscu --store -H {target_host} -p {target_port} --call {target_aet} -r -i "{container_path}" --verbose'
        exec_result = container.exec_run(["bash", "-c", cmd], tty=True)
        output = exec_result.output.decode('utf-8', errors='ignore')
        
        if exec_result.exit_code == 0:
            update_study_status(folder_path.name, 'enviado', f'Enviado com sucesso!', total_files, total_files)
            return True, f"Estudo reenviado com sucesso! ({total_files} arquivos)"
        else:
            # Tenta contar quantos foram enviados
            sent_count = output.count('successfully')
            error_msg = output[:300] if output else "Erro desconhecido"
            update_study_status(folder_path.name, 'falha', f'Erro no envio: {error_msg}', sent_count, total_files)
            return False, f"Erro ao reenviar: {error_msg}"
    except Exception as e:
        update_study_status(folder_path.name, 'falha', f'Exceção: {str(e)}')
        return False, f"Exceção: {str(e)}"

def test_connection(host, port, timeout=2):
    """Testa conexão TCP"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        return result == 0
    except:
        return False

def check_port_listening(port):
    """Verifica se porta está escutando localmente"""
    try:
        # Tenta conectar na porta para verificar se está escutando
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        htr_ip = os.getenv("HTR_IP", "172.22.61.14")
        result = sock.connect_ex((htr_ip, int(port)))
        sock.close()
        if result == 0:
            return True
        # Fallback: verifica via netstat sem sudo
        result = subprocess.run(
            f"netstat -tlnp 2>/dev/null | grep ':{port}' || ss -tlnp | grep ':{port}'",
            shell=True, capture_output=True, text=True
        )
        return len(result.stdout) > 0
    except:
        return True  # Em caso de dúvida, assume que está funcionando

def get_firewall_status():
    """Verifica status do firewall/iptables"""
    try:
        result = subprocess.run(
            "sudo iptables -L -n | head -20",
            shell=True, capture_output=True, text=True, timeout=2
        )
        return result.stdout
    except:
        return "Erro ao verificar firewall"

def delete_study(folder_path: Path):
    """Deleta pasta do estudo e limpa metadados/status"""
    folder_name = folder_path.name
    try:
        shutil.rmtree(folder_path)
        # Remove do status de envio
        status_data = load_send_status()
        status_data.pop(folder_name, None)
        save_send_status(status_data)
        # Remove dos metadados
        metadata = load_metadata()
        keys_to_remove = [k for k, v in metadata.items() if v.get('folder') == folder_name]
        for k in keys_to_remove:
            del metadata[k]
        if keys_to_remove:
            save_metadata(metadata)
        return True, "Estudo deletado com sucesso"
    except Exception as e:
        return False, f"Erro ao deletar: {e}"

# --- Funções do Visualizador CT ---

CT_PRESETS = {
    "Tecido Mole": {"wc": 40, "ww": 400},
    "Pulmão": {"wc": -600, "ww": 1500},
    "Osso": {"wc": 400, "ww": 1800},
    "Cérebro": {"wc": 40, "ww": 80},
    "Mediastino": {"wc": 50, "ww": 350},
    "Fígado": {"wc": 60, "ww": 150},
}

if VIEWER_AVAILABLE:
    @st.cache_data(ttl=300)
    def get_sorted_dcm_files(study_path_str: str) -> list[str]:
        """Lista e ordena arquivos .dcm por InstanceNumber (headers only)."""
        study_path = Path(study_path_str)
        dcm_files = list(study_path.glob("*.dcm"))
        if not dcm_files:
            return []
        indexed = []
        for f in dcm_files:
            try:
                ds = pydicom.dcmread(str(f), stop_before_pixels=True)
                idx = int(getattr(ds, "InstanceNumber", 0))
            except Exception:
                idx = 0
            indexed.append((idx, str(f)))
        indexed.sort(key=lambda x: x[0])
        return [path for _, path in indexed]

    @st.cache_data(ttl=300)
    def get_study_info(study_path_str: str) -> dict:
        """Extrai metadados do paciente do primeiro DICOM."""
        study_path = Path(study_path_str)
        dcm_files = list(study_path.glob("*.dcm"))
        if not dcm_files:
            return {}
        try:
            ds = pydicom.dcmread(str(dcm_files[0]), stop_before_pixels=True)
            raw_name = str(getattr(ds, "PatientName", "N/A"))
            # Limpa separadores DICOM (^ e =) para exibição
            clean_name = ' '.join(raw_name.replace('^', ' ').replace('=', ' ').split())
            return {
                "patient_name": clean_name,
                "patient_id": str(getattr(ds, "PatientID", "N/A")),
                "study_date": str(getattr(ds, "StudyDate", "N/A")),
                "modality": str(getattr(ds, "Modality", "N/A")),
                "total_slices": len(dcm_files),
            }
        except Exception:
            return {"patient_name": "N/A", "patient_id": "N/A", "study_date": "N/A", "modality": "N/A", "total_slices": len(dcm_files)}

    def apply_ct_windowing(pixel_array: "np.ndarray", intercept: float, slope: float, wc: int, ww: int) -> "np.ndarray":
        """Converte pixel data para HU e aplica janelamento Window/Level."""
        hu = pixel_array.astype(np.float64) * slope + intercept
        lower = wc - ww / 2
        upper = wc + ww / 2
        img = np.clip(hu, lower, upper)
        img = ((img - lower) / (upper - lower) * 255).astype(np.uint8)
        return img

    @st.cache_data(ttl=600, max_entries=500)
    def render_slice(dcm_path: str, wc: int, ww: int, size: tuple[int, int] | None = None) -> bytes | None:
        """Lê DICOM, aplica janelamento, retorna PNG bytes."""
        try:
            ds = pydicom.dcmread(dcm_path)
            if not hasattr(ds, "PixelData"):
                return None
            pixel_array = ds.pixel_array
            intercept = float(getattr(ds, "RescaleIntercept", 0))
            slope = float(getattr(ds, "RescaleSlope", 1))
            img_array = apply_ct_windowing(pixel_array, intercept, slope, wc, ww)
            img = Image.fromarray(img_array, mode="L")
            if size:
                img = img.resize(size, Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            return None

# --- Conexão Docker ---
try:
    client = docker.from_env()
except Exception as e:
    st.error(f"❌ Erro ao conectar com Docker: {e}")
    st.stop()

def get_container(service_name_part):
    containers = client.containers.list(all=True)
    for c in containers:
        if service_name_part in c.name:
            return c
    return None

scp_container = get_container("storescp")
scu_container = get_container("storescu")
dash_container = get_container("dashboard")

# --- Carrega Configurações ---
env_vars = load_env()
HTR_IP = env_vars.get('HTR_IP', '172.22.61.14')
SCP_PORT = env_vars.get('SCP_PORT', '104')
TARGET_HOST = env_vars.get('TARGET_HOST', '192.168.10.16')
TARGET_PORT = env_vars.get('TARGET_PORT', '4243')
TARGET_AET = env_vars.get('TARGET_AET', 'ZEROCLICK')

# ==================== SIDEBAR ====================
st.sidebar.header("⚙️ Status do Sistema")

# Status dos serviços
def show_container_status(container, name, emoji):
    if container:
        status = container.status
        if status == "running":
            st.sidebar.success(f"{emoji} **{name}**: ✅ Ativo")
        else:
            st.sidebar.error(f"{emoji} **{name}**: ❌ {status.upper()}")
        
        col1, col2 = st.sidebar.columns(2)
        if col2.button(f"🔄 Restart", key=f"rst_{name}", use_container_width=True):
            with st.spinner(f"Reiniciando {name}..."):
                container.restart()
                time.sleep(2)
                st.rerun()
    else:
        st.sidebar.warning(f"{emoji} **{name}**: ⚠️ Não encontrado")

show_container_status(scp_container, "Recebimento", "📥")
show_container_status(scu_container, "Envio", "📤")
show_container_status(dash_container, "Dashboard", "📊")

st.sidebar.divider()

# Testes de Conectividade
st.sidebar.subheader("🌐 Conectividade")

# Teste Rede HTR
htr_listening = check_port_listening(SCP_PORT)
if htr_listening:
    st.sidebar.success(f"✅ Porta {SCP_PORT} escutando em {HTR_IP}")
else:
    st.sidebar.error(f"❌ Porta {SCP_PORT} não está escutando")

# Teste Rede Clínica
target_reachable = test_connection(TARGET_HOST, TARGET_PORT)
if target_reachable:
    st.sidebar.success(f"✅ Zero Click alcançável ({TARGET_HOST}:{TARGET_PORT})")
else:
    st.sidebar.warning(f"⚠️ Zero Click não responde ({TARGET_HOST}:{TARGET_PORT})")

# Echo Test
if st.sidebar.button("🔍 Executar Echo Test", use_container_width=True):
    with st.spinner("Testando conectividade..."):
        st.sidebar.write("**Teste de Ping HTR:**")
        result_htr = subprocess.run(f"ping -c 2 {HTR_IP}", shell=True, capture_output=True, text=True)
        st.sidebar.code(result_htr.stdout[-200:], language="bash")
        
        st.sidebar.write(f"**Teste de Ping Zero Click:**")
        result_target = subprocess.run(f"ping -c 2 {TARGET_HOST}", shell=True, capture_output=True, text=True)
        st.sidebar.code(result_target.stdout[-200:], language="bash")

st.sidebar.divider()

# Auto-refresh
auto_refresh = st.sidebar.checkbox('🔄 Auto-refresh (10s)', value=False)
if auto_refresh:
    time.sleep(10)
    st.rerun()

# ==================== ABAS PRINCIPAIS ====================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Estudos DICOM", "🖼️ Visualizador CT", "📝 Logs em Tempo Real", "🔧 Diagnóstico", "⚙️ Configurações"])

# ==================== ABA 1: ESTUDOS DICOM ====================
with tab1:
    study_folders = get_study_folders()

    if not study_folders:
        st.info("Nenhum estudo recebido ainda. Aguardando imagens...")
    else:
        # Métricas compactas
        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        mc1.metric("Estudos", len(study_folders))
        mc2.metric("Imagens", sum(f['file_count'] for f in study_folders))
        mc3.metric("Enviados", len([f for f in study_folders if f['status'] == 'enviado']))
        mc4.metric("Falhas", len([f for f in study_folders if f['status'] == 'falha']))
        mc5.metric("Pendentes", len([f for f in study_folders if f['status'] == 'pendente']))

        st.divider()

        def get_status_icon(status):
            return {'enviado': '✅', 'falha': '❌', 'pendente': '⏳', 'enviando': '🔄'}.get(status, '❓')

        for idx, folder in enumerate(study_folders):
            s_icon = get_status_icon(folder['status'])
            s_text = folder['status'].upper()

            with st.expander(f"{s_icon} {folder['display_name']} — {folder['file_count']} img — **{s_text}**"):
                info_col, btn_col = st.columns([5, 2])

                with info_col:
                    st.caption(
                        f"Pasta: `{folder['name']}` | {folder['size_mb']:.1f} MB"
                        + (f" | Atualizado: {folder['last_update']}" if folder['last_update'] else "")
                        + (f" | {folder['sent_count']}/{folder['total_count']} enviados" if folder['total_count'] > 0 else "")
                    )
                    if folder['status_message']:
                        st.caption(f"Msg: {folder['status_message'][:120]}")

                with btn_col:
                    b1, b2, b3 = st.columns(3)
                    with b1:
                        if st.button("🔄 Reenviar", key=f"resend_{idx}", type="primary", use_container_width=True):
                            with st.spinner("Enviando..."):
                                success, message = resend_study(folder['path'], TARGET_HOST, TARGET_PORT, TARGET_AET)
                                if success:
                                    st.success(message)
                                else:
                                    st.error(message)
                                st.rerun()
                    with b2:
                        if st.button("📂 Arquivos", key=f"view_{idx}", use_container_width=True):
                            files = list(folder['path'].glob("*.dcm"))[:20]
                            for f in files:
                                st.caption(f"• {f.name}")
                            if folder['file_count'] > 20:
                                st.caption(f"... +{folder['file_count'] - 20}")
                    with b3:
                        with st.popover("🗑️ Deletar", use_container_width=True):
                            st.warning(f"Excluir **{folder['display_name']}** permanentemente?")
                            if st.button("Confirmar exclusão", key=f"del_{idx}", type="primary"):
                                ok, msg = delete_study(folder['path'])
                                if ok:
                                    st.success(msg)
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error(msg)

        st.divider()

        # Reenvio em lote compacto
        batch_col1, batch_col2 = st.columns([3, 1])
        with batch_col1:
            selected_studies = st.multiselect(
                "Reenvio em lote:",
                options=[f['name'] for f in study_folders],
                format_func=lambda n: next((f['display_name'] for f in study_folders if f['name'] == n), n),
                key="batch_select"
            )
        with batch_col2:
            st.write("")  # spacing
            if st.button("🚀 Reenviar Selecionados", type="primary", disabled=len(selected_studies) == 0, use_container_width=True):
                bar = st.progress(0)
                for i, sn in enumerate(selected_studies):
                    fl = next((f for f in study_folders if f['name'] == sn), None)
                    if fl:
                        ok, msg = resend_study(fl['path'], TARGET_HOST, TARGET_PORT, TARGET_AET)
                        (st.success if ok else st.error)(f"{fl['display_name']}: {msg}")
                    bar.progress((i + 1) / len(selected_studies))

        # Disco compacto
        try:
            disk = subprocess.run("df -h /home/dicom --output=size,used,avail,pcent", shell=True, capture_output=True, text=True)
            st.caption(f"💾 Disco: {disk.stdout.strip().splitlines()[-1].strip()}")
        except:
            pass

# ==================== ABA 2: VISUALIZADOR CT ====================
with tab2:
    if not VIEWER_AVAILABLE:
        st.warning("Dependências do visualizador não disponíveis. Instale: `pydicom numpy Pillow`")
    else:
        viewer_folders = get_study_folders()
        if not viewer_folders:
            st.info("Nenhum estudo encontrado.")
        else:
            # Barra de controles compacta — tudo em uma linha
            sel_c, preset_c, wc_c, ww_c = st.columns([3, 2, 1, 1])
            with sel_c:
                viewer_names = [f["name"] for f in viewer_folders]
                selected_vname = st.selectbox(
                    "Paciente:",
                    options=viewer_names,
                    format_func=lambda n: next((f['display_name'] for f in viewer_folders if f['name'] == n), n),
                    key="ct_viewer_study"
                )
                selected_vfolder = next(f for f in viewer_folders if f["name"] == selected_vname)
            with preset_c:
                preset_name = st.selectbox("Preset:", list(CT_PRESETS.keys()), key="ct_preset")
            preset = CT_PRESETS[preset_name]
            with wc_c:
                wc = st.number_input("WC", value=preset["wc"], step=10, key="ct_wc")
            with ww_c:
                ww = st.number_input("WW", value=preset["ww"], min_value=1, step=10, key="ct_ww")

            study_path_str = str(selected_vfolder["path"])

            # Info compacta em uma linha
            info = get_study_info(study_path_str)
            if info:
                st.caption(
                    f"**{info.get('patient_name', 'N/A')}** | "
                    f"ID: {info.get('patient_id', 'N/A')} | "
                    f"Data: {info.get('study_date', 'N/A')} | "
                    f"{info.get('modality', 'N/A')} | "
                    f"{info.get('total_slices', 0)} fatias"
                )

            sorted_files = get_sorted_dcm_files(study_path_str)
            if not sorted_files:
                st.warning("Nenhum arquivo DICOM encontrado neste estudo.")
            else:
                total = len(sorted_files)

                # Layout 2 colunas: controles+thumbs à esquerda, imagem à direita
                panel_left, panel_right = st.columns([1, 3])

                with panel_left:
                    slice_idx = st.slider("Fatia", 0, total - 1, total // 2, key="ct_slice_slider")
                    st.caption(f"Fatia {slice_idx + 1} / {total}")

                    # Thumbnails compactos no painel esquerdo
                    max_thumbs = 12
                    step = max(1, total // max_thumbs)
                    thumb_indices = list(range(0, total, step))[:max_thumbs]

                    cols_per_row = 3
                    for row_start in range(0, len(thumb_indices), cols_per_row):
                        row_indices = thumb_indices[row_start:row_start + cols_per_row]
                        tcols = st.columns(cols_per_row)
                        for tc, tidx in zip(tcols, row_indices):
                            tb = render_slice(sorted_files[tidx], wc, ww, size=(96, 96))
                            if tb:
                                tc.image(tb, caption=f"#{tidx + 1}", use_container_width=True)

                with panel_right:
                    img_bytes = render_slice(sorted_files[slice_idx], wc, ww)
                    if img_bytes:
                        st.image(img_bytes, use_container_width=True)
                    else:
                        st.warning(f"Sem imagem para fatia {slice_idx + 1}.")

# ==================== ABA 3: LOGS ====================
with tab3:
    def parse_logs(container, lines=100):
        if not container:
            return []
        logs = container.logs(tail=lines).decode('utf-8', errors='ignore').split('\n')
        return [l for l in logs if l.strip()]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📥 Recebimento (HTR → Servidor)")
        if scp_container:
            logs_scp = parse_logs(scp_container)
            st.text_area("Logs SCP", value="\n".join(logs_scp[::-1]), height=500, key="logs_scp")
        else:
            st.info("Container SCP não encontrado")

    with col2:
        st.subheader("📤 Envio (Servidor → Zero Click)")
        if scu_container:
            logs_scu = parse_logs(scu_container)
            st.text_area("Logs SCU", value="\n".join(logs_scu[::-1]), height=500, key="logs_scu")
        else:
            st.info("Container SCU não encontrado")

# ==================== ABA 4: DIAGNÓSTICO ====================
with tab4:
    st.subheader("🔧 Informações de Diagnóstico")
    
    diag_col1, diag_col2 = st.columns(2)
    
    with diag_col1:
        st.write("**🔌 Portas em Uso:**")
        try:
            result = subprocess.run(
                "sudo netstat -tlnp | grep -E ':104|:4100|:8501|:4243'",
                shell=True, capture_output=True, text=True
            )
            if result.stdout:
                st.code(result.stdout, language="bash")
            else:
                st.warning("Nenhuma porta DICOM detectada")
        except:
            st.error("Erro ao verificar portas")
        
        st.write("**🛣️ Tabela de Rotas:**")
        try:
            result = subprocess.run("ip route show", shell=True, capture_output=True, text=True)
            st.code(result.stdout, language="bash")
        except:
            st.error("Erro ao verificar rotas")
    
    with diag_col2:
        st.write("**🖧 Interfaces de Rede:**")
        try:
            result = subprocess.run(
                "ip addr show | grep -E 'inet |^[0-9]'",
                shell=True, capture_output=True, text=True
            )
            st.code(result.stdout, language="bash")
        except:
            st.error("Erro ao verificar interfaces")
        
        st.write("**🛡️ Firewall (iptables):**")
        try:
            firewall_status = get_firewall_status()
            st.code(firewall_status, language="bash")
        except:
            st.error("Erro ao verificar firewall")
    
    st.divider()
    
    # Botão para diagnóstico completo
    if st.button("📋 Gerar Relatório Completo de Diagnóstico", type="primary"):
        with st.spinner("Gerando relatório..."):
            report = f"""
=== RELATÓRIO DE DIAGNÓSTICO ===
Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

1. CONTAINERS DOCKER:
{subprocess.run('cd /home/prowess/dicomrs && sudo docker compose ps', shell=True, capture_output=True, text=True).stdout}

2. PORTAS:
{subprocess.run("sudo netstat -tlnp | grep -E ':104|:4100|:8501'", shell=True, capture_output=True, text=True).stdout}

3. CONECTIVIDADE:
Ping HTR ({HTR_IP}):
{subprocess.run(f'ping -c 2 {HTR_IP}', shell=True, capture_output=True, text=True).stdout}

Ping Zero Click ({TARGET_HOST}):
{subprocess.run(f'ping -c 2 {TARGET_HOST}', shell=True, capture_output=True, text=True).stdout}

4. DISCO:
{subprocess.run('df -h /home/dicom', shell=True, capture_output=True, text=True).stdout}

5. ARQUIVOS DICOM:
{subprocess.run('ls -lh /home/prowess/dicomrs/dicom/ | head -20', shell=True, capture_output=True, text=True).stdout}
"""
            st.download_button(
                label="💾 Baixar Relatório",
                data=report,
                file_name=f"diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
            st.code(report, language="bash")

# ==================== ABA 5: CONFIGURAÇÕES ====================
with tab5:
    st.subheader("⚙️ Configurações do Sistema")
    
    st.write("**Arquivo .env atual:**")
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r') as f:
            env_content = f.read()
        st.code(env_content, language="bash")
    else:
        st.warning("Arquivo .env não encontrado")
    
    st.divider()
    
    st.write("**📍 Caminhos Importantes:**")
    st.code(f"""
Workspace: /home/prowess/dicomrs/
Arquivos DICOM: {DICOM_ROOT}
Metadados: {METADATA_FILE}
Configuração: {ENV_FILE}
    """, language="bash")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Reiniciar Todos os Serviços", type="primary"):
            with st.spinner("Reiniciando containers..."):
                subprocess.run("cd /home/prowess/dicomrs && sudo docker compose restart", shell=True)
                time.sleep(3)
                st.success("✅ Serviços reiniciados!")
                time.sleep(1)
                st.rerun()
    
    with col2:
        if st.button("🧹 Limpar Metadados (Cuidado!)", type="secondary"):
            if METADATA_FILE.exists():
                METADATA_FILE.unlink()
                st.success("✅ Metadados limpos!")
                st.rerun()

# Rodapé
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.8em;'>
DICOM Router v2.0 | Desenvolvido para LCC | Última atualização: Janeiro 2026
</div>
""", unsafe_allow_html=True)
