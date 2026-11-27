# revela

Nunca abra fotos nem PDFs de `data/`. Tudo o que você lê vai para o provedor do modelo, e as fotos são de uma criança. Trabalhe só com a saída de texto dos comandos.

- O `revela dupes` escolhe a melhor foto de cada grupo de parecidas. Se o relatório parecer errado, ajuste `--seconds`, `--distance`, `--blur` ou `--dark` e rode de novo.
- O `dupes` não sobrescreve escolhas com `"by": "voce"`. Você também não deve sobrescrever: essas escolhas são da pessoa.
- Depois de mudar escolhas, rode `revela apply` antes do `fotobuch build`.
- Para ajustar o layout, peça à pessoa para olhar o preview (link "ver o álbum" no picker) e responder com endereços `página:slot`, que aparecem em cada foto.
