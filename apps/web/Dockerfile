FROM node:20-alpine

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json* ./
COPY apps/web/package.json ./apps/web/package.json

RUN npm ci --workspace apps/web

COPY apps/web ./apps/web

WORKDIR /app

EXPOSE 3000

CMD ["npm", "--workspace", "apps/web", "run", "dev", "--", "--hostname", "0.0.0.0"]
