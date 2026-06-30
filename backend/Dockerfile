FROM golang:1.22-alpine AS build
WORKDIR /app/backend
COPY backend/go.mod backend/go.sum* ./
RUN go mod download
COPY backend/ ./
RUN go build -o /out/maelstrom ./cmd/server

FROM alpine:3.20
WORKDIR /app
RUN adduser -D -u 10001 appuser
COPY --from=build /out/maelstrom /usr/local/bin/maelstrom
COPY backend/migrations /app/backend/migrations
USER appuser
EXPOSE 8080
CMD ["maelstrom"]
