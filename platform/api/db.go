package main

import (
	"context"
	"fmt"
	"net/http"
	"os"

	"github.com/jackc/pgx/v5/pgxpool"
)

var db *pgxpool.Pool

func initDB() error {
	dsn := fmt.Sprintf(
		"host=%s port=%s dbname=%s user=%s password=%s sslmode=disable",
		getenv("POSTGRES_HOST", "localhost"),
		getenv("POSTGRES_PORT", "5432"),
		getenv("POSTGRES_DB", "rocket_elevators"),
		getenv("POSTGRES_USER", "rocket_user"),
		getenv("POSTGRES_PASSWORD", "rocket_pass"),
	)

	cfg, err := pgxpool.ParseConfig(dsn)
	if err != nil {
		return fmt.Errorf("parse db config: %w", err)
	}
	cfg.MaxConns = 10

	pool, err := pgxpool.NewWithConfig(context.Background(), cfg)
	if err != nil {
		return fmt.Errorf("create db pool: %w", err)
	}

	if err := pool.Ping(context.Background()); err != nil {
		return fmt.Errorf("db ping: %w", err)
	}

	db = pool
	fmt.Println("Database connection established")
	return nil
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	if err := db.Ping(context.Background()); err != nil {
		writeErr(w, http.StatusServiceUnavailable, "database unavailable")
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
