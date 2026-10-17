#!/usr/bin/env python3
"""
expansor-wayland — expansor de texto próprio, feito para o GNOME no Wayland.

Desenho (por que não é o Espanso): a injeção aqui é SEMPRE por uinput (teclado virtual
no kernel) — nunca pelo clipboard. Foi o uso do clipboard que produzia aquele quadradinho
piscando perto do cursor. Detecção por leitura direta de /dev/input (grupo input), portanto
sem XRecord, sem X11, sem portal.

Como funciona:
  1. lê os teclados físicos (event1 = interno, event3 = Logitech MK270);
  2. mantém uma janela dos últimos caracteres digitados, interpretando o layout br;
  3. quando o texto termina com um gatilho da lista, apaga o gatilho (backspace) e digita
     a substituição pelo uinput;
  4. registra tudo em ~/.cache/expansor/expansor.log.

Config:  ~/.config/expansor/gatilhos.tsv   (uma linha por gatilho:  gatilho<TAB>texto)
"""
import json
import os
import select
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uinput_type import K, SHIFTED, SHIFT_EXTRA, Teclado  # noqa: E402

EV_KEY = 1
def descobrir_teclados():
    """Todos os /dev/input/event* que o udev marca como teclado (índices mudam entre boots)."""
    import subprocess
    devs = []
    for i in range(64):
        d = "/dev/input/event%d" % i
        if not os.path.exists(d):
            continue
        try:
            props = subprocess.run(["udevadm", "info", "-q", "property", "-n", d],
                                   capture_output=True, text=True, timeout=3).stdout
        except Exception:
            continue
        # inclui teclados reais e também os virtuais do Solaar/MK270
        if "ID_INPUT_KEYBOARD=1" in props or "ID_INPUT_KEY=1" in props:
            nome = ""
            try:
                with open("/sys/class/input/%s/device/name" % os.path.basename(d)) as f:
                    nome = f.read().strip()
            except Exception:
                pass
            # nunca ler a si mesmo (laço infinito) nem os teclados virtuais do Typeless
            if nome in ("expansor-hermes",):
                log("ignorando dispositivo %s (%s)" % (d, nome))
                continue
            devs.append(d)
    return devs or ["/dev/input/event1", "/dev/input/event3"]
CONFIG = os.path.expanduser("~/.config/expansor/gatilhos.tsv")
LOG = os.path.expanduser("~/.cache/expansor/expansor.log")
MAXBUF = 48

# keycode evdev -> caractere (sem shift) no layout br
CHAR = {}
for ch, code in K.items():
    if len(ch) == 1 and ch.isalnum():
        CHAR.setdefault(code, ch)
for sym, base in {".": ".", ",": ",", "-": "-", "=": "=", "/": "/", ";": ";", " ": " ",
                  "'": "'", "[": "[", "]": "]", "\\": "\\", "`": "`"}.items():
    CHAR[K[sym]] = base
CHAR[K[" "]] = " "

# no layout br, algumas posições produzem outro símbolo
BR_EXTRA = {39: "ç", 40: "~" , 41: "'", 43: "]", 26: "[", 27: "]", 12: "-", 13: "="}

# acentos: código da tecla morta (ou "SHIFT" + código) e a vogal
ACENTO = {
    "á": (26, K["a"]), "é": (26, K["e"]), "í": (26, K["i"]), "ó": (26, K["o"]), "ú": (26, K["u"]),
    "ã": (40, K["a"]), "õ": (40, K["o"]),
    "â": ("S", K["6"]), "ê": ("S", K["6"]), "î": ("S", K["6"]), "ô": ("S", K["6"]), "û": ("S", K["6"]),
    "ç": (39, None),
}
VOGAIS_CIRC = {"a": K["a"], "e": K["e"], "i": K["i"], "o": K["o"], "u": K["u"], "A": K["a"], "E": K["e"]}


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("%s %s\n" % (time.strftime("%d/%m %H:%M:%S"), msg))


def carregar_gatilhos():
    g = []
    if os.path.exists(CONFIG):
        with open(CONFIG, encoding="utf-8") as f:
            for linha in f:
                if not linha.strip() or linha.startswith("#"):
                    continue
                partes = linha.rstrip("\n").split("\t", 1)
                if len(partes) == 2:
                    g.append((partes[0], partes[1]))
    g.sort(key=lambda t: -len(t[0]))       # gatilhos mais longos primeiro
    return g


def digitar_texto(kb, texto):
    """Usa o mesmo motor do uinput_type (uma fonte só de verdade)."""
    kb.digitar(texto, pausa=0.011, pausa_acento=0.045)


# --- vigia de /dev/input por inotify: quem avisa é o kernel, não um relógio ---
# O polling ("olhar a cada 10 s") é um palpite sobre QUANDO mudou. Aqui o kernel avisa no
# instante em que um nó entra ou sai de /dev/input, e só então reabrimos. Sem dependências:
# inotify pela libc com ctypes.
IN_CREATE, IN_DELETE, IN_MOVED_FROM, IN_MOVED_TO, IN_ATTRIB = 0x100, 0x200, 0x40, 0x80, 0x04


def criar_vigia_input(caminho="/dev/input"):
    """Abre um fd de inotify observando o diretório. Devolve None se não for possível."""
    try:
        import ctypes
        import ctypes.util
        libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
        libc.inotify_init1.restype = ctypes.c_int
        fd = libc.inotify_init1(0x800)          # IN_NONBLOCK
        if fd < 0:
            return None
        mascara = IN_CREATE | IN_DELETE | IN_MOVED_FROM | IN_MOVED_TO | IN_ATTRIB
        if libc.inotify_add_watch(fd, caminho.encode(), mascara) < 0:
            os.close(fd)
            return None
        return fd
    except Exception:
        return None


