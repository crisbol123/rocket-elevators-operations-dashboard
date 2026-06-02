# Stage 1: build
FROM golang:1.26-alpine AS builder

WORKDIR /app
COPY go.mod ./
COPY *.go ./
RUN go build -o rocket-elevators-api .

# Stage 2: runtime
FROM alpine:3.20

RUN apk --no-cache add ca-certificates
WORKDIR /app
COPY --from=builder /app/rocket-elevators-api .

EXPOSE 8081
CMD ["./rocket-elevators-api"]
