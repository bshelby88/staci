FROM node:20-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package.json /app/kernel-link/
COPY . /app
RUN npm install --omit=dev --no-audit --no-fund
CMD ["node", "server.js"]
