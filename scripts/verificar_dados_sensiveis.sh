#!/usr/bin/env bash
# =============================================================
# NoiseDC — auditoria de dados sensíveis antes da publicação
#
# Varre a árvore de trabalho em busca de credenciais, endereços
# e identificadores institucionais que não devem ir a público.
# NÃO substitui uma revisão manual, mas pega a maior parte dos casos.
#
# Uso:
#   bash scripts/verificar_dados_sensiveis.sh          # árvore atual
#   bash scripts/verificar_dados_sensiveis.sh --historico   # inclui histórico Git
# =============================================================
set -uo pipefail

VERMELHO='\033[0;31m'; AMARELO='\033[0;33m'; VERDE='\033[0;32m'; NEUTRO='\033[0m'
ACHADOS=0
EXCLUIR="--exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules \
--exclude-dir=__pycache__ --exclude=*.wav --exclude=*.npy --exclude=*.png \
--exclude=verificar_dados_sensiveis.sh"

buscar() {
  local rotulo="$1" padrao="$2" severidade="${3:-alta}"
  local saida
  saida=$(grep -rInE $EXCLUIR "$padrao" . 2>/dev/null | grep -vE '\.example|PREENCHER|<[A-Z_]+>|XXXX' | head -20)
  if [[ -n "$saida" ]]; then
    ACHADOS=$((ACHADOS+1))
    if [[ "$severidade" == "alta" ]]; then
      echo -e "${VERMELHO}[CRÍTICO] ${rotulo}${NEUTRO}"
    else
      echo -e "${AMARELO}[REVISAR] ${rotulo}${NEUTRO}"
    fi
    echo "$saida" | sed 's/^/    /'
    echo
  fi
}

echo "==============================================="
echo " Auditoria de dados sensíveis — $(date '+%Y-%m-%d %H:%M')"
echo "==============================================="
echo

# ---- 1. Credenciais ----
buscar "Senhas, tokens e chaves de API" \
  '(senha|password|passwd|pwd|secret|token|api[_-]?key|apikey|auth[_-]?token)[[:space:]]*[:=][[:space:]]*[^[:space:]#]{4,}'
buscar "Chaves privadas embutidas" \
  'BEGIN (RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY'
buscar "Credenciais em URL (usuario:senha@host)" \
  'https?://[^/[:space:]]+:[^@[:space:]]+@'

# ---- 2. Infraestrutura ----
buscar "Comunidades SNMP em texto claro" \
  '(community|comunidade)[[:space:]]*[:=][[:space:]]*[^[:space:]#]+|snmp.*(public|private)'
buscar "Endereços IP privados (RFC 1918)" \
  '\b(10\.[0-9]{1,3}|192\.168|172\.(1[6-9]|2[0-9]|3[01]))\.[0-9]{1,3}\.[0-9]{1,3}\b'
buscar "Endereços IP públicos" \
  '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' "media"
buscar "Endereços MAC" \
  '\b([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b' "media"
buscar "Nomes de host institucionais (.ufrn.br e afins)" \
  '[a-zA-Z0-9_.-]+\.(ufrn|imd)\.br' "media"
buscar "Portas de serviços de gerência" \
  ':(10050|10051|3000|161|162|22|389|636)\b' "media"

# ---- 3. Rede local do protótipo ----
buscar "SSID / senha de Wi-Fi" \
  '(ssid|wifi|wpa|psk)[[:space:]]*[:=][[:space:]]*[^[:space:]#]+'

# ---- 4. Dados pessoais ----
buscar "Endereços de e-mail" \
  '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' "media"
buscar "CPF / matrícula / SIAPE" \
  '\b[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}\b|\b(matricula|siape)[[:space:]]*[:=]' "media"

echo "-----------------------------------------------"

# ---- 5. Arquivos que não deveriam existir na árvore ----
echo -e "${AMARELO}[ARQUIVOS] Verificando arquivos de risco...${NEUTRO}"
ARQ=$(find . -type f \( -name ".env" -o -name "*.pem" -o -name "*.key" \
  -o -name "id_rsa*" -o -name "credentials.json" -o -name "service-account*.json" \
  -o -name "*.psk" -o -name "zabbix_agentd.conf" \) -not -path "./.git/*" 2>/dev/null)
if [[ -n "$ARQ" ]]; then
  ACHADOS=$((ACHADOS+1))
  echo -e "${VERMELHO}    Arquivos sensíveis presentes:${NEUTRO}"
  echo "$ARQ" | sed 's/^/    /'
else
  echo "    Nenhum arquivo de credencial encontrado."
fi
echo

# ---- 6. Arquivos grandes ou de áudio prestes a ser versionados ----
echo -e "${AMARELO}[TAMANHO] Arquivos acima de 10 MB:${NEUTRO}"
find . -type f -size +10M -not -path "./.git/*" -not -path "./data/raw/*" \
  -exec ls -lh {} \; 2>/dev/null | awk '{print "    " $5 "  " $9}' | head -20
echo

# ---- 7. Histórico do Git (opcional) ----
if [[ "${1:-}" == "--historico" ]] && [[ -d .git ]]; then
  echo -e "${AMARELO}[HISTÓRICO] Procurando segredos em commits anteriores...${NEUTRO}"
  git rev-list --all 2>/dev/null | while read -r commit; do
    git grep -InE '(senha|password|token|api[_-]?key|BEGIN [A-Z]+ PRIVATE KEY)[[:space:]]*[:=]' \
      "$commit" -- 2>/dev/null | grep -v '\.example' | head -5
  done | sort -u | head -30
  echo
  echo "    Se houver achados acima, o histórico precisa ser reescrito"
  echo "    (git filter-repo) ou o repositório deve ser recriado do zero."
  echo
fi

echo "==============================================="
if [[ $ACHADOS -eq 0 ]]; then
  echo -e "${VERDE} Nenhuma ocorrência crítica automática detectada.${NEUTRO}"
  echo " Prossiga para a revisão manual do checklist."
else
  echo -e "${VERMELHO} $ACHADOS categoria(s) com ocorrências. NÃO publique${NEUTRO}"
  echo -e "${VERMELHO} antes de tratar cada uma delas.${NEUTRO}"
fi
echo "==============================================="
exit 0
