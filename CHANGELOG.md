# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [Não publicado]

- Mapear `/` e `?` no layout brasileiro (faltam; `tools/calibrar.py` faz a medição).

## [0.1.0] — 2026-10-16

Primeira versão publicada.

### Adicionado

- Detecção pelo `evdev`, lendo apenas os dispositivos marcados como teclado pelo `udev`,
  com descoberta dinâmica (os índices `event*` mudam entre reinicializações).
- Injeção por teclado virtual `uinput`: sem clipboard, sem root, sem X11, sem portal.
- Configuração por `gatilhos.tsv` (gatilho + substituição), com exemplo neutro.
- Instalador de usuário e serviço `systemd` (`install.sh`).
- Ferramenta de calibração de layout (`tools/calibrar.py`).
- Mapa do teclado brasileiro medido por sonda, incluindo as sequências de tecla morta.
- Mapa de teclas estrangeiro: ignorar os teclados virtuais de aplicativos de ditado.

### Corrigido

- Piscada de "quadradinho" perto do cursor: era o caminho de clipboard do espanso,
  eliminado por construção neste projeto.
- Expansão no **soltar** da tecla, com 40 ms de margem: expandir no apertar colidia com a
  tecla ainda pressionada e o aplicativo comia caractere (o `c` de *Bacharelado*).
- 2 ms entre apertar e soltar cada tecla: sem isso, alguns aplicativos leem repetição.
- Folga entre tecla morta e vogal, para a composição de acentos completar.
