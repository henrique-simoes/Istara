🇺🇸 [Read in English](README.md)

<div align="center">
<img width="300" height="300" alt="Istara" src="https://github.com/user-attachments/assets/b250903a-8272-43b7-b91d-dfcf3b249910" />
</div>

# 🐾 Istara

### IA local para pesquisa de UX — seus dados nunca saem da sua máquina

[![License: MIT](https://img.shields.io/badge/Licença-MIT-blue.svg)](LICENSE)
[![Versão](https://img.shields.io/github/v/release/henrique-simoes/Istara?label=vers%C3%A3o&sort=semver)](https://github.com/henrique-simoes/Istara/releases/latest)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](backend/)
[![Node](https://img.shields.io/badge/node-20-green.svg)](frontend/)
[![Platform](https://img.shields.io/badge/plataforma-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)](installer/)
[![GitHub](https://img.shields.io/badge/GitHub-henrique--simoes%2FIstara-181717?logo=github)](https://github.com/henrique-simoes/Istara)

[**Instalar em 1 Minuto**](#instalar) · [**Arquitetura**](#arquitetura) · [**Testes**](TESTING.md) · [**Segurança**](SECURITY.md) · [**Mapa de Docs**](DOCUMENTATION.md) · [**Referências**](#referências-acadêmicas-e-padrões) · [**Contribuir**](CONTRIBUTING.md)

---

*Cinco agentes autônomos de IA. Cinquenta e três skills de pesquisa com melhoria governada. Zero dependência de nuvem.*
*Todo insight confiável é validado na fonte. O aprendizado dos agentes é governado, por projeto e auditável.*
*Inteligência em escala: compartilhe poder computacional entre membros da equipe para rodar mais agentes simultaneamente—um time mais inteligente e rápido trabalhando como um enxame agentic.*

<div align="center">
<img src="Screenshots/istara_presentation.gif" width="900" alt="Demo do Istara — agentes de IA conduzindo pesquisa de UX de forma autônoma" />
<img src="Screenshots/istara_chat.gif" width="900" alt="Chat inteligente do Istara — conversas fundamentadas com seus dados de pesquisa" />
</div>

### Resumo Rápido

| Recurso | O Que Faz |
|---|---|
| 🧠 Chat Inteligente | Conversas fundamentadas nos seus dados de pesquisa, respostas conscientes de fonte e evidências revisáveis |
| ⚛️ Achados Atômicos | Átomos/nuggets aceitos → fatos → insights → recomendações, cada afirmação confiável vinculada à evidência validada |
| 📐 Leis de UX | 30+ princípios psicológicos auditados automaticamente nos seus designs com pontuação |
| 📋 Quadro Kanban | Agentes assumem tarefas e executam skills, enquanto revisão, Done e portões de relatório continuam explícitos |
| 🎯 Roteamento Inteligente | Direcione tarefas para especialistas — Pixel para auditorias de UI, Sage para avaliação de UX |
| 🎙️ Análise de Entrevistas | Transcreva, categorize, analise e relacione padrões em todo o seu grupo de participantes de uma vez |
| 🧭 Motor de Contexto | Baseie agentes na cultura da empresa, objetivos e diretrizes — quanto mais contexto, melhor a análise |
| 🛠️ 53+ Skills de Pesquisa | Análise competitiva, card sorting, jornada do usuário — agentes prontos para qualquer desafio |
| 🐝 Enxame de Agentes | Cinco especialistas que aprendem com resultados verificados e memória de processo por projeto |
| 🎨 Google Stitch e Figma | Geração de telas com IA, specs de handoff, auditoria de componentes — ponte design-dev num só lugar |
| 💬 Canais de Mensageria | Slack, Telegram, WhatsApp — colete dados onde seus usuários estão, gerenciado pelos agentes |
| 📊 Sincronização de Surveys | SurveyMonkey, Typeform, Google Forms — ingira respostas na Research Spine com fonte, revisão e confiabilidade |
| 🔄 Autoresearch | Experimentos de auto-melhoria em sandbox — mudanças candidatas de prompt/RAG/modelo viram propostas governadas antes de uso em produção |
| 🧾 Governança de Melhorias | Mudanças de auto-evolução são por projeto, baseadas em evidência, aprovadas por governança, reversíveis e impedidas de contornar a Research Spine |
| ✅ Saúde do Ensemble | Codificação multi-modelo, métricas de confiabilidade, evidência de rota, revisão adversarial e reconciliação humana |

<details>
<summary><strong>Ver screenshots do produto</strong></summary>

<div align="center">
  <p><strong>Chat Inteligente:</strong> Converse com o contexto da sua pesquisa. Pergunte sobre achados, faça brainstorm com os agentes e obtenha respostas instantâneas baseadas nos seus dados.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.37.30.png" width="900" />

  <p><strong>Achados de Pesquisa Atômica:</strong> Extraia átomos candidatos, valide-os contra evidência de fonte, e então promova nuggets, fatos, insights e recomendações aceitos. Cada afirmação confiável permanece ligada à sua fonte original.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.37.34.png" width="900" />

  <p><strong>Conformidade com Leis de UX:</strong> Audite seus designs contra mais de 30 princípios psicológicos e heurísticas de Nielsen. Veja exatamente onde sua UI brilha ou precisa melhorar.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.38.34.png" width="900" />

  <p><strong>Gestão Autônoma de Tarefas:</strong> Um poderoso quadro Kanban onde os agentes assumem tarefas, executam skills e reportam o progresso em tempo real, enquanto outputs de pesquisa permanecem revisáveis até aprovação.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.38.47.png" width="900" />

  <p><strong>Atribuição Multi-Agente:</strong> Escolha o melhor agente para o trabalho. Direcione tarefas para especialistas como Pixel para auditorias de UI ou Sage para avaliação de UX.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.38.54.png" width="900" />

  <p><strong>Entrevistas e Transcrições:</strong> Istara pode transcrever, categorizar, analisar, relacionar e gerar relatórios de várias entrevistas ao mesmo tempo — incluindo mensagens de voz do WhatsApp e Telegram com transcrição automática Whisper e scoring de confiabilidade inter-codificador. Encontre insights compartilhados em todo o seu grupo de participantes!</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.01.png" width="900" />

  <p><strong>Motor de Contexto:</strong> Baseie seus agentes na cultura da sua empresa, objetivos do projeto e diretrizes específicas. Quanto mais eles sabem, melhor eles performam.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.08.png" width="900" />

  <p><strong>Catálogo de Skills:</strong> Mais de 50 skills de pesquisa prontas para uso. De Análise Competitiva a Card Sorting, seus agentes estão equipados para qualquer desafio de pesquisa.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.11.png" width="900" />

  <p><strong>Enxame Agentic:</strong> Conheça sua equipe—Cleo, Sentinel, Pixel, Sage e Echo. Cinco agentes especializados que aprendem com resultados verificados, telemetria por projeto e memória de processo governada.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.16.png" width="900" />

  <p><strong>Integração Google Stitch & Figma:</strong> Gere telas com IA, conecte ao Figma para specs de handoff, audite componentes e feche a lacuna entre intenção de design e implementação.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.28.png" width="900" />

  <p><strong>Canais de Mensageria:</strong> Implante sua pesquisa diretamente no Slack, Telegram ou WhatsApp. Colete dados onde seus usuários estão, gerenciado inteiramente por seus agentes.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.36.png" width="900" />

  <p><strong>Integrações de Pesquisa (Surveys):</strong> Puxe dados do SurveyMonkey, Typeform ou Google Forms. As respostas entram no mesmo pipeline de unidades de evidência, codificação, confiabilidade, revisão e portão de relatório usado por entrevistas e documentos.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.40.png" width="900" />

  <p><strong>Motor de Autoresearch:</strong> Ative loops de auto-melhoria em sandbox. Os agentes medem mudanças candidatas de prompt, RAG ou modelo, revertem após a avaliação e enviam candidatos bem-sucedidos para aprovação governada antes de uso em produção.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.39.59.png" width="900" />

  <p><strong>Saúde do Ensemble:</strong> Confiança através da verificação. Istara usa codificação multi-modelo, métricas de confiabilidade, evidência de rota, revisão adversarial, debates e reconciliação humana antes que evidências virem reportáveis.</p>
  <img src="Screenshots/Screenshot%202026-04-02%20at%2016.40.15.png" width="900" />
</div>

</details>

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

## Postura de Release, Testes e Segurança

O processo de release público do Istara agora é orientado por evidências. O
desenvolvimento passa por work orders, análise de impacto e gates do Compass
Forge; o histórico de testes fica em baselines curadas, não em registros
temporários espalhados.

- **Testes e evals:** veja [TESTING.md](TESTING.md),
  [testing/TESTING_STRATEGY.md](testing/TESTING_STRATEGY.md),
  [testing/AI_EVALS_STRATEGY.md](testing/AI_EVALS_STRATEGY.md) e
  [testing/TEST_HISTORY.md](testing/TEST_HISTORY.md). A suite cobre contratos
  backend, build/tipos/lint/unit do frontend, relay, simulação, benchmarks de
  orquestração, checagens live de LLM com perfil único, RAG, Prompt RAG,
  LLMLingua, DAG/ReAct, ReasoningBank, Memento Skills, Meta Hyperagents,
  controles de saída de pensamento e contratos de voz.
- **Segurança:** veja [SECURITY.md](SECURITY.md),
  [security/SECURITY_BENCHMARK.md](security/SECURITY_BENCHMARK.md),
  [security/RELEASE_SECURITY_READINESS.md](security/RELEASE_SECURITY_READINESS.md)
  e [a avaliação atual](security/ISTARA_SECURITY_ASSESSMENT_2026-05-08.md).
  O gate de release mapeia controles para OWASP ASVS, NIST SP 800-63-4,
  orientação do Better Auth, WebAuthn, OAuth Security BCP, riscos OWASP para
  LLMs/agentes, NIST AI RMF, SSDF, SLSA, OpenSSF Scorecard e GitHub Artifact
  Attestations.
- **Testes live de LLM:** testes live usam um único perfil OpenAI-compatible
  gitignored e o modelo fixo `google/gemma-4-e4b`. Endpoints e tokens privados
  nunca são commitados, e os testes não devem procurar nem carregar múltiplos
  modelos pesados.
- **Organização da documentação:** veja [DOCUMENTATION.md](DOCUMENTATION.md)
  para o mapa canônico de docs atuais, docs geradas, notas de compatibilidade,
  histórico de testes, evidências de segurança e markdown runtime ignorado.

---

## Por Que o Istara Existe

Pesquisadores de UX merecem ferramentas que respeitam seus dados, garantem rigor metodológico e melhoram com o uso — não plataformas SaaS que fazem upload de transcrições para servidores externos, cobram por usuário, e esquecem tudo no momento em que você fecha a aba.

O Istara roda inteiramente no seu hardware. Ele vem com cinco agentes de IA especializados, 53 skills de pesquisa UX e uma metodologia de cadeia de evidências fundamentada em pesquisas científicas revisadas por pares. Agentes e skills podem melhorar, mas somente por telemetria com escopo de projeto, resultados verificados, propostas governadas e portões da Research Spine.

**Sem nuvem. Sem assinatura. Evidência em primeiro lugar.**

---

## Istara vs. As Alternativas

| Capacidade | Istara | Alternativas |
|---|---|---|
| Privacidade de dados | 100% local — dados nunca saem da sua máquina | Upload para servidores do fornecedor |
| Memória dos agentes | Personas persistentes e evolutivas entre sessões | Chamadas de API sem estado |
| Metodologia de pesquisa | Research Spine com artefatos Atomic Research validados na fonte | Sumarização ad-hoc |
| Melhoria de skills | Saúde de skill verificada por projeto e mudanças de prompt governadas | Prompts estáticos |
| Criação de agentes | Fábrica de agentes em tempo de execução — sem código | Conjunto de funcionalidades fixo |
| Validação multi-modelo | Codificação de evidência, métricas de confiabilidade, evidência de rota e reconciliação | Modelo único, sem validação |
| Compressão de memória | Inspirado no LLMLingua, 30–74% de economia de tokens | Sem gestão de contexto longo |
| Conformidade UX | Auditoria automatizada das 30 Leis de UX | Não disponível |
| Compartilhamento de computação | Doe GPU via relay WebSocket — cluster da equipe | Pague por chamada de API |
| Pesquisa autônoma | Propostas de autoresearch em sandbox; sem mutação live antes de governança | Execução manual apenas |
| Canais de survey | WhatsApp, Telegram, Typeform, SurveyMonkey | Integrações limitadas |
| Preço | Gratuito, open source, licença MIT | R$X.XXX/ano SaaS |

---

## 1. 🧠 Agentes que Criam Outros Agentes

> *"Let Agents Design Agents"* — Zhou et al. (2026)

O Istara implementa uma **fábrica de agentes inspirada no Memento**, fundamentada na percepção de que a forma mais eficaz de estender um sistema de IA é fazer com que ele projete suas próprias extensões. Quando um agente existente detecta uma lacuna de capacidade — uma tarefa de pesquisa que não consegue executar bem — ele propõe um novo agente especializado: define a persona, seleciona as skills, escreve os protocolos e o registra no pipeline de orquestração.

**Sem mutação direta em produção. O sistema pode propor suas próprias extensões, mas a aprovação governada decide o que fica ativo.**

Os cinco agentes integrados carregam, cada um, quatro arquivos de persona evolutivos:

| Agente | Nome | Especialização |
|---|---|---|
| `istara-main` | **Cleo** | Pesquisadora principal — executa todas as 53 skills, lidera projetos, é sua interface |
| `istara-devops` | **Sentinel** | Guardião de integridade de dados — monitora saúde, audita registros órfãos, executa verificações |
| `istara-ui-audit` | **Pixel** | Especialista em conformidade WCAG — heurísticas de Nielsen, pontuação de acessibilidade |
| `istara-ux-eval` | **Sage** | Analista de carga cognitiva — jornadas de usuário, detecção de fricção em fluxos |
| `istara-sim` | **Echo** | Testadora end-to-end — simula usuários, executa 75 cenários de regressão |

A persona de cada agente é armazenada em quatro arquivos — `CORE.md` (identidade), `SKILLS.md` (capacidades), `PROTOCOLS.md` (regras de comportamento), `MEMORY.md` (aprendizados acumulados) — mas atualizações são limitadas por escopo de projeto, verificação e regras de governança. Metodologia protegida de pesquisa, limites de confiabilidade, autorização e portões de relatório não são reescritos silenciosamente.

### Pipeline de Auto-Evolução

```
Interação do usuário
      ↓
Agente registra sinal de processo com escopo de projeto
      ↓
Telemetria separa sucesso de ferramenta · sucesso de execução · verificação · qualidade de pesquisa · reportabilidade
      ↓
Aprendizado candidato rastreado: 3+ ocorrências · projeto ativo · janela de 30 dias · confiança · taxa de sucesso
      ↓
Governança bloqueia mutações protegidas de metodologia, portões e auth
      ↓
Aprendizado aprovado ou permitido é promovido para a superfície correta de persona/memória/protocolo
      ↓
Trabalhos futuros podem usar a melhoria, ainda dentro dos portões da Research Spine
```

Isso não é fine-tuning. É **evolução estruturada de prompts** — funciona com qualquer modelo local, incluindo modelos de 3B parâmetros em hardware modesto de consumidor.

As skills também se auto-evoluem. Cada invocação registra qualidade por combinação modelo × skill:

```python
ModelSkillStats(
    project_id="project-123",
    model_name="llama-3.2-3b",
    skill_name="thematic_analysis",
    success_rate=0.94,
    avg_quality_score=4.2,
    execution_count=47,
    last_improvement_proposed="2026-03-15"
)
```

Quando a qualidade cai abaixo do limite, o Istara exibe um diff entre o prompt atual e a revisão proposta. Você aprova ou rejeita. Skills que consistentemente produzem resultados verificados e válidos pela Research Spine ganham pontuações de saúde maiores e prioridade no roteamento dentro daquele projeto. Sucesso bruto de ferramenta, sozinho, não melhora uma skill.

Toda auto-melhoria agora passa por um contrato de **Governança de Melhorias** e pelo **Arquivo DGM-H**. Memórias de raciocínio e telemetria podem ser registradas automaticamente, enquanto mudanças de comportamento em prompts, configs, skills, agentes, UI, integrações, computação ou código backend viram propostas visíveis com evidências, métricas, aprovação, linhagem, pontuação de seleção de pais e rastreamento de rollback/reversão.

> **Referências:** Zhou et al. (2026) "Memento-Skills: Let Agents Design Agents" arXiv:2603.18743; Zhang et al. (2026) "Hyperagents: DGM-H Metacognitive Self-Modification for Cross-Domain Transfer" arXiv:2603.19461; Ouyang et al. (2026) "ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory" arXiv:2509.25140

---

## 2. 🔬 Validação Multi-Modelo com Revisão Humana

> *"Improving Factuality and Reasoning in Language Models through Multiagent Debate"* — Du et al. (2024)

Descobertas de pesquisa produzidas por um único LLM são não confiáveis. O Istara emprega um **pipeline de validação sensível à computação disponível** que prefere modelos distintos autorizados para o projeto quando eles estão saudáveis, usa validação dual-run quando há apenas dois modelos, e recorre a variações Self-MoA de um único modelo somente quando a computação está restrita. O sistema registra evidência de rota, identidade de modelo quando disponível, métricas de confiabilidade sobre unidades de evidência codificadas, estado de discordância e estado de revisão humana em vez de tratar uma resposta de modelo como fato de pesquisa.

### A Pilha de Validação

```
Fontes (transcrições, surveys, notas, tickets, diários, analytics)
      ↓
Unidades de evidência estáveis com span, participante, método e projeto
      ↓
Calibração de codificação aberta → codebook preliminar → freeze governado
      ↓
Modelos distintos autorizados ao projeto codificam independentemente
      ↓
Kappa/Alpha são calculados sobre matrizes de unidades de evidência codificadas
      ↓
Debate, revisão adversarial e reconciliação humana resolvem discordâncias
      ↓
Átomos/nuggets aceitos e reconciliados viram Fatos → Insights → Recomendações
      ↓
Somente tarefas aprovadas como Done geram evidências prontas para relatório
      ↓
Relatório com cadeia de evidência, confiabilidade, rota e estado de revisão
```

**As descobertas de pesquisa são restringidas por evidências, não magicamente imunes a erro.** O Istara armazena links de fonte, estado de revisão de tarefa, pontuações de consenso e metadados de discordância para que pesquisadores rejeitem trabalho fraco. Relatórios usam evidências de tarefas aprovadas como Done; tarefas ainda em revisão são excluídas.

O contrato de validade de pesquisa vive em [`docs/architecture/research-validity-contract.md`](docs/architecture/research-validity-contract.md). O contrato de auto-melhoria vive em [`docs/architecture/self-improvement-governance-contract.md`](docs/architecture/self-improvement-governance-contract.md). Kappa de Fleiss, Kappa de Cohen e Alpha de Krippendorff são aplicados a matrizes de unidades de evidência codificadas. Codificação qualitativa não é marcação por palavras-chave: modelos recebem protocolo protegido, codebook, critérios de inclusão/exclusão, exemplos, esquema de unidade de evidência, política de confiabilidade e portão de promoção antes de codificar. Autoresearch, ReasoningBank, Memento Skills, Meta-Hyperagent, auto-evolução, RAG/GraphRAG, Prompt-RAG e LLMLingua podem melhorar a qualidade do processo, mas não viram evidência de relatório nem contornam a Research Spine.

Quando três ou mais modelos distintos, saudáveis e autorizados ao projeto existem, o Istara usa por padrão o caminho multi-modelo de codificação/validação. Com dois modelos distintos, usa o caminho de dois codificadores. Com um modelo, pode rodar fallback estilo Self-MoA, mas o resultado é marcado como menor garantia e não pode ser apresentado como confiabilidade de ensemble completa.

> **Referências:** Fleiss (1971) "Measuring nominal scale agreement among many raters"; Cohen (1960) "A coefficient of agreement for nominal scales"; O'Connor & Joffe (2020) "Intercoder Reliability in Qualitative Research"; MacQueen et al. (1998) "Codebook Development for Team-Based Qualitative Analysis"; Wang et al. (2024) "Mixture-of-Agents Enhances Large Language Model Capabilities"; Du et al. (2023) "Improving Factuality and Reasoning in Language Models through Multiagent Debate"; Li et al. (2025) "Rethinking Mixture-of-Agents"; Zheng et al. (2023) "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena"

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

Em fluxos de pesquisa, ferramentas de contexto continuam subordinadas à Research Spine. Prompt RAG pode adicionar contexto de apoio, mas metodologia obrigatória de codificação, critérios de codebook, política de confiabilidade e portões de promoção são injetados deterministicamente pelos serviços relevantes. A compressão estilo LLMLingua preserva blocos protegidos de protocolo, codebook, esquema de evidência, confiabilidade, promoção e auth durante compressão e corte final.

> **Referências:** Jiang et al. (2023) "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models" EMNLP 2023; Chen et al. (2023) "Walking Down the Memory Maze: Beyond Context Limit through Interactive Reading" arXiv:2310.05029; Pan et al. (2024) "From RAG to Prompt RAG" ACL 2024

---

## 4. 🖥️ Enxame de Computação Distribuída

> *"Petals: Collaborative Inference and Fine-tuning of Large Models"* — Borzunov et al. (2022/2023)

O hardware ocioso da sua equipe é um cluster esperando para ser usado. O **Compute Relay** do Istara implementa uma rede de inferência por requisição completa baseada em WebSocket, onde membros da equipe doam capacidade de GPU ou CPU disponível para um pool com escopo de projeto. As requisições de inferência são roteadas para os nós disponíveis com **agendamento por prioridade, detecção automática de capacidade, contadores de rota e failover**.

Ele é inspirado no Petals no sentido de colaboração, mas não é equivalente ao Petals com particionamento de camadas de transformer. O Istara doa e roteia requisições completas de chat, embeddings e servidores de modelo por nós autorizados.

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
rcl_<convite-assinado-de-usuario-ou-computacao>
```

Strings de convite de usuário não carregam um JWT de login pré-gerado; elas são resgatadas em uma sessão controlada pelo servidor e códigos de recuperação.

> **Referências:** Borzunov et al. (2022) "Petals: Collaborative Inference and Fine-tuning of Large Models" arXiv:2209.01188; Borzunov et al. (2023) "Distributed Inference and Fine-tuning of Large Language Models Over the Internet" NeurIPS 2023

---

## 5. 🔎 Autoresearch do Karpathy Integrado

> *"autoresearch: autonomous experiment loops for AI systems"* — Karpathy (2026)

O Istara inclui um **motor autônomo de otimização de pesquisa** inspirado no framework autoresearch de Karpathy. Ele executa experimentos controlados com escopo de projeto para melhorar a qualidade do processo — testando parâmetros de recuperação RAG, templates de prompt de skills, configurações de temperatura dos modelos e configurações relacionadas sem deixar o experimento mutar estado de produção.

Experimentos são executados em sandbox, com limite de taxa, reversíveis e não-reportáveis. Um experimento bem-sucedido vira proposta governada, não mudança automática em produção.

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
Se melhoria ≥ limite: reverte a mutação de sandbox e cria candidato proposal_ready
      ↓
Revisão governada aprova, rejeita ou arquiva a proposta com evidência de rollback
      ↓
Repete: próxima hipótese
```

O sistema mantém um painel **Monitor de Saúde de Skills** exibindo tendências de desempenho por skill, quais experimentos estão em execução, quais propostas aguardam revisão e quais mudanças governadas foram aprovadas. Artefatos de autoresearch são somente evidência de processo; não podem virar achados de pesquisa nem evidência de relatório.

> **Referência:** Karpathy (2026) "autoresearch" github.com/karpathy/autoresearch

---

## 6. 📊 Cadeia de Evidências Atomic Research

> *"The Atomic Research model"* — Sharon & Gadbaw (2018)

Cada insight que o Istara produz deve permanecer rastreável porque se conecta a uma cadeia de evidências verificada com referências de fonte e estado de revisão de tarefa. Isso implementa a metodologia de Atomic Research desenvolvida na WeWork (Sharon & Gadbaw, 2018) como um pipeline computacional.

```
Citação bruta ou observação de fonte
      ↓  cria: unidade de evidência com texto exato + proveniência
Átomo/nugget candidato
      ↓  requer: extração/codificação independente + grounding + confiabilidade/reconciliação
Átomo/nugget aceito
      ↓  promove: padrão verificado, fato, insight, recomendação
Evidência de relatório
      ↓  requer: evidência aceita/reconciliada em tarefa Done aprovada por humano
```

**Sem recomendação reportável sem insight aceito. Sem insight aceito sem fatos aceitos. Sem fato aceito sem átomos/nuggets aceitos. Sem átomo/nugget aceito sem validação fundamentada na fonte.**

Cada nível da cadeia é armazenado como um registro discreto no banco de dados com relacionamentos de chave estrangeira impondo a hierarquia. Artefatos de Atomic Research não são confiáveis só porque um modelo os escreveu; outputs brutos de modelo permanecem candidatos/provisórios até que a Research Spine os aceite ou reconcilie. Relatórios usam achados de tarefas aprovadas como Done; outputs de tarefas ainda em revisão não são evidência de relatório. Quando você exporta um relatório de pesquisa, cada recomendação deve voltar pela cadeia até a passagem exata de entrevista, resposta de survey ou observação que a sustenta.

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

RAG Híbrido é a camada de recuperação de evidência exata do Istara. O fallback BM25 preserva `evidence_unit_id`, span de documento/fonte, estado de revisão, estado de confiabilidade e proveniência; quando essa proveniência falta, o resultado é marcado como não-promocional. Evidence Graph / GraphRAG é a camada de síntese e rastreabilidade, usada para relações entre documentos e perguntas de dependência, mas respostas em grafo precisam preencher a evidência exata via RAG Híbrido antes de qualquer promoção.

**O LanceDB é embutido** — sem processo de banco de dados vetorial separado, sem sobrecarga de rede, sem configuração.

> **Referências:** Lewis et al. (2020) "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" NeurIPS 2020; Cormack et al. (2009) "Reciprocal rank fusion outperforms condorcet and individual rank learning methods" SIGIR 2009; Robertson & Zaragoza (2009) "The Probabilistic Relevance Framework: BM25 and Beyond" *Foundations and Trends in Information Retrieval* 3(4)

---

## 8. 📱 Deploy de Surveys e Entrevistas no WhatsApp e Telegram

> *"AURA: Adaptive User Research Assistant"* — arXiv:2510.27126

O Istara suporta **fluxos de entrevista adaptativa no estilo AURA** e caminhos de configuração com credenciais para canais de mensagens e surveys. Canais reais com participantes exigem credenciais do provedor ou simuladores de teste delimitados; sem isso, o Istara documenta o caminho de configuração/erro em vez de fingir uma implantação real com participantes.

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
Registra fonte bruta → extrai unidades de evidência → cria átomos/códigos candidatos
      ↓
Executa confiabilidade, grounding, reconciliação e portões de revisão
      ↓
Verificação de detecção de IA sinaliza respostas que parecem geradas por máquina
```

O motor de entrevista adaptativa deve ajustar dinamicamente a formulação e a ordem das perguntas com base nas respostas anteriores, produzindo dados qualitativos mais ricos do que formulários de survey estáticos quando a integração do canal está configurada. Respostas importadas não viram achados confiáveis diretamente; elas entram na mesma Research Spine de documentos, entrevistas e notas manuais.

> **Referência:** AURA: Adaptive User Research Assistant, arXiv:2510.27126

---

## 9. 🎨 Figma + Ferramentas de Design de IA Google Stitch

O Istara conecta pesquisa e design em um único fluxo de trabalho:

- **Integração Figma**: Importe arquivos de design, extraia tokens de design system, vincule decisões de design a evidências aceitas/reconciliadas, execute verificações de conformidade com as Leis de UX
- **Google Stitch MCP**: Gere wireframes de tela e conceitos de UI a partir de insights aceitos e evidência candidata claramente marcada — descreva o que os usuários precisam, receba propostas de design
- **Design Briefs**: Gere automaticamente design briefs a partir de achados reportáveis, com referências às Leis de UX anexadas a cada recomendação
- **Rastreabilidade Evidência-para-Design**: Cada decisão de design reportável se conecta de volta a átomos/nuggets aceitos e à evidência de fonte que a motivou

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
Extrai unidades de evidência → cria átomos/códigos candidatos → valida/reconcilia antes de tarefas
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

> **Referências:** Model Context Protocol (2025) "MCP Specification" modelcontextprotocol.io; Agent2Agent Project (2026) "A2A Protocol Specification" a2a-protocol.org

---

## 13. 🛡️ Segurança e Privacidade por Design

O Istara é **zero-trust por padrão**:

- **Autenticação JWT** em todos os endpoints de API — nenhum acesso não autenticado
- **Endurecimento de conta inspirado no Better Auth** — o primeiro admin recebe códigos de recuperação de uso único no onboarding, a configuração de passkey é oferecida imediatamente, usuários podem mudar username/perfil/senha em Configurações, e usuários criados por admin recebem códigos de recuperação de uso único
- **Opções de segundo fator** — login com senha pode exigir TOTP, códigos de recuperação são o fator de fallback, e WebAuthn/passkeys oferecem login passwordless resistente a phishing; o Istara não usa SMS nem OTP por email
- **Criptografia de campo Fernet** em campos sensíveis do banco de dados — segredos criptografados em repouso
- **Criptografia de arquivos e backups administrada por admin** — quando habilitada, uploads gerenciados, texto armazenado de documentos e backups futuros são criptografados em repouso; backups são gravados como `.tar.gz.enc` e exigem a chave correta para restauração
- **Tratamento seguro de chaves** — a chave de criptografia de arquivos deve ficar em um gerenciador de segredos ou no macOS Keychain, com fallback para arquivo local apenas-leitura-do-dono em instalações source; perder a chave é destrutivo para arquivos e backups criptografados
- **Arquitetura local-first** — a inferência de LLM roda no seu hardware via LM Studio ou Ollama; nenhum dado é transmitido para APIs externas a menos que você configure explicitamente uma
- **Servidor MCP DESATIVADO por padrão** — o acesso externo de agentes requer opt-in consciente
- **Banco de dados SQLite** — um único arquivo portátil sob seu controle completo
- **Sem telemetria externa** — o Istara registra eventos locais de processo, rota, qualidade e governança para auditoria, mas nunca os envia para um serviço externo

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                       FRONTEND (Next.js 14)                         │
│  Chat · Kanban · Achados · Documentos · Skills · Agentes · Config   │
│  22 visões · Onboarding contextual por visão · Modo escuro/claro    │
│  Estado Zustand · Conformidade WCAG 2.1 AA · Bandeja Tauri          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST (400+ endpoints) + WebSocket (16 eventos)
┌────────────────────────────▼────────────────────────────────────────┐
│                         BACKEND (FastAPI)                           │
│                                                                     │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ 400+ REST  │  │ WebSocket  │  │ Servidor MCP│  │ Protocolo   │  │
│  │  endpoints │  │  Manager   │  │  (opt-in)   │  │ A2A         │  │
│  └──────┬─────┘  └──────┬─────┘  └──────┬──────┘  └──────┬──────┘  │
│         └───────────────┴───────────────┴─────────────────┘        │
│                                    │                                │
│  ┌─────────────────────────────────▼──────────────────────────┐    │
│  │                      MOTOR CENTRAL                         │    │
│  │                                                            │    │
│  │  MetaOrchestrator (roteamento de mensagens A2A)            │    │
│  │  Hierarquia de Contexto (6 níveis) + Sumarizador DAG       │    │
│  │  RAG Híbrido: LanceDB + BM25 + RRF + estado proveniência   │    │
│  │  Evidence Graph / GraphRAG para rastreabilidade e síntese  │    │
│  │  Compressor LLMLingua com blocos protegidos da Spine       │    │
│  │  Governança de Auto-Melhoria + Saúde de Skills             │    │
│  │  Propostas de Autoresearch em sandbox, não mutações live   │    │
│  │  Codificação/Validação multi-modelo (Kappa/Alpha + rota)   │    │
│  │  Governador de Recursos + Agendador por Prioridade         │    │
│  │  Cadeia Atomic Research aceita (Atom→Fato→Insight→Rec)     │    │
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
| Evolução de Skill | Propor melhorias governadas de prompt/skill a partir de resultados verificados pela Research Spine |
| Conformidade com Leis de UX | Auditoria automatizada contra as 30 Leis de UX |
| Gerador de Design Brief | Gerar design briefs a partir de descobertas de pesquisa |
| Validador de Cadeia de Evidências | Verificar vinculação átomo/nugget aceito → fato → insight → recomendação |
| Validador Multi-modelo | Validar unidades de evidência de fonte com modelos distintos autorizados por projeto e métricas de confiabilidade |
| Otimizador de Autoresearch | Executar experimentos de otimização em sandbox que produzem propostas governadas de melhoria |

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

Echo é a agente de garantia de qualidade. Ela executa a suíte de teste de simulação com 75 cenários, realiza testes de regressão em fluxos de trabalho de pesquisa, e valida que mudanças no sistema não quebram pipelines de pesquisa existentes.

**Capacidades principais:** Suite de testes E2E com 75 cenários · Testes de regressão · Simulação de usuário · Validação de endpoints de API · Benchmarking de performance

</details>

---

## Screenshots

<!-- TODO: Adicionar screenshots após o primeiro deploy público -->
*Referências adicionais de arquitetura e processo estão em [DOCUMENTATION.md](DOCUMENTATION.md).*

---

## Estrutura do Repositório

```
istara/
├── backend/                   # Backend FastAPI (Python 3.12)
│   └── app/
│       ├── api/               # 400+ endpoints REST + manager WebSocket
│       ├── agents/            # Personas dos agentes (CORE, SKILLS, PROTOCOLS, MEMORY)
│       ├── core/              # Orquestrador, RAG, motor de evolução, autoresearch
│       ├── models/            # 51+ modelos SQLAlchemy 2.0
│       ├── services/          # Integrações de survey, MCP, canais, relay de computação
│       └── skills/            # Classe base de skill, fábrica, 53 implementações
├── frontend/                  # Next.js 14 (React, Tailwind CSS, Zustand)
│   └── src/
│       ├── components/        # 22 visões + componentes UI compartilhados
│       ├── stores/            # Gerenciamento de estado Zustand
│       └── lib/               # Cliente API, helpers de rota, tipos compartilhados
├── desktop/                   # Aplicativo Tauri v2 para bandeja do sistema
├── installer/                 # Configs de build macOS DMG + Windows NSIS + Linux AppImage
├── relay/                     # Servidor relay WebSocket para doação de computação
├── skills/                    # Arquivos de definição de skill (SKILL.md por skill)
├── security/                  # Matriz de benchmark, checklist de release e avaliações
├── testing/                   # Estratégia de testes, evals, benchmarks e histórico
├── tests/
│   └── simulation/            # Suite de testes E2E com 75 cenários de simulação
└── scripts/                   # Verificações de integridade, atualizadores de MEMORY.md de agentes
```

---

## Contribuindo

O Istara tem licença MIT e aceita ativamente contribuições. Áreas de alto impacto:

- **Novas skills de pesquisa** — Adicione um `SKILL.md` + definição JSON. Sem Python necessário para a maioria das skills.
- **Adaptadores de LLM** — Suporte para novos backends de inferência local
- **Integrações de canais** — Discord, Microsoft Teams, Signal, etc.
- **Componentes de UI** — Melhorias de acessibilidade, novas visões de pesquisa
- **Metodologia de pesquisa** — Prompts melhorados e lógica de validação, com mudanças protegidas de protocolo/portões sob governança
- **Citações acadêmicas** — Conecte funcionalidades a literatura de pesquisa relevante

```bash
# Execute a suite de testes do backend
pytest tests/

# Execute o agente de simulação E2E com 75 cenários
node tests/simulation/run.mjs

# Verifique a integridade do sistema antes de commitar
python scripts/check_integrity.py

# Verifique governança, segurança e release
python scripts/check_ci_governance.py
python scripts/security_benchmark.py --fail-on-threshold
python scripts/security_release_readiness.py
python scripts/production_rehearsal.py --json
```

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para instruções de configuração, guia de estilo de código e checklist de mudanças.
Veja [TESTING.md](TESTING.md), [SECURITY.md](SECURITY.md) e [DOCUMENTATION.md](DOCUMENTATION.md) antes de mudanças sensíveis para release.

---

## Referências Acadêmicas e Padrões

<details>
<summary><strong>Bibliografia e padrões completos (38 referências)</strong></summary>

### Auto-Evolução e Design de Agentes

1. **Zhou et al. (2026)** — "Memento-Skills: Let Agents Design Agents" *arXiv:2603.18743*. O artigo fundacional para a fábrica de agentes do Istara: agentes detectando lacunas de capacidade e projetando novos agentes especializados.

2. **Zhang et al. (2026)** — "Hyperagents: DGM-H Metacognitive Self-Modification for Cross-Domain Transfer and Recursive Improvement" *arXiv:2603.19461*. Framework para auto-modificação metacognitiva em agentes autônomos; informa o pipeline de evolução de skills do Istara.

### Validação Multi-Modelo

3. **Fleiss, J. L. (1971)** — "Measuring Nominal Scale Agreement among Many Raters" *Psychological Bulletin* 76(5):378-382. DOI: 10.1037/h0031619. Usado para confiabilidade de 3+ codificadores em matrizes nominais item-por-avaliador.

4. **Cohen, J. (1960)** — "A Coefficient of Agreement for Nominal Scales" *Educational and Psychological Measurement* 20(1):37-46. DOI: 10.1177/001316446002000104. Usado para confiabilidade com dois codificadores.

5. **O'Connor & Joffe (2020)** — "Intercoder Reliability in Qualitative Research: Debates and Practical Guidelines" *International Journal of Qualitative Methods*. DOI: 10.1177/1609406919899220. Usado para o processo de codificação independente e reconciliação.

6. **MacQueen et al. (1998)** — "Codebook Development for Team-Based Qualitative Analysis" *Cultural Anthropology Methods* 10(2):31-36. DOI: 10.1177/1525822X980100020301. Usado para definições de códigos, critérios de inclusão/exclusão e disciplina de codebook em equipe.

7. **Wang et al. (2024)** — "Mixture-of-Agents Enhances Large Language Model Capabilities" *arXiv:2406.04692*. Inspiração para a camada de validação multi-agente do Istara.

8. **Du et al. (2023)** — "Improving Factuality and Reasoning in Language Models through Multiagent Debate" *arXiv:2305.14325*. Protocolo de debate adversarial para reduzir outputs sem suporte; implementado como caminho de validação/refinamento no Istara.

9. **Li et al. (2025)** — "Rethinking Mixture-of-Agents: Is Mixing Different Large Language Models Beneficial?" *arXiv:2502.00674*. Variante Self-MoA de modelo único para ambientes com computação limitada.

10. **Zheng et al. (2023)** — "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" *NeurIPS 2023*. Metodologia LLM-as-Judge usada somente como validação auxiliar, não como substituto de evidência, confiabilidade e revisão humana.

### Memória e Gestão de Contexto

11. **Jiang et al. (2023)** — "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models" *EMNLP 2023*. Compressão de prompt; o Istara protege blocos de metodologia, codebook, evidência e confiabilidade contra perda por compressão.

12. **Jiang et al. (2023)** — "LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression" *arXiv:2310.06839*. Referência de compressão para contexto longo; blocos protegidos de validade de pesquisa não são compressíveis.

13. **Chen et al. (2023)** — "Walking Down the Memory Maze: Beyond Context Limit through Interactive Reading" *arXiv:2310.05029*. Sumarização hierárquica baseada em DAG do MemWalker; implementada na hierarquia de contexto do Istara.

14. **Pan et al. (2024)** — "From RAG to Prompt RAG: Revisiting Retrieval-Augmented Generation for Long-Context Language Models" *ACL 2024*. Prompt RAG para injetar contexto recuperado no momento da inferência; o Istara ainda injeta metodologia obrigatória de codificação de forma determinística.

15. **Ouyang et al. (2026)** — "ReasoningBank: Scaling Agent Self-Evolving with Reasoning Memory" *arXiv:2509.25140*. Memória estruturada de raciocínio para destilar trajetórias bem-sucedidas e falhas de agentes em estratégias reutilizáveis; implementada como camada compartilhada de memória de orquestração para roteamento Memento, autoresearch e observação meta-agente.

### Geração Aumentada por Recuperação

16. **Lewis et al. (2020)** — "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" *NeurIPS 2020*. O artigo fundacional de RAG; a recuperação híbrida do Istara é a camada de evidência exata.

17. **Edge et al. (2024)** — "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" *arXiv:2404.16130*. Base para síntese global estilo GraphRAG; o Istara usa síntese em grafo apenas sobre evidência rastreável e nunca como bypass de codificação, confiabilidade e revisão.

18. **Microsoft Research GraphRAG / LazyGraphRAG / DRIFT Search** — Documentação oficial da Microsoft Research e GraphRAG. Usada para conceitos de busca local/global/DRIFT e desenho de recuperação em grafo com custo controlado.

19. **Cormack et al. (2009)** — "Reciprocal rank fusion outperforms condorcet and individual rank learning methods" *SIGIR 2009*. Algoritmo RRF mesclando rankings de busca vetorial e por palavras-chave no Istara.

20. **Robertson & Zaragoza (2009)** — "The Probabilistic Relevance Framework: BM25 and Beyond" *Foundations and Trends in Information Retrieval* 3(4). Componente de busca por palavras-chave BM25 da recuperação híbrida do Istara.

### Computação Distribuída

21. **Borzunov et al. (2022)** — "Petals: Collaborative Inference and Fine-tuning of Large Models" *arXiv:2209.01188*. Arquitetura de inferência distribuída; o Compute Relay do Istara é inspirado no Petals.

22. **Borzunov et al. (2023)** — "Distributed Inference and Fine-tuning of Large Language Models Over the Internet" *NeurIPS 2023*.

### Canais de Survey e Entrevista

23. **AURA (2025)** — "AURA: Adaptive User Research Assistant" *arXiv:2510.27126*. Arquitetura de agente de entrevista adaptativa implantada pelo Istara em canais de mensagens.

### Metodologia de Pesquisa

24. **Sharon & Gadbaw (2018)** — "Atomic Research" WeWork Research Operations. O Istara implementa Atomic Research como cadeia de evidências aceita e validada na fonte: Atom/Nugget→Fato→Insight→Recomendação.

25. **Yablonski, J. (2020)** — *Laws of UX: Design Principles for Persuasive and Ethical Products*. O'Reilly Media. As 30 Leis de UX auditadas pelo verificador de conformidade do Istara.

26. **Karpathy, A. (2026)** — "autoresearch: autonomous experiment loops for AI systems" github.com/karpathy/autoresearch. Framework de otimização autônoma; implementado como motor de autoresearch do Istara.

### Padrões de Interoperabilidade

21. **Model Context Protocol (2025)** — "MCP Specification" modelcontextprotocol.io. Padrão aberto para interações LLM aumentadas por ferramentas; o Istara expõe um servidor MCP.

22. **Agent2Agent Project (2026)** — "Agent2Agent (A2A) Protocol Specification" a2a-protocol.org. Padrão de descoberta e comunicação de agentes; o Istara publica um manifesto de descoberta A2A.

### Avaliação e Benchmarks

23. **OpenAI (2026)** — "Evals" github.com/openai/evals e documentação da API de Evals da OpenAI. Modelo de framework e registry para avaliações repetíveis de LLMs e sistemas.

24. **UK AI Security Institute (2026)** — "Inspect AI" inspect.aisi.org.uk. Padrão de harness de avaliação para avaliações reprodutíveis de modelos e agentes.

25. **Liang et al. (2022)** — "Holistic Evaluation of Language Models" Stanford CRFM HELM. Inspiração de avaliação multi-métrica para baselines versionadas do Istara.

26. **Es et al. (2023)** — "RAGAS: Automated Evaluation of Retrieval Augmented Generation" *arXiv:2309.15217*. Base para avaliação de RAG em fidelidade, relevância de contexto e relevância da resposta.

27. **Berkeley Sky Computing Lab (2026)** — "Berkeley Function Calling Leaderboard (BFCL) V4" gorilla.cs.berkeley.edu. Inspiração de benchmark para correção de chamadas de ferramentas/funções nos testes ReAct e schemas de skills do Istara.

28. **Yao et al. (2024)** — "tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains" *arXiv:2406.12045*. Inspiração para avaliação multi-turno de ferramenta-agente-usuário nas simulações e fluxos agentic do Istara.

### Segurança, Identidade e Padrões de Release

29. **OWASP (2025)** — "Application Security Verification Standard 5.0.0" owasp.org. Baseline de segurança de aplicação para a matriz de benchmark do Istara.

30. **NIST (2025)** — "Digital Identity Guidelines, SP 800-63-4 and SP 800-63B-4" pages.nist.gov. Orientação de identidade, autenticadores, MFA, passkeys e sessão.

31. **Better Auth (2026)** — "Security" better-auth.com/docs/reference/security. Referência comparativa para base URLs, trusted origins, sessões, salvaguardas CSRF, rate limiting e tratamento de segredos.

32. **W3C (2026)** — "Web Authentication: An API for accessing Public Key Credentials, Level 3" w3.org/TR/webauthn-3. Referência de passkeys/WebAuthn para validação de origem/RP e credenciais de chave pública.

33. **IETF (2025)** — "OAuth 2.0 Security Best Current Practice, RFC 9700" datatracker.ietf.org. Orientação de segurança para integrações OAuth/OpenID-style.

34. **OWASP GenAI Security Project (2025)** — "OWASP Top 10 for LLM Applications 2025" genai.owasp.org. Modelo de ameaças para prompt injection, vazamento sensível, fronteiras de modelo/provedor e abuso de ferramentas.

35. **NIST (2023–2026)** — "AI Risk Management Framework 1.0" e recursos do perfil GenAI. Governança de risco de IA para orquestração agentic, telemetria, avaliação e rollback.

36. **Model Context Protocol (2025)** — "MCP Specification 2025-11-25" modelcontextprotocol.io. Modelo de ferramentas, prompts, recursos, autorização e trust/safety para integrações MCP.

37. **Agent2Agent Project (2026)** — "Agent2Agent (A2A) Protocol Specification" a2a-protocol.org. Referência de descoberta por agent-card e interoperabilidade JSON-RPC.

38. **OpenSSF / SLSA / GitHub (2026)** — OpenSSF Scorecard, SLSA v1.2 e GitHub Artifact Attestations. Referências de postura de supply chain e proveniência de release para hardening de instaladores.

</details>

---

## Licença

MIT © 2026 Istara Contributors — veja [LICENSE](LICENSE).

---

<div align="center">

Construído para pesquisadores que acreditam que seus dados devem pertencer a eles.

**Autônomo. Auto-evolutivo. Zero-trust. Evidência em primeiro lugar.**

[GitHub](https://github.com/henrique-simoes/Istara) · [Issues](https://github.com/henrique-simoes/Istara/issues) · [Discussões](https://github.com/henrique-simoes/Istara/discussions)

</div>
