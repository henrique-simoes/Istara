FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install --production

COPY . .

CMD ["node", "index.mjs", "--server", "${ISTARA_SERVER:-ws://localhost:8000/ws/relay}", "--provider", "${LLM_PROVIDER:-ollama}", "--llm-host", "${LLM_HOST:-http://localhost:11434}"]
