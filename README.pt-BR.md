🇺🇸 [Read in English](README.md)

<div align="center">

# Istara

**IA local para pesquisa de UX — agentes que aprendem, evoluem e trabalham para você.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/versão-2026.03.29-brightgreen.svg)](VERSION)
[![Platform](https://img.shields.io/badge/plataforma-macOS%20%7C%20Windows-lightgrey.svg)](installer/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](backend/)
[![Node](https://img.shields.io/badge/node-18%2B-green.svg)](frontend/)

[**Começar**](#início-rápido) · [**Arquitetura**](#arquitetura) · [**Skills**](#53-skills-de-pesquisa) · [**Agentes**](#5-agentes-de-ia) · [**Contribuir**](CONTRIBUTING.md)

---

*Seus dados de pesquisa nunca saem da sua máquina. Seus agentes ficam mais inteligentes a cada dia.*

</div>

---

## O que é o Istara?

O Istara é uma **plataforma de pesquisa com IA auto-evolutiva** que roda inteiramente no seu hardware. Ele vem com cinco agentes de IA especializados, 53 skills de pesquisa UX e uma metodologia completa de cadeia de evidências — tudo com inferência local de LLM (LM Studio ou Ollama).

Não há nuvem. Não há assinatura. Não há lock-in de fornecedor. Cada insight, cada transcrição, cada descoberta vive no seu banco de dados.

Os agentes melhoram a si mesmos com o tempo. As skills rastreiam seu próprio desempenho. A plataforma aprende suas preferências de fluxo de trabalho. E fica melhor quanto mais você usa.

---

## Por Que o Istara É Diferente

| Funcionalidade | Istara | Ferramentas Típicas de Pesquisa com IA |
|---|---|---|
| Privacidade de dados | 100% local — dados nunca saem | Upload para nuvem |
| Memória dos agentes | Personas persistentes e evolutivas | Sessões sem estado |
| Metodologia de pesquisa | Cadeia Atomic Research (Nuggets → Recomendações) | Ad-hoc |
| Melhoria de skills | Pontuações de qualidade auto-evolutivas | Prompts estáticos |
| Criação de agentes | Fábrica — crie agentes em tempo de execução | Conjunto fixo |
| Conformidade UX | Auditoria das 30 Leis de UX | Não disponível |
| Computação em equipe | Doe capacidade de GPU via relay WebSocket | Pague por chamada de API |
| Preço | Gratuito, open source | SaaS pago |

---

## Destaques Principais

### 🧠 5 Agentes de IA com Identidades Persistentes

Conheça sua equipe de pesquisa — agentes com nomes, memórias e especializações:

| Agente | Nome | Função |
|---|---|---|
| `istara-main` | **Cleo** | Pesquisadora principal. Executa todas as 53 skills, lidera projetos, fala com você |
| `istara-devops` | **Sentinel** | Guardião de integridade de dados. Monitora saúde, audita registros órfãos |
| `istara-ui-audit` | **Pixel** | Especialista em conformidade WCAG. Heurísticas de Nielsen, pontuação de acessibilidade |
| `istara-ux-eval` | **Sage** | Analista de carga cognitiva. Jornadas de usuário, detecção de fricção em fluxos |
| `istara-sim` | **Echo** | Testador end-to-end. Simula usuários, executa cenários de regressão |

Cada agente carrega quatro arquivos de persona — **CORE.md** (identidade), **SKILLS.md** (capacidades), **PROTOCOLS.md** (regras de comportamento), **MEMORY.md** (aprendizados acumulados) — e todos os quatro evoluem conforme o agente trabalha.

### 🔁 Agentes que Criam Outros Agentes

O Istara inclui uma **Fábrica de Agentes**: crie agentes de pesquisa personalizados em tempo de execução pela interface, defina sua persona, atribua skills, e eles entram imediatamente no pipeline de orquestração. Sem mudanças de código. Sem reinicializações.

O MetaOrchestrator coordena todos os agentes por um protocolo de mensagens A2A com roteamento tipado.

### 📈 53 Skills de Pesquisa que se Auto-Melhoram

Skills não são prompts estáticos. Cada skill:
- Tem um ciclo de vida `plan()` → `execute()` → `validate()`
- Rastreia qualidade de execução por combinação modelo × skill
- Exibe uma pontuação no **Monitor de Saúde de Skills** na interface
- Propõe automaticamente melhorias de prompt quando a qualidade cai abaixo do limite

As skills cobrem toda a metodologia do **Double Diamond**:

**Descobrir** — Entrevistas com Usuários, Pesquisa Contextual, Design de Survey, Gerador de Survey, Análise Competitiva, Estudos Diários, Estudos de Campo, Revisão de Analytics, Auditoria de Acessibilidade, Pesquisa Desk, Entrevistas com Stakeholders, Gerador de Perguntas para Entrevista, Deploy de Pesquisa por Canal, Detecção de IA em Survey

**Definir** — Análise Temática, Análise Temática Kappa, Mapeamento de Afinidade, Mapa de Empatia, Criação de Persona, Mapa de Jornada, Declarações HMW, Análise JTBD, Síntese de Pesquisa, Gerador de Taxonomia, Matriz de Priorização, Mapeamento de Fluxo do Usuário

**Desenvolver** — Teste de Usabilidade, Avaliação Heurística, Walkthrough Cognitivo, Teste de Conceito, Card Sorting, Tree Testing, Análise de Teste AB, Crítica de Design, Feedback de Protótipo, Facilitação de Workshop

**Entregar** — Auditoria de Design System, Pontuação SUS/UMUX, Análise de NPS, Apresentação para Stakeholders, Documentação de Handoff, Impacto de Regressão, Análise Quantitativa de Tarefas, Curadoria de Repositório, Retrospectiva de Pesquisa, Rastreamento Longitudinal

### 🔗 Cadeia de Evidências Atomic Research

Cada descoberta é rastreável desde a fonte bruta até a recomendação final:

```
Citação / observação (Nugget)
       ↓
Padrão verificado a partir de 2+ nuggets (Fato)
       ↓
Significado interpretado — "e daí?" (Insight)
       ↓
Proposta acionável com prioridade (Recomendação)
```

Nenhum insight sem proveniência. Cada recomendação se conecta pela cadeia de volta à citação exata que a sustenta.

### 🔍 RAG Híbrido: Busca Vetorial + por Palavra-chave

A recuperação usa uma mistura ponderada:
- **70% similaridade vetorial** (embeddings LanceDB)
- **30% busca por palavras-chave BM25**

Isso significa que o Istara encontra tanto conteúdo semanticamente similar quanto correspondências exatas de terminologia. Mude para modo vetorial puro ou por palavra-chave puro por consulta quando precisar.

### 🔒 Seus Dados, Seu Hardware

- LLMs locais via **LM Studio** (padrão) ou **Ollama**
- Banco de dados SQLite — um único arquivo, totalmente portátil
- Vector store LanceDB — embarcado, sem processo separado
- Servidor MCP **DESATIVADO por padrão** — ative apenas quando precisar de acesso externo de agentes
- Todos os uploads de arquivos processados localmente

---

## Arquitetura

```
┌──────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js 14)                   │
│   Chat · Kanban · Achados · Documentos · Skills · Agentes    │
│   22 visões · Onboarding contextual · Modo escuro/claro      │
└────────────────────────┬─────────────────────────────────────┘
                         │ REST + WebSocket (16 tipos de evento)
┌────────────────────────▼─────────────────────────────────────┐
│                      BACKEND (FastAPI)                        │
│                                                              │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐  │
│  │ 337 REST  │ │ WebSocket │ │ Servidor  │ │ Protocolo   │  │
│  │ endpoints │ │  Manager  │ │ MCP (opt) │ │ A2A         │  │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └──────┬──────┘  │
│        └─────────────┴─────────────┴───────────────┘        │
│                               │                              │
│  ┌────────────────────────────▼──────────────────────────┐   │
│  │                   MOTOR CENTRAL                       │   │
│  │  MetaOrchestrator · Hierarquia de Contexto (6 níveis) │   │
│  │  RAG Híbrido (LanceDB + BM25) · Compressor de Prompt  │   │
│  │  Auto-Evolução · Monitor de Saúde de Skills           │   │
│  │  Governador de Recursos · Sumarizador de Contexto DAG │   │
│  └────────────────────────────┬──────────────────────────┘   │
│                               │                              │
│  ┌─────────────────┐  ┌───────▼──────────┐  ┌────────────┐  │
│  │ Personas Agente │  │  Camada de Dados  │  │ Camada LLM │  │
│  │  CORE · SKILLS  │  │  SQLite (51+     │  │ LM Studio  │  │
│  │  PROTOCOLS      │  │  modelos)        │  │ Ollama     │  │
│  │  MEMORY         │  │  LanceDB         │  │ Qualquer   │  │
│  └─────────────────┘  └──────────────────┘  │ compatível │  │
│                                              │ OpenAI     │  │
│                                              └────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Stack de Tecnologia

| Camada | Tecnologia |
|---|---|
| Frontend | Next.js 14, React, Tailwind CSS, Zustand |
| Backend | FastAPI, Python 3.11+, SQLAlchemy assíncrono |
| Banco de Dados | SQLite + aiosqlite (zero configuração, ACID) |
| Vector Store | LanceDB (embarcado, sem processo de servidor) |
| App Desktop | Tauri v2 (bandeja do sistema, gerenciamento de processos) |
| Tempo Real | WebSocket — 16 tipos de eventos de broadcast |
| Provedores de LLM | LM Studio · Ollama · APIs compatíveis com OpenAI |
| Instaladores | macOS DMG · Windows NSIS EXE |

---

## Início Rápido

### Pré-requisitos

- Python 3.11+
- Node 18+
- [LM Studio](https://lmstudio.ai) ou [Ollama](https://ollama.ai)

### Opção A: App Desktop (Recomendado)

Baixe o instalador para sua plataforma em [Releases](https://github.com/henrique-simoes/Istara/releases):

- **macOS**: `Istara-2026.03.29.dmg`
- **Windows**: `Istara-Setup-2026.03.29.exe`

O assistente de configuração guia você pela configuração do LLM, cria seu primeiro projeto e inicia o agente na bandeja do sistema.

### Opção B: Executar a Partir do Código-Fonte

```bash
git clone https://github.com/henrique-simoes/Istara.git
cd Istara

# Inicie o LM Studio e carregue um modelo, depois:

# Backend
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (novo terminal)
cd frontend
npm install
npm run dev
```

Abra [http://localhost:3000](http://localhost:3000).

### Opção C: Docker

```bash
docker-compose up
```

---

## Funcionalidades da Plataforma

### Modo Equipe

Compartilhe o Istara com toda sua equipe de pesquisa com uma única string de conexão:

```
istara://team@seuservidor:8000?token=JWT_AQUI
```

Cole a string no assistente de onboarding — ele configura a URL do backend e autentica automaticamente.

### Doação de Computação

Membros da equipe podem doar capacidade de GPU disponível para o pool compartilhado. O **Relay de Computação** (baseado em WebSocket) roteia requisições de inferência para nós disponíveis com detecção automática de capacidade e failover. Sem nuvem — o hardware da sua equipe se torna o cluster.

### Integrações de Pesquisa

| Integração | O que Faz |
|---|---|
| **SurveyMonkey** | Deploy automático de surveys, coleta de respostas |
| **Google Forms** | Cria e distribui formulários |
| **Typeform** | Deploy de surveys conversacionais |
| **Figma** | Extrai tokens de design system e decisões de design |
| **Google Stitch MCP** | Telas geradas por IA |
| **Slack / Telegram / WhatsApp** | Receba achados como mensagens |

### Inteligência Documental

Adicione qualquer arquivo ao Istara — PDF, DOCX, transcrição, especificação:
- Classifica automaticamente o tipo de documento
- Extrai nuggets e cria tarefas
- Vincula achados de volta às passagens de origem
- Suporta observação de pastas para ingestão contínua
- Vincule pastas externas sem copiar arquivos

### Auditoria das 30 Leis de UX

Execute uma verificação de conformidade contra todas as 30 Leis de UX (Lei de Jakob, Lei de Fitts, Lei de Hick, e mais 27) diretamente em qualquer design ou descrição de interface. Obtenha um relatório pontuado com evidências e recomendações.

### Onboarding Contextual

Cada uma das 22 visões do Istara tem seu próprio fluxo de onboarding. Primeira vez na visão de Skills? Um guia contextual explica o que são skills e como executar uma. Ele se adapta ao que você já configurou.

---

## Screenshots

<!-- TODO: Adicionar screenshots após o primeiro deploy público -->
*Screenshots em breve — veja [docs/](docs/) para diagramas de arquitetura.*

---

## Auto-Evolução dos Agentes: Como Funciona

```
Interação do usuário
      ↓
Agente registra padrão de erro ou preferência de fluxo
      ↓
Padrão rastreado: ocorrências · contextos · tempo
      ↓
Limite atingido: 3+ ocorrências, 2+ contextos, 30 dias
      ↓
Aprendizado promovido → escrito no MEMORY.md do agente
      ↓
Persona do agente atualizada permanentemente
      ↓
Próxima conversa começa com agente melhorado
```

Isso não é fine-tuning. É evolução estruturada de prompts — funciona com qualquer modelo local, incluindo modelos de 3B parâmetros em hardware modesto.

---

## Rastreamento de Desempenho de Skills

Cada invocação de skill é registrada por combinação modelo × skill:

```python
ModelSkillStats(
    model_name="llama-3.2-3b",
    skill_name="thematic_analysis",
    success_rate=0.94,
    avg_quality_score=4.2,
    execution_count=47,
    last_improvement_proposed="2026-03-15"
)
```

Quando a qualidade cai abaixo do limite, o Istara exibe uma proposta de melhoria na interface — um diff entre o prompt atual da skill e a revisão proposta. Você aprova ou rejeita. Skills que consistentemente performam bem no seu hardware ganham uma pontuação de saúde maior e prioridade no roteamento.

---

## Servidor MCP e Protocolo Agente-a-Agente

O Istara expõe duas interfaces de interoperabilidade:

**Servidor MCP** (desativado por padrão, `http://localhost:8001/mcp` quando habilitado):
```
list_skills()       list_projects()     get_findings()
search_memory()     execute_skill()     deploy_research()
create_project()    get_deployment_status()
```

**Protocolo A2A** endpoint de descoberta em `/.well-known/agent.json` — interoperabilidade padrão de agentes para ferramentas externas e frameworks de agentes.

Ambos são controlados por `MCPAccessPolicy` granular com permissões por ferramenta e log completo de auditoria.

---

## Contribuindo

O Istara tem licença MIT e aceita contribuições. As áreas de maior impacto:

- **Novas skills** — Adicione um `SKILL.md` + definição JSON, sem Python necessário para a maioria das skills
- **Adaptadores de LLM** — Novos backends de inferência local
- **Integrações de canais** — Plataformas de mensagens (Discord, Teams, etc.)
- **Componentes de UI** — Melhorias de acessibilidade, novas visões
- **Metodologia de pesquisa** — Melhore prompts, adicione lógica de validação às skills existentes

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para instruções de configuração e guia de estilo de código.

```bash
# Execute o conjunto de testes
pytest tests/

# Execute o agente de simulação com 66 cenários
node tests/simulation/run.mjs

# Verifique a integridade do sistema antes de commitar
python scripts/check_integrity.py
```

---

## Estrutura do Repositório

```
istara/
├── backend/          # Backend FastAPI (Python 3.11+)
│   └── app/
│       ├── api/      # 337 endpoints REST + WebSocket
│       ├── agents/   # Personas dos agentes (CORE, SKILLS, PROTOCOLS, MEMORY)
│       ├── core/     # Orquestrador, RAG, motor de evolução
│       ├── models/   # 51+ modelos SQLAlchemy
│       ├── services/ # Integrações de survey, MCP, canais
│       └── skills/   # Classe base de skill, fábrica, implementações
├── frontend/         # Next.js 14 (React, Tailwind, Zustand)
├── desktop/          # App Tauri v2 para bandeja do sistema
├── installer/        # Configs de build macOS DMG + Windows NSIS
├── relay/            # Relay WebSocket para doação de computação
├── skills/           # Arquivos de definição de skill (SKILL.md por skill)
├── tests/
│   └── simulation/   # Suite de testes E2E com 66 cenários
└── scripts/          # Verificações de integridade, atualizações de agent md
```

---

## Licença

MIT © 2026 Istara Contributors — veja [LICENSE](LICENSE).

---

<div align="center">

Construído para pesquisadores que acreditam que seus dados devem pertencer a eles.

[GitHub](https://github.com/henrique-simoes/Istara) · [Issues](https://github.com/henrique-simoes/Istara/issues) · [Discussões](https://github.com/henrique-simoes/Istara/discussions)

</div>
