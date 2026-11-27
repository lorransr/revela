# revela

Monta um fotolivro a partir de um álbum do iCloud sem tirar as fotos do seu computador.
Usa o [icloudpd](https://github.com/icloud-photos-downloader/icloud_photos_downloader)
para baixar e o [fotobuch](https://github.com/EddyXorb/fotobuch) para diagramar.

## Uso

```bash
cp .env.example .env                      # preencha
mkdir -p data/photos data/books
docker compose run --rm sync --auth-only  # login e 2FA; repita quando a Apple pedir
docker compose run --rm sync              # baixa o álbum; rode de novo para buscar fotos novas

docker compose run --rm -w /books fotobuch project new livro --width 297 --height 210

alias fb='docker compose run --rm fotobuch'
fb add -r /photos                               # cada dia vira um grupo
fb build                                        # preview em data/books/livro/livro.pdf
fb build release                                # PDF final, 300 DPI
```

Os outros comandos estão na [documentação do fotobuch](https://eddyxorb.github.io/fotobuch).

## Privacidade

- Só o serviço `sync` acessa a rede, e só para falar com a Apple.
- `data/session` dá acesso a todas as suas fotos do iCloud. Não copie esse diretório para fora da máquina.
- Um agente com LLM na nuvem envia ao provedor cada foto ou PDF que abre.
  `.claude/settings.json` bloqueia a ferramenta Read em `data/`, mas comandos de shell como `cat` não passam por essa regra.
