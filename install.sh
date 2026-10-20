#!/bin/bash
# uinput-expander — instalador para usuário (sem root)
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"

# Os programas ficam num diretório e o COMANDO é um arquivo com o nome "expansor".
# Caminhos diferentes de propósito: usar o mesmo para os dois faz o instalador morrer com
# "É um diretório" (foi o que aconteceu com o instalador do ditado-hermes na v0.1.3).
DEST="$HOME/.local/lib/expansor"
BIN="$HOME/.local/bin/expansor"
CONF="$HOME/.config/expansor"

# --- migração do layout antigo (~/.local/bin/expansor era um DIRETÓRIO com os .py) ---
if [ -d "$BIN" ]; then
    echo "==> migrando o layout antigo de $BIN para $DEST"
    mkdir -p "$DEST"
    for f in "$BIN"/*.py; do [ -e "$f" ] && mv -f "$f" "$DEST"/; done
    rm -rf "$BIN/__pycache__"
    if rmdir "$BIN" 2>/dev/null; then
        echo "==> diretório antigo removido"
    else
        echo "ERRO: $BIN ainda tem arquivos que não são .py. Mova-os e rode de novo." >&2
        exit 1
    fi
fi

echo "==> instalando em $DEST"
mkdir -p "$DEST" "$(dirname "$BIN")" "$CONF" "$HOME/.cache/expansor"
install -m 644 "$SRC/src/uinput_type.py" "$DEST/"
install -m 755 "$SRC/src/expansor.py"     "$DEST/"
install -m 755 "$SRC/tools/calibrar.py"   "$DEST/"
[ -f "$SRC/tools/captura-codigos.py" ] && install -m 755 "$SRC/tools/captura-codigos.py" "$DEST/"

echo "==> instalando o comando 'expansor' em $BIN"
install -m 755 "$SRC/bin/expansor" "$BIN"

if [ ! -f "$CONF/gatilhos.tsv" ]; then
    install -m 644 "$SRC/examples/gatilhos.tsv" "$CONF/gatilhos.tsv"
    echo "==> exemplo de configuração criado em $CONF/gatilhos.tsv (edite à vontade)"
fi

echo "==> instalando o serviço de usuário"
mkdir -p "$HOME/.config/systemd/user"
sed -e "s|%h/.local/bin/expansor/expansor.py|$DEST/expansor.py|" \
    -e "s|%h/.local/lib/expansor/expansor.py|$DEST/expansor.py|" \
    "$SRC/systemd/expansor.service" > "$HOME/.config/systemd/user/expansor.service"
systemctl --user daemon-reload
systemctl --user enable --now expansor.service
systemctl --user restart expansor.service || true

echo
echo "==> verificação"
echo "    serviço:  $(systemctl --user is-active expansor.service)"
echo "    programa: $DEST/expansor.py"
echo "    comando:  $BIN"
echo "    gatilhos: $(awk -F'\t' 'NF>=2 && $1 !~ /^[[:space:]]*#/ {n++} END{print n+0}' "$CONF/gatilhos.tsv" 2>/dev/null)"
if ! id -nG | grep -qw input; then
    echo "ATENÇÃO: seu usuário não está no grupo 'input'. Rode:"
    echo "    sudo usermod -aG input \"$USER\"    (depois saia e entre de novo)"
fi
echo
echo "Comandos:  expansor edit | restart | status | log | teste \"texto\""
echo "Log:       ~/.cache/expansor/expansor.log"
