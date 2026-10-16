#!/usr/bin/env python3
"""
Calibração do expansor: mede o menor intervalo entre teclas que NÃO perde caractere.

Para cada intervalo, abre uma janela de teste (zenity), digita uma frase com acentos e os
símbolos mais difíceis via uinput, e compara o que a janela recebeu com o esperado.
O resultado vai para /tmp/calibracao-expansor.txt.

Enquanto roda, não use o teclado: a janela rouba o foco.
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, "~/.local/bin/expansor")
from uinput_type import K, Teclado  # noqa: E402

AMOSTRA = 'Bacharelado em Ciencia da Computacao: "TDD" 12,3 - _ @ # . < > á ã ç ê'
PAUSAS = [0.025, 0.020, 0.016, 0.012, 0.010, 0.008, 0.006, 0.004]
SAIDA = "/tmp/calibracao-expansor.txt"


def main():
    env = dict(os.environ)
    env.update(DISPLAY=":0", WAYLAND_DISPLAY="wayland-0", XDG_RUNTIME_DIR="/run/user/1000")
    linhas = []
    for pausa in PAUSAS:
        proc = subprocess.Popen(
            ["zenity", "--entry", "--timeout=25", "--width=900",
             "--title=Calibracao do expansor - %.0f ms" % (pausa * 1000),
             "--text=Nao digite no teclado agora"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        time.sleep(2.0)                       # dar tempo do foco
        kb = Teclado()
        try:
            kb.digitar(AMOSTRA, pausa=pausa)
            kb.key(K["enter"])
        finally:
            kb.fechar()
        try:
            recebido, _ = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            recebido = ""
        recebido = (recebido or "").strip()
        ok = recebido == AMOSTRA
        linha = "%.3f s (%2.0f ms) -> %s  recebidos %d de %d" % (
            pausa, pausa * 1000, "OK" if ok else "FALHOU", len(recebido), len(AMOSTRA))
        linhas.append(linha)
        print("  " + linha, flush=True)
        if not ok:
            # mostra a primeira diferença, para diagnóstico
            for i, (a, b) in enumerate(zip(AMOSTRA, recebido)):
                if a != b:
                    print("     primeira diferença no %dº caractere: esperado %r, veio %r" % (i + 1, a, b), flush=True)
                    break
            if len(recebido) < len(AMOSTRA):
                print("     faltaram caracteres a partir de: %r" % AMOSTRA[len(recebido):len(recebido) + 20], flush=True)
        with open(SAIDA, "w", encoding="utf-8") as f:
            f.write("\n".join(linhas) + "\n")
        time.sleep(0.8)
    return 0


if __name__ == "__main__":
    sys.exit(main())
