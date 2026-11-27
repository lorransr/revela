# revela

Monta um fotolivro a partir de um álbum do iCloud sem tirar as fotos do seu computador.
Usa o [icloudpd](https://github.com/icloud-photos-downloader/icloud_photos_downloader)
para baixar e o [fotobuch](https://github.com/EddyXorb/fotobuch) para diagramar.

## Uso

```bash
cp .env.example .env                      # preencha
mkdir -p data/photos data/selected data/books
docker compose run --rm sync --auth-only  # login e 2FA; repita quando a Apple pedir

docker compose run --rm sync              # baixa o álbum (e as fotos novas, nas próximas vezes)
docker compose run --rm revela dupes      # sugere o que sai: parecidas, tremidas e escuras
docker compose up picker                  # revise em http://127.0.0.1:8765: ← fora, → dentro, ou arraste

docker compose run --rm -w /books fotobuch project new livro --width 297 --height 210   # só na primeira vez
docker compose run --rm revela apply      # leva as escolhas para o livro

alias fb='docker compose run --rm fotobuch'
fb build                                  # preview: link "ver o álbum" no picker
fb build release                          # PDF final, 300 DPI
```

Os outros comandos estão na [documentação do fotobuch](https://eddyxorb.github.io/fotobuch).

## Privacidade

- O `sync` acessa a rede só para falar com a Apple. O `revela` e o `fotobuch` rodam sem rede.
- O `picker` precisa de rede para abrir a porta, mas só escuta em `127.0.0.1`, só aceita `Host` local e não carrega nada de fora: o htmx está em `static/`.
- `data/session` dá acesso a todas as suas fotos do iCloud. Não copie esse diretório para fora da máquina.
- Um agente com LLM na nuvem envia ao provedor cada foto ou PDF que abre.
  `.claude/settings.json` bloqueia a ferramenta Read em `data/`, mas comandos de shell como `cat` não passam por essa regra.
