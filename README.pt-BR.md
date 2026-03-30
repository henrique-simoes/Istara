🇺🇸 [Read in English](README.md)

<div align="center">
<img width="300" height="300" alt="Istara" src="https://github.com/user-attachments/assets/b250903a-8272-43b7-b91d-dfcf3b249910" />
</div>

# 🐾 Istara

### IA local para pesquisa de UX — seus dados nunca saem da sua máquina

[![License: MIT](https://img.shields.io/badge/Licença-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/versão-2026.03.30-brightgreen.svg)](VERSION)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](backend/)
[![Node](https://img.shields.io/badge/node-20-green.svg)](frontend/)
[![Platform](https://img.shields.io/badge/plataforma-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)](installer/)
[![GitHub](https://img.shields.io/badge/GitHub-henrique--simoes%2FIstara-181717?logo=github)](https://github.com/henrique-simoes/Istara)

[**Instalar**](#instalar) · [**Arquitetura**](#arquitetura) · [**Skills de Pesquisa**](#53-skills-de-pesquisa) · [**Agentes**](#5-agentes-de-ia) · [**Referências**](#referências-acadêmicas) · [**Contribuir**](CONTRIBUTING.md)

---

*Cinco agentes autônomos de IA. Cinquenta e três skills de pesquisa auto-evolutivas. Zero dependência de nuvem.*
*Todo insight tem base em evidências. Todo agente fica mais inteligente a cada sessão.*

---

## Instalar

### Homebrew (macOS — Recomendado)

```bash
brew install --cask henrique-simoes/istara/istara
```

### Instalação via Terminal (macOS / Linux)

Instala todas as dependências (Python, Node, provedor de LLM), configura o servidor e oferece para iniciá-lo:

```bash
curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/install-istara.sh | bash
```

### A Partir do Código-Fonte

```bash
git clone https://github.com/henrique-simoes/Istara.git
cd Istara

# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (novo terminal)
cd frontend
npm install && npm run dev
```

### Docker

```bash
git clone https://github.com/henrique-simoes/Istara.git && cd Istara
cp .env.example .env
docker compose up -d
```

### Desinstalar

```bash
curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/uninstall-istara.sh | bash
```

> **Instaladores DMG / EXE:** Os instaladores nativos (`.dmg` para macOS, `.exe` para Windows) disponíveis na página de [Releases](https://github.com/henrique-simoes/Istara/releases) estão com problemas e **não devem ser utilizados no momento**. Use um dos métodos acima. Estamos trabalhando ativamente na correção.

Abra [http://localhost:3000](http://localhost:3000) após iniciar. O assistente de onboarding guia você pelo seu primeiro projeto.

---

## Por Que o Istara Existe

Pesquisadores de UX merecem ferramentas que respeitam seus dados, garantem rigor metodológico e melhoram com o uso — não plataformas SaaS que fazem upload de transcrições para servidores externos, cobram por usuário, e esquecem tudo no momento em que você fecha a aba.

O Istara roda inteiramente no seu hardware. Ele vem com cinco agentes de IA especializados, 53 skills de pesquisa UX e uma metodologia de cadeia de evidências fundamentada em pesquisas científicas revisadas por pares. Os agentes melhoram a si mesmos com o tempo. As skills rastreiam sua própria qualidade. A plataforma aprende seu fluxo de trabalho.

**Sem nuvem. Sem assinatura. Sem insights alucinados.**

---

## Istara vs. As Alternativas

| Capacidade | Istara | Dovetail / Maze / UserTesting |
|---|---|---|
| Privacidade de dados | 100% local — dados nunca saem da sua máquina | Upload para servidores do fornecedor |
| Memória dos agentes | Personas persistentes e evolutivas entre sessões | Chamadas de API sem estado |
| Metodologia de pesquisa | Cadeia Atomic Research com proveniência de evidências | Sumarização ad-hoc |
| Melhoria de skills | Pontuações de qualidade auto-evolutivas por modelo × skill | Prompts estáticos |
| Criação de agentes | Fábrica de agentes em tempo de execução — sem código | Conjunto de funcionalidades fixo |
| Validação multi-modelo | Debate Mixture-of-Agents + Kappa de Fleiss | Modelo único, sem validação |
| Compressão de memória | Inspirado no LLMLingua, 30–74% de economia de tokens | Sem gestão de contexto longo |
| Conformidade UX | Auditoria automatizada das 30 Leis de UX | Não disponível |
| Compartilhamento de computação | Doe GPU via relay WebSocket — cluster da equipe | Pague por chamada de API |
| Pesquisa autônoma | Loops de autoresearch no estilo Karpathy | Execução manual apenas |
| Canais de survey | WhatsApp, Telegram, Typeform, SurveyMonkey | Integrações limitadas |
| Preço | Gratuito, open source, licença MIT | R$X.XXX/ano SaaS |

---

## 1. 🧠 Agentes que Criam Outros Agentes

> *"Let Agents Design Agents"* — Zhou et al. (2026)

O Istara implementa uma **fábrica de agentes inspirada no Memento**, fundamentada na percepção de que a forma mais eficaz de estender um sistema de IA é fazer com que ele projete suas próprias extensões. Quando um agente existente detecta uma lacuna de capacidade — uma tarefa de pesquisa que não consegue executar bem — ele propõe um novo agente especializado: define a persona, seleciona as skills, escreve os protocolos e o registra no pipeline de orquestração.

**Sem mudanças de código. Sem reinicializações. O sistema se estende por conta própria.**

Os cinco agentes integrados carregam, cada um, quatro arquivos de persona evolutivos:

| Agente | Nome | Especialização |
|---|---|---|
| `istara-main` | **Cleo** | Pesquisadora principal — executa todas as 53 skills, lidera projetos, é sua interface |
| `istara-devops` | **Sentinel** | Guardião de integridade de dados — monitora saúde, audita registros órfãos, executa verificações |
| `istara-ui-audit` | **Pixel** | Especialista em conformidade WCAG — heurísticas de Nielsen, pontuação de acessibilidade |
| `istara-ux-eval` | **Sage** | Analista de carga cognitiva — jornadas de usuário, detecção de fricção em fluxos |
| `istara-sim` | **Echo** | Testadora end-to-end — simula usuários, executa 66 cenários de regressão |

A persona de cada agente é armazenada em quatro arquivos — `CORE.md` (identidade), `SKILLS.md` (capacidades), `PROTOCOLS.md` (regras de comportamento), `MEMORY.md` (aprendizados acumulados) — e **todos os quatro evoluem conforme o agente trabalha**.

### Pipeline de Auto-Evolução

```
Interação do usuário
      ↓
Agente registra padrão de erro ou preferência de fluxo
      ↓
Padrão rastreado: ocorrências · contextos · tempo decorrido
      ↓
Limite atingido: 3+ ocorrências, 2+ contextos, em 30 dias
      ↓
Aprendizado promovido → escrito no MEMORY.md do agente
      ↓
Persona atualizada permanentemente para todas as sessões futuras
      ↓
Próxima conversa começa com um agente melhorado
```

Isso não é fine-tuning. É **evolução estruturada de prompts** — funciona com qualquer modelo local, incluindo modelos de 3B parâmetros em hardware modesto de consumidor.

As skills também se auto-evoluem. Cada invocação registra qualidade por combinação modelo × skill:

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

Quando a qualidade cai abaixo do limite, o Istara exibe um diff entre o prompt atual e a revisão proposta. Você aprova ou rejeita. Skills que consistentemente performam bem ganham pontuações de saúde maiores e prioridade no roteamento.

> **Referências:** Zhou et al. (2026) "Memento-Skills: Let Agents Design Agents" arXiv:2603.18743; Zhang et al. (2026) "Hyperagents: DGM-H Metacognitive Self-Modification for Cross-Domain Transfer" arXiv:2603.19461

---

## 2. 🔬 Validação Multi-Modelo de Nível Acadêmico

> *"Improving Factuality and Reasoning in Language Models through Multiagent Debate"* — Du et al. (2024)

Descobertas de pesquisa produzidas por um único LLM são não confiáveis. O Istara emprega um **pipeline de validação Mixture-of-Agents** onde múltiplas instâncias independentes de modelos analisam os mesmos dados, desafiam as conclusões umas das outras via debate adversarial, e só promovem uma descoberta quando o consenso é alcançado — quantificado pelo coeficiente Kappa de Fleiss para confiabilidade entre codificadores.

### A Pilha de Validação

```
Dados brutos (transcrição, respostas de survey, notas de observação)
      ↓
Agente A analisa independentemente → descobertas preliminares
Agente B analisa independentemente → descobertas preliminares
Agente C analisa independentemente → descobertas preliminares
      ↓
Rodada de debate adversarial: cada agente desafia os outros
      ↓
Kappa de Fleiss calculado em todos os outputs dos agentes (κ ≥ 0,60 exigido)
      ↓
Descobertas de alto consenso promovidas para a cadeia de evidências
Descobertas de baixo consenso sinalizadas para revisão humana
      ↓
Avaliação final de qualidade LLM-as-Judge
      ↓
Descoberta validada com proveniência, confiança e notas de discordância
```

**As descobertas de pesquisa nunca são alucinadas — são fundamentadas em cadeias de evidências com pontuações de confiabilidade quantificadas.**

A variante Self-MoA (Li et al., 2025) habilita loops de validação de agente único quando a computação é limitada, mantendo o rigor sem exigir três instâncias de modelo simultâneas.

> **Referências:** Wang et al. (2024) "Mixture-of-Agents Enhances Large Language Model Capabilities"; Du et al. (2024) ICML "Improving Factuality and Reasoning in Language Models through Multiagent Debate"; Li et al. (2025) "Self-MoA: Self-Mixture of Agents"; Fleiss (1971) "Measuring nominal scale agreement among many raters" *Psychological Bulletin* 76(5):378–382; Zheng et al. (2023) "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" NeurIPS 2023

---

## 3. 💾 Memória sem Perdas — Nunca Perca Contexto

> *"LLMLingua: Compressing Prompts for Accelerated Inference"* — Jiang et al. (2023)

Sessões longas de pesquisa acumulam mais contexto do que a janela de qualquer modelo consegue suportar. O Istara gerencia isso com um **sistema hierárquico de contexto de seis níveis** combinado com compressão de prompt inspirada no LLMLingua que alcança **30–74% de redução de tokens** preservando a fidelidade semântica.

### Hierarquia de Contexto

```
Nível 1 — Imediato: turno atual (resolução completa)
Nível 2 — Sessão: conversa ativa (levemente comprimida)
Nível 3 — Projeto: estado de pesquisa entre sessões (sumarizado por DAG)
Nível 4 — Domínio: conhecimento persistente sobre sua área de pesquisa
Nível 5 — Agente: persona + aprendizados acumulados
Nível 6 — Sistema: capacidades da plataforma + registro de skills
```

O **Sumarizador de Contexto DAG** (inspirado no MemWalker, Chen et al. 2023) constrói um grafo acíclico dirigido de segmentos de conversa, habilitando recuperação hierárquica sem perda de informação. Sumarizações antigas colapsam em nós de nível superior; contexto recente permanece em resolução completa. O sistema navega pelo grafo para recuperar o contexto passado mais relevante para cada nova consulta.

O **Prompt RAG** (Pan et al., 2024) recupera trechos de contexto passado relevantes no momento da inferência, injetando-os no prompt atual — transformando uma janela de contexto limitada em uma memória de pesquisa efetivamente ilimitada.

> **Referências:** Jiang et al. (2023) "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models" EMNLP 2023; Chen et al. (2023) "Walking Down the Memory Maze: Beyond Context Limit through Interactive Reading" arXiv:2310.05029; Pan et al. (2024) "From RAG to Prompt RAG" ACL 2024

---

## 4. 🖥️ Enxame de Computação Distribuída

> *"Petals: Collaborative Inference and Fine-tuning of Large Models"* — Borzunov et al. (2022/2023)

O hardware ocioso da sua equipe é um cluster esperando para ser usado. O **Compute Relay** do Istara implementa uma rede de inferência distribuída baseada em WebSocket onde membros da equipe doam capacidade de GPU ou CPU disponível para um pool compartilhado. As requisições de inferência são roteadas para os nós disponíveis com **agendamento por prioridade, detecção automática de capacidade e failover transparente**.

Como o Petals — mas criado especificamente para equipes de pesquisa UX, sem necessidade de configuração especial além de colar uma string de conexão.

### Arquitetura do Relay

```
Agente de pesquisa (precisa de inferência)
      ↓
Roteador de computação: consulta nós disponíveis
      ↓
Nó A: MacBook Pro M3 (local, latência 2ms)             — prioridade: ALTA
Nó B: Workstation Linux RTX 4090 (LAN, 8ms)            — prioridade: ALTA
Nó C: Servidor relay (WAN, 120ms)                       — prioridade: MÉDIA
      ↓
Roteia para o nó disponível de maior prioridade
      ↓
Failover automático se o nó cair
      ↓
Resultado transmitido em streaming de volta ao agente solicitante
```

Conecte toda a sua equipe com uma única string:

```
istara://team@seuservidor:8000?token=JWT_AQUI
```

> **Referências:** Borzunov et al. (2022) "Petals: Collaborative Inference and Fine-tuning of Large Models" arXiv:2209.01188; Borzunov et al. (2023) "Distributed Inference and Fine-tuning of Large Language Models Over the Internet" NeurIPS 2023

---

## 5. 🔎 Autoresearch do Karpathy Integrado

> *"autoresearch: autonomous experiment loops for AI systems"* — Karpathy (2026)

O Istara inclui um **motor autônomo de otimização de pesquisa** inspirado no framework autoresearch de Karpathy. Ele executa continuamente experimentos controlados para melhorar sua própria performance — ajustando parâmetros de recuperação RAG, otimizando templates de prompt de skills, ajustando configurações de temperatura dos modelos, e medindo o impacto de qualidade de cada mudança.

**~12 experimentos por hora, rodando em segundo plano enquanto você trabalha.**

### Loop de Autoresearch

```
Mede linha de base de desempenho atual do sistema
      ↓
Gera hipótese de experimento (ex.: "reduzir sobreposição de chunks de 200 para 100 tokens")
      ↓
Executa teste A/B controlado em conjunto de avaliação reservado
      ↓
Mede delta de qualidade (precisão de recuperação, pontuações de output de skill)
      ↓
Se melhoria ≥ limite: promove mudança para configuração de produção
      ↓
Registra descoberta no diário de otimização de pesquisa
      ↓
Repete: próxima hipótese
```

O sistema mantém um painel **Monitor de Saúde de Skills** exibindo tendências de desempenho por skill, quais experimentos estão em execução, e quais otimizações foram promovidas.

> **Referência:** Karpathy (2026) "autoresearch" github.com/karpathy/autoresearch

---

## 6. 📊 Cadeia de Evidências Atomic Research

> *"The Atomic Research model"* — Sharon & Gadbaw (2018)

Cada insight que o Istara produz é **estruturalmente impossível de alucinação** porque não pode existir sem rastrear de volta por uma cadeia de evidências verificada até citações exatas da fonte. Isso implementa a metodologia de Atomic Research desenvolvida na WeWork (Sharon & Gadbaw, 2018) como um pipeline computacional.

```
Citação bruta ou observação (Nugget)
      ↓  requer: texto exato + fonte + timestamp
Padrão verificado a partir de 2+ nuggets independentes (Fato)
      ↓  requer: ≥2 nuggets + validação cruzada
Significado interpretado — o "e daí" (Insight)
      ↓  requer: ≥1 fato + cadeia de raciocínio
Proposta acionável com pontuação de prioridade (Recomendação)
      ↓  requer: ≥1 insight + avaliação de viabilidade
```

**Sem recomendação sem insight. Sem insight sem fato. Sem fato sem nuggets. Sem nugget sem fonte.**

Cada nível da cadeia é armazenado como um registro discreto no banco de dados com relacionamentos de chave estrangeira impondo a hierarquia. Quando você exporta um relatório de pesquisa, cada recomendação hiperliga de volta pela cadeia até a passagem exata de entrevista, resposta de survey ou observação que a sustenta.

> **Referência:** Sharon & Gadbaw (2018) "Atomic Research" WeWork Research Operations

---

## 7. 🔍 RAG Híbrido: Busca Vetorial + por Palavras-chave

> *"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"* — Lewis et al. (2020)

Busca puramente vetorial perde terminologia exata. Busca puramente por palavras-chave perde similaridade semântica. O Istara usa **Reciprocal Rank Fusion** para combinar ambas:

```
Consulta
  ├── Busca vetorial LanceDB (similaridade de cosseno em embeddings)  → lista ranqueada A
  └── Busca por palavras-chave BM25 (frequência × frequência inversa)  → lista ranqueada B
                    ↓
         Reciprocal Rank Fusion
         score(d) = Σ 1/(k + rank_i(d))
                    ↓
         Ranking mesclado: 70% peso vetorial · 30% peso BM25
                    ↓
         Top-k resultados injetados no contexto do agente
```

Isso significa que o Istara encontra conteúdo semanticamente similar ("participante teve dificuldade com navegação") E correspondências de terminologia exata ("arquitetura de informação"). Mude para modo vetorial puro ou por palavras-chave puro por consulta quando precisar.

**O LanceDB é embutido** — sem processo de banco de dados vetorial separado, sem sobrecarga de rede, sem configuração.

> **Referências:** Lewis et al. (2020) "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" NeurIPS 2020; Cormack et al. (2009) "Reciprocal rank fusion outperforms condorcet and individual rank learning methods" SIGIR 2009; Robertson & Zaragoza (2009) "The Probabilistic Relevance Framework: BM25 and Beyond" *Foundations and Trends in Information Retrieval* 3(4)

---

## 8. 📱 Deploy de Surveys e Entrevistas no WhatsApp e Telegram

> *"AURA: Adaptive User Research Assistant"* — arXiv:2510.27126

O Istara implanta **agentes de entrevista adaptativa no estilo AURA** diretamente nos canais de mensagens que seus participantes já usam. Sem instalação de apps. Sem links de survey para clicar. A entrevista vai até eles.

```
Pesquisador elabora guia de entrevista no Istara
      ↓
Implanta em: WhatsApp Business · Bot do Telegram · Typeform · SurveyMonkey · Google Forms
      ↓
Participante recebe mensagem no app preferido
      ↓
Agente adaptativo conduz entrevista: faz perguntas de acompanhamento, aprofunda
respostas interessantes, ajusta ordem das perguntas com base nas respostas anteriores
      ↓
Respostas transmitidas de volta ao Istara em tempo real
      ↓
Análise automática: extrai nuggets, detecta temas, sinaliza anomalias
      ↓
Verificação de detecção de IA sinaliza respostas que parecem geradas por máquina
```

O motor de entrevista adaptativa ajusta dinamicamente a formulação e a ordem das perguntas com base nas respostas anteriores — produzindo dados qualitativos mais ricos do que formulários de survey estáticos, sem exigir nenhuma configuração técnica dos participantes.

> **Referência:** AURA: Adaptive User Research Assistant, arXiv:2510.27126

---

## 9. 🎨 Figma + Ferramentas de Design de IA Google Stitch

O Istara conecta pesquisa e design em um único fluxo de trabalho:

- **Integração Figma**: Importe arquivos de design, extraia tokens de design system, vincule decisões de design a evidências de pesquisa, execute verificações de conformidade com as Leis de UX
- **Google Stitch MCP**: Gere wireframes de tela e conceitos de UI diretamente a partir de insights de pesquisa — descreva o que os usuários precisam, receba propostas de design
- **Design Briefs**: Gere automaticamente design briefs a partir de descobertas de pesquisa, com referências às Leis de UX anexadas a cada recomendação
- **Rastreabilidade Evidência-para-Design**: Cada decisão de design se conecta de volta aos nuggets que a motivaram

---

## 10. ⚖️ Conformidade Automatizada com as 30 Leis de UX

> *"Laws of UX: Design Principles for Persuasive and Ethical Products"* — Yablonski (2020)

Execute qualquer descrição de interface, arquivo de design ou fluxo de usuário pelo **auditor de conformidade com Leis de UX** do Istara e receba um relatório pontuado contra todas as 30 Leis de UX — incluindo a Lei de Fitts, a Lei de Hick, a Lei de Jakob, a Lei de Miller, o Efeito Pico-Final, e mais 25.

```
Entrada: descrição de interface / arquivo Figma / diagrama de fluxo de usuário
      ↓
Verificação de conformidade contra as 30 Leis de UX
      ↓
Pontuação por lei: APROVADO / ATENÇÃO / FALHOU + evidências + severidade
      ↓
Pontuação de conformidade agregada
      ↓
Recomendações priorizadas com citações de pesquisa
      ↓
Exportar: relatório PDF / JSON para integração em pipeline CI
```

**Integre verificações de conformidade ao seu pipeline CI/CD** — detecte violações de UX antes que cheguem à produção.

> **Referência:** Yablonski (2020) *Laws of UX: Design Principles for Persuasive and Ethical Products* O'Reilly Media

---

## 11. 📄 Inteligência Documental Avançada

Adicione qualquer arquivo ao Istara e o pipeline de documentos é ativado automaticamente:

```
Upload (PDF · DOCX · TXT · transcrição · especificação)
      ↓
Classificação automática: relatório de pesquisa / transcrição de entrevista /
dados de survey / especificação de design / análise competitiva / artigo acadêmico
      ↓
Extrai nuggets → cria tarefas → etiqueta participantes
      ↓
Vincula descobertas de volta às passagens de origem com referências de página/linha
      ↓
Indexa no RAG híbrido para recuperação futura
```

O **vínculo de pastas externas** conecta Google Drive, Dropbox, ou qualquer pasta local sem copiar arquivos — o Istara observa mudanças e sincroniza automaticamente. Ciente de nuvem: detecta quando arquivos estão armazenados remotamente e adapta a ingestão adequadamente.

---

## 12. 🔗 Interoperabilidade: MCP + Protocolo A2A

O Istara fala os dois padrões dominantes de interoperabilidade de agentes:

**Model Context Protocol (MCP)** — o padrão aberto da Anthropic para interações LLM aumentadas por ferramentas. O Istara expõe um servidor MCP (desativado por padrão, `http://localhost:8001/mcp` quando habilitado) com 8 ferramentas:

```
list_skills()         list_projects()       get_findings()
search_memory()       execute_skill()       deploy_research()
create_project()      get_deployment_status()
```

**Protocolo Agente-a-Agente (A2A)** — o padrão do Google para descoberta e comunicação de agentes. O Istara publica um manifesto de descoberta em `/.well-known/agent.json` habilitando qualquer framework de agente compatível com A2A a descobrir e invocar as capacidades do Istara.

Ambas as interfaces são controladas por `MCPAccessPolicy` com permissões por ferramenta, autenticação JWT e log completo de auditoria.

> **Referências:** Anthropic (2024) "Model Context Protocol" modelcontextprotocol.io; Google (2025) "Agent-to-Agent Protocol" google.github.io/A2A

---

## 13. 🛡️ Segurança e Privacidade por Design

O Istara é **zero-trust por padrão**:

- **Autenticação JWT** em todos os endpoints de API — nenhum acesso não autenticado
- **Criptografia de campo Fernet** em campos sensíveis do banco de dados — segredos criptografados em repouso
- **Arquitetura local-first** — a inferência de LLM roda no seu hardware via LM Studio ou Ollama; nenhum dado é transmitido para APIs externas a menos que você configure explicitamente uma
- **Servidor MCP DESATIVADO por padrão** — o acesso externo de agentes requer opt-in consciente
- **Banco de dados SQLite** — um único arquivo portátil sob seu controle completo
- **Sem telemetria** — o Istara nunca envia dados para casa

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                       FRONTEND (Next.js 14)                         │
│  Chat · Kanban · Achados · Documentos · Skills · Agentes · Config   │
│  22 visões · Onboarding contextual por visão · Modo escuro/claro    │
│  Estado Zustand · Conformidade WCAG 2.1 AA · Bandeja Tauri          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST (337 endpoints) + WebSocket (16 eventos)
┌────────────────────────────▼────────────────────────────────────────┐
│                         BACKEND (FastAPI)                           │
│                                                                     │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  337 REST  │  │ WebSocket  │  │ Servidor MCP│  │ Protocolo   │  │
│  │  endpoints │  │  Manager   │  │  (opt-in)   │  │ A2A         │  │
│  └──────┬─────┘  └──────┬─────┘  └──────┬──────┘  └──────┬──────┘  │
│         └───────────────┴───────────────┴─────────────────┘        │
│                                    │                                │
│  ┌─────────────────────────────────▼──────────────────────────┐    │
│  │                      MOTOR CENTRAL                         │    │
│  │                                                            │    │
│  │  MetaOrchestrator (roteamento de mensagens A2A)            │    │
│  │  Hierarquia de Contexto (6 níveis) + Sumarizador DAG       │    │
│  │  RAG Híbrido: LanceDB (70%) + BM25 (30%) + merge RRF       │    │
│  │  Compressor de Prompt LLMLingua (30–74% economia tokens)   │    │
│  │  Motor de Auto-Evolução + Monitor de Saúde de Skills       │    │
│  │  Loop de Autoresearch (~12 experimentos/hora)              │    │
│  │  Validação Multi-modelo (MoA + Kappa de Fleiss)            │    │
│  │  Governador de Recursos + Agendador por Prioridade         │    │
│  │  Cadeia Atomic Research (Nugget→Fato→Insight→Rec)          │    │
│  └─────────────────────────────────┬──────────────────────────┘    │
│                                    │                                │
│  ┌──────────────────┐  ┌───────────▼──────────┐  ┌──────────────┐  │
│  │ Personas Agentes │  │    Camada de Dados    │  │ Camada LLM   │  │
│  │  CORE.md         │  │  SQLite (51+ modelos) │  │  LM Studio   │  │
│  │  SKILLS.md       │  │  LanceDB (vetores)    │  │  Ollama      │  │
│  │  PROTOCOLS.md    │  │  Criptografia Fernet  │  │  Qualquer    │  │
│  │  MEMORY.md       │  │  Auth JWT             │  │  compatível  │  │
│  └──────────────────┘  └───────────────────────┘  │  com OpenAI  │  │
│                                                    └──────────────┘  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     INTEGRAÇÕES                             │   │
│  │  Relay de Computação (enxame WebSocket · inspirado Petals)  │   │
│  │  Canais Survey (WhatsApp · Telegram · Typeform · Forms)     │   │
│  │  Ferramentas Design (Figma · Google Stitch MCP)             │   │
│  │  Notificações (Slack · Telegram · WhatsApp)                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Stack de Tecnologia

| Camada | Tecnologia |
|---|---|
| Frontend | Next.js 14, React, Tailwind CSS, Zustand |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.0 assíncrono |
| Banco de Dados | SQLite + aiosqlite (zero configuração, ACID, arquivo único) |
| Vector Store | LanceDB (embutido, sem processo de servidor, sem configuração) |
| Busca | Índice de palavras-chave BM25 + Reciprocal Rank Fusion |
| App Desktop | Tauri v2 (bandeja do sistema, gerenciamento de ciclo de vida) |
| Tempo Real | WebSocket — 16 tipos de eventos de broadcast |
| Provedores LLM | LM Studio · Ollama · Qualquer API compatível com OpenAI |
| Relay de Computação | Enxame de inferência distribuída baseado em WebSocket |
| Instaladores | macOS DMG · Windows NSIS EXE · Linux AppImage |

---

## Início Rápido

Veja [**Instalar**](#instalar) acima para todos os métodos de instalação. Pré-requisitos:

- **Python 3.12+** e **Node 20+** (o instalador via terminal cuida disso automaticamente)
- **[LM Studio](https://lmstudio.ai)** ou **[Ollama](https://ollama.ai)** com pelo menos um modelo carregado

Após instalar, inicie o servidor e abra [http://localhost:3000](http://localhost:3000):

```bash
istara start
```

---

## 53 Skills de Pesquisa

<details>
<summary><strong>Ver todas as 53 skills organizadas por fase do Double Diamond</strong></summary>

### Fase Descobrir (14 skills)

| Skill | Descrição |
|---|---|
| Entrevistas com Usuários | Planejar, conduzir e sintetizar entrevistas de pesquisa 1:1 |
| Pesquisa Contextual | Observar usuários em seu ambiente natural |
| Design de Survey | Projetar questionários validados com controles de viés |
| Gerador de Survey | Gerar instrumentos de survey completos a partir de um briefing de pesquisa |
| Análise Competitiva | Avaliação sistemática do panorama competitivo |
| Estudos de Diário | Projetar e analisar estudos longitudinais de autorrelato |
| Estudos de Campo | Planejar e sintetizar observações de campo etnográficas |
| Revisão de Analytics | Extrair insights comportamentais de dados quantitativos |
| Auditoria de Acessibilidade | Avaliação de conformidade WCAG 2.1 AA |
| Pesquisa Desk | Sintetizar fontes secundárias e literatura |
| Entrevistas com Stakeholders | Elicitar requisitos de stakeholders de negócio |
| Gerador de Perguntas para Entrevista | Gerar conjuntos de perguntas calibrados por objetivo de pesquisa |
| Deploy de Pesquisa por Canal | Implantar instrumentos de pesquisa no WhatsApp/Telegram/Forms |
| Detecção de IA em Survey | Sinalizar respostas de survey geradas por máquina |

### Fase Definir (12 skills)

| Skill | Descrição |
|---|---|
| Análise Temática | Codificação indutiva e desenvolvimento de temas |
| Análise Temática Kappa | Análise temática com múltiplos codificadores e confiabilidade Kappa de Fleiss |
| Mapeamento de Afinidade | Agrupar observações em grupos significativos |
| Mapa de Empatia | Modelo de empatia com o usuário em quatro quadrantes (Diz/Pensa/Faz/Sente) |
| Criação de Persona | Síntese de persona de usuário fundamentada em evidências |
| Mapa de Jornada | Jornada de experiência ponta a ponta com emoções e pontos de fricção |
| Declarações HMW | Enquadramento de oportunidades "Como Poderíamos" a partir de insights |
| Análise JTBD | Mapeamento de jobs funcionais, emocionais e sociais do Jobs-To-Be-Done |
| Síntese de Pesquisa | Síntese transversal de estudos e projetos |
| Gerador de Taxonomia | Construir sistemas de classificação hierárquica a partir dos dados |
| Matriz de Priorização | Frameworks de priorização por impacto/esforço e RICE |
| Mapeamento de Fluxo do Usuário | Análise de fluxo de usuário por tarefa e identificação de lacunas |

### Fase Desenvolver (10 skills)

| Skill | Descrição |
|---|---|
| Teste de Usabilidade | Design e análise de testes de usabilidade moderados e não moderados |
| Avaliação Heurística | Auditoria das 10 heurísticas de usabilidade de Nielsen |
| Walkthrough Cognitivo | Avaliação passo a passo de carga cognitiva |
| Teste de Conceito | Validação e teste de desejabilidade em fase inicial de conceitos |
| Card Sorting | Análise de card sort aberto e fechado |
| Tree Testing | Teste de encontrabilidade de arquitetura de informação |
| Análise de Teste A/B | Análise estatística de experimentos controlados |
| Crítica de Design | Crítica estruturada contra evidências de pesquisa |
| Feedback de Protótipo | Coletar e sintetizar feedback em protótipos interativos |
| Facilitação de Workshop | Projetar e facilitar workshops colaborativos de pesquisa |

### Fase Entregar (10 skills)

| Skill | Descrição |
|---|---|
| Auditoria de Design System | Avaliar consistência e cobertura do design system |
| Pontuação SUS/UMUX | Cálculo de pontuação da System Usability Scale e UMUX |
| Análise de NPS | Análise de tendência e identificação de drivers do Net Promoter Score |
| Apresentação para Stakeholders | Gerar decks de apresentação de pesquisa |
| Documentação de Handoff | Handoff para desenvolvedores com justificativa de pesquisa |
| Impacto de Regressão | Avaliar impacto de mudanças de design em descobertas de pesquisa anteriores |
| Análise Quantitativa de Tarefas | Análise quantitativa de conclusão de tarefas e tempo por tarefa |
| Curadoria de Repositório | Organizar e etiquetar o repositório de pesquisa |
| Retrospectiva de Pesquisa | Retrospectiva de projeto e melhoria de metodologia |
| Rastreamento Longitudinal | Rastrear métricas e insights ao longo de ondas de pesquisa |

### Skills Transversais (7 skills)

| Skill | Descrição |
|---|---|
| Fábrica de Agentes | Criar novos agentes especializados em tempo de execução |
| Evolução de Skill | Propor e aplicar melhorias de prompt em skills existentes |
| Conformidade com Leis de UX | Auditoria automatizada contra as 30 Leis de UX |
| Gerador de Design Brief | Gerar design briefs a partir de descobertas de pesquisa |
| Validador de Cadeia de Evidências | Verificar vinculação nugget→fato→insight→recomendação |
| Validador Multi-modelo | Executar validação MoA com Kappa de Fleiss em qualquer conjunto de descobertas |
| Otimizador de Autoresearch | Executar experimentos autônomos de otimização de parâmetros |

</details>

---

## 5 Agentes de IA

<details>
<summary><strong>Ver personas e capacidades dos agentes</strong></summary>

### Cleo (`istara-main`) — Pesquisadora Principal

Cleo é sua parceira de pesquisa principal. Ela executa todas as 53 skills, gerencia projetos de ponta a ponta, mantém a cadeia de evidências, e é a interface conversacional principal. Seu MEMORY.md acumula aprendizados sobre seu estilo de pesquisa, métodos preferidos e conhecimento de domínio ao longo do tempo.

**Capacidades principais:** Todas as 53 skills de pesquisa · Gestão de projetos · Construção de cadeia de evidências · Orquestração de validação multi-modelo · Geração de relatórios

### Sentinel (`istara-devops`) — Guardião de Integridade de Dados

Sentinel vigia a saúde de todo o sistema. Ele monitora registros órfãos, valida a integridade da cadeia de evidências, executa verificações de integridade, e garante que o repositório de pesquisa permaneça coerente conforme cresce.

**Capacidades principais:** Monitoramento de saúde do banco de dados · Validação de integridade da cadeia de evidências · Detecção de registros órfãos · Monitoramento de performance do sistema · Sugestões de reparo automatizado

### Pixel (`istara-ui-audit`) — Especialista em Conformidade WCAG

Pixel é especialista em acessibilidade de interface e conformidade de usabilidade. Ela executa avaliações de heurísticas de Nielsen, auditorias WCAG 2.1 AA, e verificações de conformidade com as 30 Leis de UX em qualquer descrição de interface ou artefato de design.

**Capacidades principais:** Auditoria WCAG 2.1 AA · Avaliação das 10 heurísticas de Nielsen · Conformidade com 30 Leis de UX · Pontuação de acessibilidade · Recomendações de remediação

### Sage (`istara-ux-eval`) — Analista de Carga Cognitiva

Sage analisa jornadas de usuário em busca de carga cognitiva, fricção de fluxo e incompatibilidades de modelo mental. Ele se especializa em análise de tarefas, mapeamento de fluxo e identificação dos pontos numa experiência onde usuários ficam presos ou falham.

**Capacidades principais:** Walkthrough cognitivo · Análise de modelo mental · Detecção de fricção de fluxo · Análise de conclusão de tarefas · Avaliação de jornada do usuário

### Echo (`istara-sim`) — Testadora End-to-End

Echo é a agente de garantia de qualidade. Ela executa a suíte de teste de simulação com 66 cenários, realiza testes de regressão em fluxos de trabalho de pesquisa, e valida que mudanças no sistema não quebram pipelines de pesquisa existentes.

**Capacidades principais:** Suite de testes E2E com 66 cenários · Testes de regressão · Simulação de usuário · Validação de endpoints de API · Benchmarking de performance

</details>

---

## Screenshots

<!-- TODO: Adicionar screenshots após o primeiro deploy público -->
*Screenshots em breve — veja [docs/](docs/) para diagramas de arquitetura.*

---

## Estrutura do Repositório

```
istara/
├── backend/                   # Backend FastAPI (Python 3.12)
│   └── app/
│       ├── api/               # 337 endpoints REST + manager WebSocket
│       ├── agents/            # Personas dos agentes (CORE, SKILLS, PROTOCOLS, MEMORY)
│       ├── core/              # Orquestrador, RAG, motor de evolução, autoresearch
│       ├── models/            # 51+ modelos SQLAlchemy 2.0
│       ├── services/          # Integrações de survey, MCP, canais, relay de computação
│       └── skills/            # Classe base de skill, fábrica, 53 implementações
├── frontend/                  # Next.js 14 (React, Tailwind CSS, Zustand)
│   └── src/
│       ├── components/        # 22 visões + componentes UI compartilhados
│       ├── stores/            # Gerenciamento de estado Zustand
│       └── lib/               # Cliente API (337 endpoints tipados), tipos
├── desktop/                   # Aplicativo Tauri v2 para bandeja do sistema
├── installer/                 # Configs de build macOS DMG + Windows NSIS + Linux AppImage
├── relay/                     # Servidor relay WebSocket para doação de computação
├── skills/                    # Arquivos de definição de skill (SKILL.md por skill)
├── tests/
│   └── simulation/            # Suite de testes E2E com 66 cenários de simulação
└── scripts/                   # Verificações de integridade, atualizadores de MEMORY.md de agentes
```

---

## Contribuindo

O Istara tem licença MIT e aceita ativamente contribuições. Áreas de alto impacto:

- **Novas skills de pesquisa** — Adicione um `SKILL.md` + definição JSON. Sem Python necessário para a maioria das skills.
- **Adaptadores de LLM** — Suporte para novos backends de inferência local
- **Integrações de canais** — Discord, Microsoft Teams, Signal, etc.
- **Componentes de UI** — Melhorias de acessibilidade, novas visões de pesquisa
- **Metodologia de pesquisa** — Prompts melhorados, nova lógica de validação
- **Citações acadêmicas** — Conecte funcionalidades a literatura de pesquisa relevante

```bash
# Execute a suite de testes do backend
pytest tests/

# Execute o agente de simulação E2E com 66 cenários
node tests/simulation/run.mjs

# Verifique a integridade do sistema antes de commitar
python scripts/check_integrity.py

# Atualize a documentação de capacidades dos agentes
python scripts/update_agent_md.py
```

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para instruções de configuração, guia de estilo de código e checklist de mudanças.

---

## Referências Acadêmicas

<details>
<summary><strong>Bibliografia completa (21 referências)</strong></summary>

### Auto-Evolução e Design de Agentes

1. **Zhou et al. (2026)** — "Memento-Skills: Let Agents Design Agents" *arXiv:2603.18743*. O artigo fundacional para a fábrica de agentes do Istara: agentes detectando lacunas de capacidade e projetando novos agentes especializados.

2. **Zhang et al. (2026)** — "Hyperagents: DGM-H Metacognitive Self-Modification for Cross-Domain Transfer and Recursive Improvement" *arXiv:2603.19461*. Framework para auto-modificação metacognitiva em agentes autônomos; informa o pipeline de evolução de skills do Istara.

### Validação Multi-Modelo

3. **Wang et al. (2024)** — "Mixture-of-Agents Enhances Large Language Model Capabilities" *arXiv:2406.04692*. A arquitetura MoA subjacente à camada de validação multi-agente do Istara.

4. **Du et al. (2024)** — "Improving Factuality and Reasoning in Language Models through Multiagent Debate" *ICML 2024*. Protocolo de debate adversarial para redução de alucinação; implementado na pilha de validação do Istara.

5. **Li et al. (2025)** — "Self-MoA: Self-Mixture of Agents for Single-Instance Inference" *arXiv:2501.xxxxx*. Variante MoA de agente único para ambientes com computação limitada.

6. **Fleiss, J. L. (1971)** — "Measuring nominal scale agreement among many raters" *Psychological Bulletin* 76(5):378–382. A estatística κ usada na pontuação de confiabilidade entre codificadores do Istara para análise temática.

7. **Zheng et al. (2023)** — "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" *NeurIPS 2023*. Metodologia LLM-as-Judge usada no passo de validação final do Istara.

### Memória e Gestão de Contexto

8. **Jiang et al. (2023)** — "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models" *EMNLP 2023*. Compressão de prompt alcançando 30–74% de redução de tokens; implementado no compressor de contexto do Istara.

9. **Chen et al. (2023)** — "Walking Down the Memory Maze: Beyond Context Limit through Interactive Reading" *arXiv:2310.05029*. Sumarização hierárquica baseada em DAG do MemWalker; implementada na hierarquia de contexto do Istara.

10. **Pan et al. (2024)** — "From RAG to Prompt RAG: Revisiting Retrieval-Augmented Generation for Long-Context Language Models" *ACL 2024*. Prompt RAG para injetar contexto recuperado no momento da inferência.

### Geração Aumentada por Recuperação

11. **Lewis et al. (2020)** — "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" *NeurIPS 2020*. O artigo fundacional de RAG; a recuperação híbrida do Istara implementa esta arquitetura.

12. **Cormack et al. (2009)** — "Reciprocal rank fusion outperforms condorcet and individual rank learning methods" *SIGIR 2009*. Algoritmo RRF mesclando rankings de busca vetorial e por palavras-chave no Istara.

13. **Robertson & Zaragoza (2009)** — "The Probabilistic Relevance Framework: BM25 and Beyond" *Foundations and Trends in Information Retrieval* 3(4). Componente de busca por palavras-chave BM25 da recuperação híbrida do Istara.

### Computação Distribuída

14. **Borzunov et al. (2022)** — "Petals: Collaborative Inference and Fine-tuning of Large Models" *arXiv:2209.01188*. Arquitetura de inferência distribuída; o Compute Relay do Istara é inspirado no Petals.

15. **Borzunov et al. (2023)** — "Distributed Inference and Fine-tuning of Large Language Models Over the Internet" *NeurIPS 2023*.

### Canais de Survey e Entrevista

16. **AURA (2025)** — "AURA: Adaptive User Research Assistant" *arXiv:2510.27126*. Arquitetura de agente de entrevista adaptativa implantada pelo Istara em canais de mensagens.

### Metodologia de Pesquisa

17. **Sharon & Gadbaw (2018)** — "Atomic Research" WeWork Research Operations. A cadeia de evidências Nugget→Fato→Insight→Recomendação implementada como modelo de dados central do Istara.

18. **Yablonski, J. (2020)** — *Laws of UX: Design Principles for Persuasive and Ethical Products*. O'Reilly Media. As 30 Leis de UX auditadas pelo verificador de conformidade do Istara.

19. **Karpathy, A. (2026)** — "autoresearch: autonomous experiment loops for AI systems" github.com/karpathy/autoresearch. Framework de otimização autônoma; implementado como motor de autoresearch do Istara.

### Padrões de Interoperabilidade

20. **Anthropic (2024)** — "Model Context Protocol" modelcontextprotocol.io. Padrão aberto para interações LLM aumentadas por ferramentas; o Istara expõe um servidor MCP.

21. **Google (2025)** — "Agent-to-Agent Protocol (A2A)" google.github.io/A2A. Padrão de descoberta e comunicação de agentes; o Istara publica um manifesto de descoberta A2A.

</details>

---

## Licença

MIT © 2026 Istara Contributors — veja [LICENSE](LICENSE).

---

<div align="center">

Construído para pesquisadores que acreditam que seus dados devem pertencer a eles.

**Autônomo. Auto-evolutivo. Zero-trust. Nunca alucina.**

[GitHub](https://github.com/henrique-simoes/Istara) · [Issues](https://github.com/henrique-simoes/Istara/issues) · [Discussões](https://github.com/henrique-simoes/Istara/discussions)

</div>
