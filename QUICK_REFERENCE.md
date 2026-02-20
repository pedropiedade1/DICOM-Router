# 🎯 Guia Rápido - DICOM Router v2.0

## 📌 Comandos Essenciais

### Status dos Serviços
```bash
cd /home/prowess/dicomrs
sudo docker compose ps                    # Ver status de todos
sudo docker compose logs -f               # Logs em tempo real
sudo docker compose logs -f storescp      # Logs só do recebimento
sudo docker compose logs -f storescu      # Logs só do envio
```

### Reiniciar Serviços
```bash
sudo docker compose restart               # Reinicia todos (~10s)
sudo docker compose restart storescp      # Só recebimento
sudo docker compose restart storescu      # Só envio
sudo docker compose down && sudo docker compose up -d  # Restart completo (~20s)
```

### Verificar Conectividade
```bash
# Rede HTR (Tomografia)
ping 172.22.61.14
sudo netstat -tlnp | grep :104

# Rede Clínica (Zero Click)
ping 192.168.10.16
telnet 192.168.10.16 4243

# Rotas
ip route show

# Interfaces
ip addr show
```

### Monitorar Fila
```bash
# Quantos arquivos na fila
ls -l /home/prowess/dicomrs/dicom/ | wc -l

# Tamanho total
du -sh /home/prowess/dicomrs/dicom/

# Pastas organizadas
ls -la /home/prowess/dicomrs/dicom/

# Metadados
cat /home/prowess/dicomrs/dicom/.metadata.json | jq .
```

### Verificar Portas
```bash
sudo netstat -tlnp | grep -E ":104|:4100|:8501|:4243"
```

### Verificar Espaço em Disco
```bash
df -h /home/prowess/dicomrs/dicom/
```

---

## 🔧 Troubleshooting Rápido

### Problema: Porta 104 não escuta
```bash
sudo docker compose restart storescp
sudo netstat -tlnp | grep :104
```

### Problema: Arquivos acumulando
```bash
# Ver logs de envio
sudo docker compose logs --tail=50 storescu

# Testar conectividade
ping 192.168.10.16
telnet 192.168.10.16 4243

# Reiniciar envio
sudo docker compose restart storescu
```

### Problema: Disco cheio
```bash
# Verificar espaço
df -h

# Ver arquivos antigos
ls -lt /home/prowess/dicomrs/dicom/ | tail -20

# CUIDADO: Limpar manualmente se necessário
# (apenas se tiver certeza que foram enviados)
cd /home/prowess/dicomrs/dicom/
sudo rm -rf PASTA_ANTIGA/
```

### Problema: Dashboard não abre
```bash
sudo docker compose restart dashboard
sudo docker compose logs dashboard
curl http://localhost:8501
```

---

## 🌐 URLs Importantes

- **Dashboard:** http://172.22.61.14:8501
- **Dashboard (rede clínica):** http://192.168.12.35:8501

---

## 📊 Estrutura de Pastas v2.0

```
dicomrs/
├── docker-compose.yml           # Orquestração
├── .env                         # Configurações (HTR_IP, TARGET_HOST, etc)
├── dicom/                       # Dados DICOM
│   ├── .metadata.json           # ← NOVO: Metadados dos estudos
│   ├── 20260122_141530_P001_DOE_JOHN/    # ← NOVO: Organizado por paciente
│   │   ├── CT.xxx.dcm
│   │   └── ...
│   └── 20260122_142015_P002_SMITH_JANE/
│       └── ...
├── scp/
│   ├── Dockerfile
│   ├── receive.sh
│   ├── organizer.py             # ← NOVO: Organizador automático
│   └── storescp.cfg
├── scu/
│   ├── Dockerfile
│   ├── scu_script.py            # v1.0 (original)
│   └── scu_script_v2.py         # ← NOVO: v2.0 com suporte a pastas
├── dashboard/
│   ├── Dockerfile
│   ├── app.py                   # v1.0 (original)
│   └── app_v2.py                # ← NOVO: Dashboard avançado
├── TROUBLESHOOTING.md           # ← NOVO: Guia de troubleshooting
├── IMPLEMENTATION_NOTES.md      # ← NOVO: Notas técnicas
├── UPGRADE_SUMMARY.md           # ← NOVO: Resumo das melhorias
├── QUICK_REFERENCE.md           # ← Este arquivo
└── upgrade_to_v2.sh             # ← NOVO: Script de atualização
```

---

## ⚙️ Configurações (.env)

```bash
# IP da interface de rede HTR (onde quer receber DICOM na porta 104)
HTR_IP=172.22.61.14

# Configurações do destino (Zero Click)
TARGET_HOST=192.168.10.16
TARGET_PORT=4243
TARGET_AET=ZEROCLICK
```

---

## 📋 Checklist de Verificação Diária

- [ ] Containers rodando? `sudo docker compose ps`
- [ ] Porta 104 OK? `sudo netstat -tlnp | grep :104`
- [ ] Ping HTR OK? `ping 172.22.61.14`
- [ ] Ping Zero Click OK? `ping 192.168.10.16`
- [ ] Fila normal? `ls dicom/ | wc -l` (deve ser baixo)
- [ ] Disco OK? `df -h` (> 20% livre)
- [ ] Dashboard OK? Abrir no navegador
- [ ] Logs sem erros? `docker compose logs --tail=50`

---

## 🚀 Atualizar para v2.0

```bash
cd /home/prowess/dicomrs
./upgrade_to_v2.sh
```

Ou leia: [UPGRADE_SUMMARY.md](UPGRADE_SUMMARY.md)

---

## 📖 Documentação Completa

1. **[README.md](README.md)** - Documentação principal (original)
2. **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - ⭐ Guia completo de troubleshooting
3. **[IMPLEMENTATION_NOTES.md](IMPLEMENTATION_NOTES.md)** - Detalhes técnicos da v2.0
4. **[UPGRADE_SUMMARY.md](UPGRADE_SUMMARY.md)** - Resumo das melhorias
5. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Este guia rápido

---

## 🆘 Emergência

### Sistema não funciona após atualização
```bash
cd /home/prowess/dicomrs
sudo docker compose down
cp backup_*/docker-compose.yml .
sudo docker compose up -d
```

### Gerar relatório de diagnóstico
```bash
cd /home/prowess/dicomrs
bash -c '
echo "=== DIAGNÓSTICO ===" > diagnostic.txt
sudo docker compose ps >> diagnostic.txt
sudo netstat -tlnp | grep -E ":104|:4100|:8501" >> diagnostic.txt
ip route show >> diagnostic.txt
df -h >> diagnostic.txt
sudo docker compose logs --tail=50 >> diagnostic.txt
cat diagnostic.txt
'
```

### Contato
- Documentação: Ver arquivos `.md` neste diretório
- Logs: `sudo docker compose logs`
- Dashboard diagnóstico: http://IP:8501 → Aba "Diagnóstico"

---

**Última atualização:** 22/01/2026  
**Versão:** 2.0
