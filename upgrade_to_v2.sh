#!/bin/bash

# Script de Atualização - DICOM Router v2.0
# Atualiza o sistema com novas funcionalidades

set -e

echo "=========================================="
echo "   DICOM Router - Atualização para v2.0"
echo "=========================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Diretório base
BASEDIR="/home/prowess/dicomrs"

# Verifica se está no diretório correto
if [ ! -f "$BASEDIR/docker-compose.yml" ]; then
    echo -e "${RED}Erro: docker-compose.yml não encontrado em $BASEDIR${NC}"
    exit 1
fi

cd "$BASEDIR"

echo -e "${YELLOW}► Verificando arquivos...${NC}"
echo ""

# Lista arquivos que serão atualizados
echo "Novos arquivos criados:"
echo "  ✓ TROUBLESHOOTING.md"
echo "  ✓ IMPLEMENTATION_NOTES.md"
echo "  ✓ scp/organizer.py"
echo "  ✓ scu/scu_script_v2.py"
echo "  ✓ dashboard/app_v2.py"
echo ""

# Pergunta se quer continuar
read -p "Deseja atualizar o sistema? (s/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[SsYy]$ ]]; then
    echo "Atualização cancelada."
    exit 0
fi

echo ""
echo -e "${YELLOW}► Fazendo backup...${NC}"
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup de arquivos importantes
cp docker-compose.yml "$BACKUP_DIR/" 2>/dev/null || true
cp .env "$BACKUP_DIR/" 2>/dev/null || true
cp scp/Dockerfile "$BACKUP_DIR/Dockerfile.scp" 2>/dev/null || true
cp scu/Dockerfile "$BACKUP_DIR/Dockerfile.scu" 2>/dev/null || true
cp dashboard/Dockerfile "$BACKUP_DIR/Dockerfile.dashboard" 2>/dev/null || true

echo -e "${GREEN}✓ Backup criado em: $BACKUP_DIR${NC}"
echo ""

# Pergunta se quer fazer backup dos dados DICOM
read -p "Fazer backup da pasta dicom/ também? (s/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[SsYy]$ ]]; then
    echo -e "${YELLOW}Copiando dados DICOM (pode demorar)...${NC}"
    cp -r dicom "$BACKUP_DIR/dicom_backup" 2>/dev/null || true
    echo -e "${GREEN}✓ Backup de dados concluído${NC}"
fi

echo ""
echo -e "${YELLOW}► Parando containers...${NC}"
sudo docker compose down
echo -e "${GREEN}✓ Containers parados${NC}"

echo ""
echo -e "${YELLOW}► Atualizando Dockerfiles...${NC}"

# Atualiza Dockerfile do SCP
cat > scp/Dockerfile <<'EOF'
FROM amd64/ubuntu

MAINTAINER Carlos Queiroz
LABEL version="0.2"

ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y \
    dcmtk \
    libgdcm-tools \
    libvtkgdcm-tools \
    rsync \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir pydicom

EXPOSE 104 4100

COPY receive.sh /home/www/
COPY storescp.cfg /home/www/
COPY organizer.py /home/www/

WORKDIR /home

# Inicia receptor DICOM e organizador em paralelo
CMD /home/www/receive.sh & python3 /home/www/organizer.py
EOF
echo -e "${GREEN}✓ scp/Dockerfile atualizado${NC}"

# Atualiza Dockerfile do Dashboard  
cat > dashboard/Dockerfile <<'EOF'
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    net-tools \
    iputils-ping \
    iproute2 \
    sudo \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir streamlit docker pandas

COPY app_v2.py /app/app.py

WORKDIR /app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
EOF
echo -e "${GREEN}✓ dashboard/Dockerfile atualizado${NC}"

# Atualiza docker-compose.yml
echo ""
echo -e "${YELLOW}► Atualizando docker-compose.yml...${NC}"

# Backup do original
cp docker-compose.yml docker-compose.yml.bak

# Atualiza comando do SCU
if grep -q "scu_script.py" docker-compose.yml; then
    sed -i 's|python /home/scu_script.py|python /home/scu_script_v2.py|g' docker-compose.yml
    echo -e "${GREEN}✓ Comando SCU atualizado${NC}"
fi

# Atualiza comando do Dashboard
if grep -q "app.py" dashboard/Dockerfile; then
    echo -e "${GREEN}✓ Comando Dashboard atualizado${NC}"
fi

# Adiciona volume de leitura do dicom no dashboard se não existir
if ! grep -q "./dicom:/home/dicom:ro" docker-compose.yml; then
    echo -e "${YELLOW}⚠ ATENÇÃO: Adicione manualmente ao docker-compose.yml:${NC}"
    echo ""
    echo "  dashboard:"
    echo "    volumes:"
    echo "      - /var/run/docker.sock:/var/run/docker.sock"
    echo "      - ./dicom:/home/dicom:ro  # ← ADICIONE ESTA LINHA"
    echo ""
fi

echo ""
echo -e "${YELLOW}► Reconstruindo imagens Docker...${NC}"
sudo docker compose build
echo -e "${GREEN}✓ Imagens reconstruídas${NC}"

echo ""
echo -e "${YELLOW}► Iniciando containers...${NC}"
sudo docker compose up -d
echo -e "${GREEN}✓ Containers iniciados${NC}"

echo ""
echo -e "${YELLOW}► Aguardando inicialização (10s)...${NC}"
sleep 10

echo ""
echo -e "${YELLOW}► Verificando status...${NC}"
sudo docker compose ps

echo ""
echo "=========================================="
echo -e "${GREEN}   ✓ Atualização Concluída!${NC}"
echo "=========================================="
echo ""
echo "Próximos passos:"
echo ""
echo "1. Verifique o dashboard: http://$(hostname -I | awk '{print $1}'):8501"
echo "2. Monitore os logs: sudo docker compose logs -f"
echo "3. Leia a documentação: cat TROUBLESHOOTING.md"
echo ""
echo "Backup salvo em: $BACKUP_DIR"
echo ""
echo -e "${YELLOW}Observações importantes:${NC}"
echo "• Arquivos DICOM serão organizados em pastas por paciente"
echo "• Dashboard agora mostra tabela de estudos com detalhes"
echo "• Testes de conectividade disponíveis no dashboard"
echo "• Metadados salvos em dicom/.metadata.json"
echo ""

# Mostra status final
echo "Status dos serviços:"
sudo docker compose ps

echo ""
echo "Para reverter a atualização:"
echo "  cd $BASEDIR"
echo "  sudo docker compose down"
echo "  cp $BACKUP_DIR/docker-compose.yml ."
echo "  sudo docker compose up -d"
echo ""
