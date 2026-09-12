FROM node:24-bookworm-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json tsconfig.base.json ./
COPY packages/ packages/
COPY apps/dashboard/ apps/dashboard/
RUN npm ci --no-audit --no-fund && npm run build
USER node
EXPOSE 3000
CMD ["node", "node_modules/next/dist/bin/next", "start", "apps/dashboard", "--hostname", "0.0.0.0", "--port", "3000"]
