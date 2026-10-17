# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

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
