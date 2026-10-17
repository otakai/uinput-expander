# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [0.1.4] — 2026-10-17

### Alterado

- **Sem rede de segurança, de propósito.** A revisão periódica de 5 min saiu: se o vigia de eventos
  parar de avisar, o defeito tem de **aparecer**, não ser mascarado por um relógio. Se o `inotify` não
  puder ser criado, o expansor agora **falha na hora** (`exit 1`), com uma linha `ERRO` no log, e o
  systemd marca o serviço como `failed` — visível, em vez de funcionar pela metade.
- **O log nomeia o que mudou**: `entrou: /dev/input/event17 (teste-nome-final-hermes)` e
  `saiu: … (nome)`. O nome do que sai vem de um cache, porque quando o nó desaparece o `/sys` já não
  responde por ele.

## [0.1.3] — 2026-10-17

### Alterado

- **A descoberta de dispositivos deixou de ser por polling.** O `0.1.2` reconferia a cada 10 s; agora
  um `inotify` em `/dev/input` (via `ctypes`, sem dependências) faz o **kernel avisar** no instante em
  que um nó entra ou sai, e os handles são reabertos ~0,3 s depois do último aviso. Reação medida:
  dispositivo criado às 12:31:02.711 → log reagindo às 12:31:03; destruído às 12:31:07.062 → log às
  12:31:07. A revisão periódica caiu para 5 min e ficou só como rede de segurança.

## [0.1.2] — 2026-10-17

### Corrigido

- **O expansor ficava surdo, em silêncio, quando os dispositivos de teclado mudavam de número.**
  Aplicativos de ditado recriam os teclados virtuais quando a sessão reinicia, e os índices
  `/dev/input/event*` mudam. O processo continuava lendo os handles antigos, sem tecla nenhuma,
  com o serviço `active` e sem uma linha de erro no log. Agora o conjunto de dispositivos é
  reconferido a cada 10 s e reaberto quando muda (testado criando e destruindo um teclado virtual).

## [Não publicado]

- Mapa de teclas para outros layouts (`tools/calibrar.py` faz a medição em um minuto).

## [0.1.0] — 2026-10-16

Primeira versão publicada.

### Adicionado

- Detecção pelo `evdev`, lendo apenas os dispositivos marcados como teclado pelo `udev`,
  com descoberta dinâmica (os índices `event*` mudam entre reinicializações).
- Injeção por teclado virtual `uinput`: sem clipboard, sem root, sem X11, sem portal.
- Configuração por `gatilhos.tsv` (gatilho + substituição), com exemplo neutro.
- Instalador de usuário e serviço `systemd` (`install.sh`).
- Ferramenta de calibração de layout (`tools/calibrar.py`).
- Mapa do teclado brasileiro medido por sonda, incluindo as sequências de tecla morta e os
  símbolos `: " ^ < > / ? \ |`.
- Todos os códigos de tecla declarados no teclado virtual (`UI_SET_KEYBIT` de 1 a 255):
  declarar só os que estão no mapa faz o kernel descartar os outros **em silêncio**.
- Mapa de teclas estrangeiro: ignorar os teclados virtuais de aplicativos de ditado.

### Corrigido

- Piscada de "quadradinho" perto do cursor: era o caminho de clipboard do espanso,
  eliminado por construção neste projeto.
- Expansão no **soltar** da tecla, com 40 ms de margem: expandir no apertar colidia com a
  tecla ainda pressionada e o aplicativo comia caractere (o `c` de *Bacharelado*).
- 2 ms entre apertar e soltar cada tecla: sem isso, alguns aplicativos leem repetição.
- Folga entre tecla morta e vogal, para a composição de acentos completar.
