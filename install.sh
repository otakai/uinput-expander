#!/bin/bash
# uinput-expander — instalador para usuário (sem root)
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/bin/expansor"
CONF="$HOME/.config/expansor"

echo "==> instalando em $DEST"
mkdir -p "$DEST" "$CONF" "$HOME/.cache/expansor"
install -m 644 "$SRC/src/uinput_type.py" "$DEST/"
install -m 755 "$SRC/src/expansor.py"     "$DEST/"
install -m 755 "$SRC/tools/calibrar.py"   "$DEST/"

if [ ! -f "$CONF/gatilhos.tsv" ]; then
    install -m 644 "$SRC/examples/gatilhos.tsv" "$CONF/gatilhos.tsv"
    echo "==> exemplo de configuração criado em $CONF/gatilhos.tsv (edite à vontade)"
fi

echo "==> instalando o serviço de usuário"
mkdir -p "$HOME/.config/systemd/user"
sed "s|%h/.local/bin/expansor/expansor.py|$DEST/expansor.py|" \
    "$SRC/systemd/expansor.service" > "$HOME/.config/systemd/user/expansor.service"
systemctl --user daemon-reload
systemctl --user enable --now expansor.service

echo
echo "==> verificação"
systemctl --user is-active expansor.service
if ! id -nG | grep -qw input; then
    echo "ATENÇÃO: seu usuário não está no grupo 'input'. Rode:"
    echo "    sudo usermod -aG input \"$USER\"    (depois saia e entre de novo)"
fi
echo "Log:  ~/.cache/expansor/expansor.log"
echo "Teste: digite um gatilho em qualquer aplicativo."
