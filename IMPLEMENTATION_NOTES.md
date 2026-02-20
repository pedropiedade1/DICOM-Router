# 📝 Notas de Implementação - DICOM Router v2.0

## Atualização: Janeiro 2026

---

## 🎯 Melhorias Implementadas

### 1. **Organização por Paciente**
- ✅ Arquivos agora são organizados automaticamente em pastas
- ✅ Estrutura: `YYYYMMDD_HHMMSS_PatientID_PatientName/`
- ✅ Imagens do mesmo estudo agrupadas na mesma pasta
- ✅ Timestamp de quando a pasta foi criada

### 2. **Dashboard Avançado**
- ✅ Tabela com informações dos estudos (Paciente, ID, Modalidade, Número de imagens)
- ✅ Status de firewall e portas
- ✅ Echo test de comunicação com tomógrafos
- ✅ Diagnóstico completo do sistema
- ✅ Monitoramento de uso de disco
- ✅ Logs em tempo real melhorados

### 3. **Metadados Persistentes**
- ✅ Arquivo `.metadata.json` mantém histórico dos estudos
- ✅ Contador de imagens por estudo
- ✅ Data/hora de recepção e envio

---

## 📦 Novos Arquivos Criados

### Scripts de Organização:
1. **`scp/organizer.py`** - Monitor que organiza arquivos DICOM após recepção
2. **`scu/scu_script_v2.py`** - SCU atualizado que trabalha com pastas organizadas
3. **`dashboard/app_v2.py`** - Dashboard melhorado com novas funcionalidades

### Documentação:
1. **`TROUBLESHOOTING.md`** - Guia completo de resolução de problemas
2. **`IMPLEMENTATION_NOTES.md`** - Este arquivo

---

## 🔄 Processo de Atualização

### Passo 1: Atualizar Dockerfile do SCP
O container SCP precisa de Python e pydicom para organizar os arquivos:

```dockerfile
FROM amd64/ubuntu

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

# Inicia ambos: receptor DICOM e organizador
CMD /home/www/receive.sh & python3 /home/www/organizer.py
```

### Passo 2: Atualizar docker-compose.yml para usar novos scripts

```yaml
services:
  storescp:
    build: ./scp
    ports:
      - "4100:4100"
      - "${HTR_IP:-0.0.0.0}:104:104"
    volumes:
      - ./dicom:/home/dicom
    restart: always

  storescu:
    build: ./scu
    environment:
      - TARGET_HOST=${TARGET_HOST:-192.168.10.16}
      - TARGET_PORT=${TARGET_PORT:-4243}
      - TARGET_AET=${TARGET_AET:-ZEROCLICK}
    volumes:
      - ./dicom:/home/dicom
    restart: always
    # Usar novo script
    command: python /home/scu_script_v2.py

  dashboard:
    build: ./dashboard
    ports:
      - "8501:8501"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./dicom:/home/dicom:ro  # Read-only para ver arquivos
    restart: always
    # Usar novo dashboard
    command: streamlit run app_v2.py
```

### Passo 3: Atualizar Dockerfile do Dashboard
Adicionar permissões para comandos de diagnóstico:

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    net-tools \
    iputils-ping \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir streamlit docker pandas

COPY app_v2.py /app/app.py

WORKDIR /app

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```

---

## ❓ Sobre a Indicação de Quantas Imagens Serão Enviadas

### Resposta:
**NÃO**, o protocolo DICOM Store (C-STORE) **não informa previamente quantas imagens serão enviadas**.

### Como funciona:
1. A tomografia abre uma **associação DICOM** (conexão)
2. Envia imagens **uma por uma** via comandos C-STORE individuais
3. Cada imagem é um comando separado
4. Quando termina, **fecha a associação**

### O que podemos fazer:
- ✅ **Contar imagens em tempo real** enquanto chegam
- ✅ **Agrupar por StudyInstanceUID** (mesmo exame)
- ✅ **Detectar quando associação fecha** (fim do envio)
- ❌ **NÃO é possível saber antecipadamente** quantas virão

### Implementação no organizador:
O script `organizer.py` já faz isso:
- Agrupa imagens do mesmo `StudyInstanceUID` na mesma pasta
- Mantém contador em tempo real no `.metadata.json`
- Atualiza o contador a cada arquivo recebido

### Log típico no storescp:
```
I: Association Received (tomografia-scanner:11112 -> STORESCP:104)
I: Received Store Request (MsgID 1, CT)
I: storing DICOM file: /home/dicom/CT.1.2.840...20839.dcm
I: Received Store Request (MsgID 2, CT)
I: storing DICOM file: /home/dicom/CT.1.2.840...20840.dcm
...
I: Received Store Request (MsgID 245, CT)
I: storing DICOM file: /home/dicom/CT.1.2.840...21084.dcm
I: Association Release
```

**Só sabemos que terminou quando vemos "Association Release"**

---

## 🚀 Como Ativar as Melhorias

### Opção 1: Atualização Completa (Recomendado)
```bash
cd /home/prowess/dicomrs