nomes_dispositivos = {}


def _nome_dispositivo(caminho):
    """Nome do dispositivo; guarda em cache porque, quando ele sai, o /sys já não responde."""
    if caminho in nomes_dispositivos:
        return nomes_dispositivos[caminho]
    try:
        nome = open("/sys/class/input/%s/device/name" % os.path.basename(caminho)).read().strip()
    except Exception:
        nome = "?"
    nomes_dispositivos[caminho] = nome
    return nome


def main():
    gatilhos = carregar_gatilhos()
    log("iniciando com %d gatilhos" % len(gatilhos))
    if not gatilhos:
        log("nenhum gatilho em %s — encerrando" % CONFIG)
        return 1

    fds = {}
    for dev in descobrir_teclados():
        try:
            fds[os.open(dev, os.O_RDONLY | os.O_NONBLOCK)] = dev
        except OSError as e:
            log("não abriu %s: %s" % (dev, e))
    if not fds:
        log("nenhum teclado acessível — encerrando")
        return 1

    kb = Teclado("expansor-hermes")
    buf = ""
    shift = False
    log("pronto; teclados: %s" % ", ".join(fds.values()))
    ifd = criar_vigia_input()
    if ifd is None:
        # SEM fallback, de propósito. Uma rede de segurança esconde exatamente o defeito que
        # interessa: se o vigia de eventos não sobe, o expansor funciona pela metade e o dono só
        # descobre quando para de expandir, sem nada no log. Falhar aqui, alto e na hora, mantém
        # o problema evidente — e o systemd marca o serviço como failed, que é visível.
        log("ERRO: não foi possível criar o vigia de /dev/input por inotify. Sem ele não há como "
            "reabrir os dispositivos quando mudarem. Falhando de propósito, sem fallback.")
        return 1
    log("vigia de /dev/input ativo (inotify) — reabre na hora em que um dispositivo entra ou sai")
    motivo_rescan = 0.0

    try:
        while True:
            espera = [ifd] if ifd is not None else []
            r, _, _ = select.select(list(fds.keys()) + espera, [], [], 1.0)
            # Quem avisa que um dispositivo entrou ou saiu de /dev/input é o KERNEL (inotify), não
            # um relógio. O aplicativo de ditado recria os teclados virtuais quando a sessão
            # reinicia e os índices event* mudam: ler só no start deixa o expansor SURDO, com o
            # serviço active e sem uma linha de erro.
            if ifd is not None and ifd in r:
                try:
                    os.read(ifd, 4096)              # drena, senão o select fica sempre pronto
                except OSError:
                    pass
                motivo_rescan = time.time()
            # Reabre 0,3 s depois do último aviso (o udev cria/renomeia em rajada). Não há
            # revisão periódica: se o kernel deixar de avisar, o defeito tem de aparecer, não ser
            # mascarado por um relógio.
            if motivo_rescan and time.time() - motivo_rescan > 0.3:
                motivo_rescan = 0.0
                try:
                    atuais = descobrir_teclados()
                except Exception:
                    atuais = list(fds.values())
                if set(atuais) != set(fds.values()):
                    entraram = sorted(set(atuais) - set(fds.values()))
                    sairam = sorted(set(fds.values()) - set(atuais))
                    log("dispositivos mudaram; reabrindo (%d -> %d)" % (len(fds), len(atuais)))
                    for d in entraram:
                        log("  entrou: %s (%s)" % (d, _nome_dispositivo(d)))
                    for d in sairam:
                        # o nó já saiu do /sys, então o nome vem do cache do scan anterior
                        log("  saiu:   %s (%s)" % (d, nomes_dispositivos.get(d, "?")))
                    for fd in list(fds):
                        try:
                            os.close(fd)
                        except OSError:
                            pass
                    fds.clear()
                    for dev in atuais:
                        try:
                            fds[os.open(dev, os.O_RDONLY | os.O_NONBLOCK)] = dev
                        except OSError:
                            continue
                    log("pronto; teclados: %s" % ", ".join(sorted(fds.values())))
            for fd in r:
                if fd == ifd:                       # o fd do inotify não é evento de teclado
                    continue
                try:
                    dados = os.read(fd, 24 * 64)
                except OSError:
                    continue
                for off in range(0, len(dados) - 23, 24):
                    _, _, etype, code, value = struct.unpack_from("llHHi", dados, off)
                    if etype != EV_KEY:
                        continue
                    if code == K["shift"]:
                        shift = value != 0
                        continue
                    if value == 0:
                        # SOLTOU a tecla: agora é seguro expandir. Se expandíssemos no apertar,
                        # os backspaces colidiriam com a tecla ainda presa e o aplicativo comeria
                        # caractere (era o 'c' de Bacharelado que sumia).
                        for gat, rep in gatilhos:
                            if buf.endswith(gat):
                                time.sleep(0.04)          # o app processar o soltar
                                log("gatilho %r -> %d caracteres" % (gat, len(rep)))
                                for _ in range(len(gat)):
                                    kb.key(K["backspace"]); time.sleep(0.008)
                                digitar_texto(kb, rep)
                                buf = ""
                                break
                        continue
                    if value != 1:            # ignora repetição (value=2)
                        continue
                    ch = CHAR.get(code) or BR_EXTRA.get(code, "")
                    if not ch:
                        continue
                    if shift and ch.isalpha():
                        ch = ch.upper()
                    elif shift and ch in BR_EXTRA.values():
                        ch = {";": ":", "'": '"', "~": "^", "[": "{", "ç": ":"}.get(ch, ch)
                    buf = (buf + ch)[-MAXBUF:]
    except KeyboardInterrupt:
        pass
    finally:
        kb.fechar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
