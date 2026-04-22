# Buscapés GymRats

Site de resultados do **Campeonato Buscapés das Estações 2026**, uma
competição familiar de exercício físico via [GymRats](https://gymrats.app).

Publicado em [buscapes.gymrats.l2n.me](https://buscapes.gymrats.l2n.me).

## O que tem no site

- **Ranking** com pódio, tabela completa e gráfico da corrida ao longo
  do tempo
- **Estatísticas** com gráficos de evolução mensal, dia da semana,
  atividades mais populares, destaques por modalidade (corrida,
  musculação, surfe, natação, ciclismo) e detalhes com distância,
  calorias e horas por esporte
- **Ranking anual** estilo WSL com colunas por estação
- **Regulamento** completo do campeonato
- **Destaques** individuais para todos os 15 participantes

## Desenvolvimento

Requisitos: [Hugo](https://gohugo.io/) 0.156+ e Python 3.

```bash
# Gerar dados e iniciar servidor local
make run

# Apenas gerar dados
make data

# Build de produção
make build
```

## Como funciona

Os dados são exportados do app GymRats em JSON
(`resources/challenge-data.json`). Um script Python
(`scripts/process_data.py`) processa esse JSON e gera arquivos em
`data/` que o Hugo usa para renderizar os gráficos e tabelas.

O script classifica atividades, funde sessões próximas, converte
fusos horários e estima valores faltantes (duração, distância,
calorias) usando médias por modalidade.

## Deploy

Pushes para `main` disparam deploy automático via GitHub Actions.
O workflow roda o script de preprocessamento antes de buildar com
`hugo --minify` e publica no GitHub Pages.

## Adicionando uma nova estação

1. Exporte os dados da nova etapa do GymRats
2. Substitua `resources/challenge-data.json` (ou adapte o script
   para múltiplos arquivos)
3. Atualize os parâmetros da estação em `hugo.toml` (`season`,
   `seasonEmoji`, datas)
4. Rode `make run` para verificar
5. Commit e push para deploy