# 1. Parar serviços
sudo docker compose down

# 2. Fazer backup da pasta dicom se houver dados importantes
sudo cp -r dicom dicom_backup_$(date +%Y%m%d)

# 3. Atualizar Dockerfiles conforme descrito acima
nano scp/Dockerfile
nano dashboard/Dockerfile

# 4. Copiar novos scripts (já criados)
# - scp/organizer.py ✓
# - scu/scu_script_v2.py ✓
# - dashboard/app_v2.py ✓

# 5. Atualizar docker-compose.yml
nano docker-compose.yml

# 6. Rebuild e restart
sudo docker compose build
sudo docker compose up -d

# 7. Verificar logs
sudo docker compose logs -f
```

### Opção 2: Teste Gradual
```bash
# Primeiro teste o organizador separadamente
cd /home/prowess/dicomrs/scp
python3 organizer.py

# Em outro terminal, veja se organiza corretamente
ls -la ../dicom/
```

---

## ⚠️ Considerações Importantes

### 1. **Compatibilidade com Arquivos Existentes**
- Arquivos `.dcm` soltos na raiz serão organizados automaticamente
- Pastas existentes serão mantidas
- Metadados são criados incrementalmente

### 2. **Performance**
- Organização adiciona ~0.5s de latência por arquivo
- Não impacta recebimento (é assíncrono)
- Recomendado para volumes até 10.000 imagens/dia

### 3. **Espaço em Disco**
- Metadados ocupam ~1KB por estudo
- Sem duplicação de arquivos
- Mesmo comportamento de exclusão após envio

### 4. **Permissões**
- Dashboard precisa de `sudo` para alguns comandos de diagnóstico
- Container roda como root (padrão Docker)
- Arquivos criados pertencem ao root

---

## 📊 Estrutura de Metadados (.metadata.json)

```json
{
  "1.2.840.113704.1.111.5396.1769089135": {
    "folder": "20260122_141530_P001_DOE_JOHN",
    "patient_id": "P001",
    "patient_name": "DOE_JOHN",
    "study_uid": "1.2.840.113704.1.111.5396.1769089135",
    "study_date": "20260122",
    "study_time": "141530",
    "modality": "CT",
    "created_at": "20260122_141530",
    "image_count": 245,
    "study_description": "CHEST CT WITH CONTRAST",
    "sent": true,
    "sent_at": "20260122_141845"
  }
}
```

---

## 🔍 Testes Recomendados

### 1. Teste de Recepção
```bash
# Enviar arquivo de teste
dcmsend 172.22.61.14 104 test.dcm

# Verificar se foi organizado
ls -la /home/prowess/dicomrs/dicom/
cat /home/prowess/dicomrs/dicom/.metadata.json
```

### 2. Teste de Dashboard
```bash
# Acessar dashboard
curl http://localhost:8501

# Verificar logs
sudo docker compose logs dashboard
```

### 3. Teste de Envio
```bash
# Verificar se SCU está processando pastas
sudo docker compose logs -f storescu
```

---

## 📞 Suporte

Para problemas, consulte:
1. `TROUBLESHOOTING.md` - Guia de resolução de problemas
2. Logs do Docker: `sudo docker compose logs`
3. Dashboard de diagnóstico: `http://IP:8501` → Aba "Diagnóstico"

---

**Última atualização:** 22/01/2026
