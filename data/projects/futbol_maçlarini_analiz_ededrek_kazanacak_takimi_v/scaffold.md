```plaintext
futvision/
├── README.md
├── .env.example
├── docker-compose.yml
├── Makefile
├── backend/
│   ├── go/
│   │   ├── go.mod
│   │   ├── go.sum
│   │   ├── cmd/
│   │   │   ├── api-gateway/
│   │   │   │   └── main.go
│   │   │   ├── auth-service/
│   │   │   │   └── main.go
│   │   │   ├── data-ingestion/
│   │   │   │   └── main.go
│   │   │   ├── match-service/
│   │   │   │   └── main.go
│   │   │   ├── prediction-orchestrator/
│   │   │   │   └── main.go
│   │   │   ├── odds-service/
│   │   │   │   └── main.go
│   │   │   └── notification-service/
│   │   │       └── main.go
│   │   └── internal/
│   │       ├── config/
│   │       │   └── config.go
│   │       ├── database/
│   │       │   ├── db.go
│   │       │   ├── models.go
│   │       │   └── migrations/
│   │       │       └── 001_initial.up.sql
│   │       ├── redis/
│   │       │   └── client.go
│   │       ├── http/
│   │       │   ├── middleware/
│   │       │   │   ├── auth.go
│   │       │   │   ├── cors.go
│   │       │   │   └── logging.go
│   │       │   └── responses/
│   │       │       └── json.go
│   │       ├── prediction/
│   │       │   ├── models.go
│   │       │   ├── poisson.go
│   │       │   ├── elo.go
│   │       │   ├── form.go
│   │       │   └── orchestrator.go
│   │       └── utils/
│   │           ├── logger.go
│   │           └── errors.go
│   └── python/
│       ├── pyproject.toml
│       ├── requirements.txt
│       ├── ml-service/
│       │   ├── src/
│       │   │   ├── __init__.py
│       │   │   ├── main.py
│       │   │   ├── models.py
│       │   │   ├── inference.py
│       │   │   └── utils.py
│       │   └── Dockerfile
│       └── llm-service/
│           ├── src/
│           │   ├── __init__.py
│           │   ├── main.py
│           │   ├── prompts.py
│           │   ├── client.py
│           │   └── utils.py
│           └── Dockerfile
├── frontend/
│   ├── web/
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── vite.config.ts
│   │   ├── tailwind.config.js
│   │   ├── postcss.config.js
│   │   ├── index.html
│   │   ├── public/
│   │   └── src/
│   │       ├── main.tsx
│   │       ├── App.tsx
│   │       ├── components/
│   │       │   ├── MatchList.tsx
│   │       │   ├── TeamCard.tsx
│   │       │   ├── PredictionDisplay.tsx
│   │       │   └── StreamingProgress.tsx
│   │       ├── pages/
│   │       │   ├── HomePage.tsx
│   │       │   ├── MatchDetailPage.tsx
│   │       │   ├── ProfilePage.tsx
│   │       │   └── LoginPage.tsx
│   │       ├── services/
│   │       │   ├── api.ts
│   │       │   └── auth.ts
│   │       ├── hooks/
│   │       │   └── usePredictions.ts
│   │       ├── store/
│   │       │   ├── index.ts
│   │       │   └── slices/
│   │       │       ├── matchesSlice.ts
│   │       │       └── predictionsSlice.ts
│   │       ├── styles/
│   │       │   └── globals.css
│   │       └── types/
│   │           └── index.ts
│   └── mobile/
│       ├── package.json
│       ├── app.json
│       ├── tsconfig.json
│       ├── babel.config.js
│       ├── metro.config.js
│       ├── index.js
│       ├── App.tsx
│       ├── src/
│       │   ├── screens/
│       │   │   ├── MatchListScreen.tsx
│       │   │   ├── MatchDetailScreen.tsx
│       │   │   └── ProfileScreen.tsx
│       │   ├── components/
│       │   │   ├── MatchCard.tsx
│       │   │   ├── PredictionCard.tsx
│       │   │   └── TeamBadge.tsx
│       │   ├── navigation/
│       │   │   └── AppNavigator.tsx
│       │   ├── services/
│       │   │   └── api.ts
│       │   ├── hooks/
│       │   │   └── usePrediction.ts
│       │   ├── store/
│       │   │   └── index.ts
│       │   └── utils/
│       │       └── constants.ts
├── infrastructure/
│   ├── docker-compose.yml
│   ├── k8s/
│   │   ├── namespaces/
│   │   │   └── futvision.yaml
│   │   ├── configmaps/
│   │   │   ├── api-gateway-config.yaml
│   │   │   └── shared-config.yaml
│   │   ├── secrets/
│   │   │   └── sealed-secrets.yaml
│   │   ├── deployments/
│   │   │   ├── api-gateway.yaml
│   │   │   ├── auth-service.yaml
│   │   │   ├── data-ingestion.yaml
│   │   │   ├── match-service.yaml
│   │   │   ├── prediction-orchestrator.yaml
│   │   │   ├── ml-service.yaml
│   │   │   ├── llm-service.yaml
│   │   │   ├── odds-service.yaml
│   │   │   └── notification-service.yaml
│   │   ├── services/
│   │   │   ├── api-gateway-svc.yaml
│   │   │   └── frontend-svc.yaml
│   │   ├── ingress/
│   │   │   └── nginx-ingress.yaml
│   │   ├── hpa/
│   │   │   └── autoscaling.yaml
│   │   └── volumes/
│   │       └── pv-claims.yaml
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── terraform.tfvars.example
│   │   └── modules/
│   │       ├── vpc/
│   │       │   ├── main.tf
│   │       │   ├── variables.tf
│   │       │   └── outputs.tf
│   │       ├── eks/
│   │       │   ├── main.tf
│   │       │   ├── variables.tf
│   │       │   └── outputs.tf
│   │       ├── rds/
│   │       │   ├── main.tf
│   │       │   ├── variables.tf
│   │       │   └── outputs.tf
│   │       └── cache/
│   │           ├── main.tf
│   │           ├── variables.tf
│   │           └── outputs.tf
│   └── scripts/
│       ├── deploy.sh
│       ├── backup.sh
│       └── restore.sh
└── .github/
    └── workflows/
        ├── ci.yml
        ├── cd-staging.yml
        └── cd-prod.yml
```

Now, the actual file contents:

## 1. Root Files

### README.md
```markdown
# FutVision AI

FutVision AI, futbol maç analiz ve tahmin platformudur. ESPN, FotMob ve diğer veri kaynaklarından gelen verileri kullanarak yapay zeka destekli skor tahminleri yapar.

## Proje Yapısı

- `backend/go/` - Go mikroservisleri (API Gateway, Auth, Data Ingestion, Match, Prediction, Odds, Notification)
- `backend/python/` - Python servisleri (ML ve LLM hizmetleri)
- `frontend/web/` - React + TypeScript web uygulaması
- `frontend/mobile/` - React Native mobil uygulama
- `infrastructure/` - Docker, Kubernetes, Terraform konfigürasyonları

## Hızlı Başlangıç

### Gereksinimler

- Docker & Docker Compose
- Node.js 18+
- Go 1.21+
- Python 3.11+
- kubectl (K8s için)
- terraform (Infra için)

### Local Geliştirme

1. Repo'yu klonlayın:
```bash
git clone https://github.com/yourusername/futvision.git
cd futvision
```

2. Environment dosyasını kopyalayın:
```bash
cp .env.example .env
# .env dosyasını düzenleyin (API keys, DB credentials)
```

3. Tüm servisleri başlatın:
```bash
docker-compose up -d
```

4. Frontend'i başlatın:
```bash
cd frontend/web
npm install
npm run dev
```

5. Mobil uygulamayı başlatın:
```bash
cd frontend/mobile
npm install
npx expo start
```

### API Dokümantasyonu

API Gateway'den Swagger UI: http://localhost:8080/docs

## Test

```bash
# Backend testleri
cd backend/go
go test ./...

# Python testleri
cd backend/python/ml-service
pytest

# Frontend testleri
cd frontend/web
npm test
```

## Deployment

Terraform ile AWS'de deployment:

```bash
cd infrastructure/terraform
terraform init
terraform apply
```

Detaylı bilgi için [Wiki](https://github.com/yourusername/futvision/wiki) sayfasına bakın.

## Lisans

MIT
```

### .env.example
```bash
# Genel
APP_ENV=development
LOG_LEVEL=debug
TIMEZONE=Europe/Istanbul

# Veritabanı
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=futvision
POSTGRES_USER=futvision
POSTGRES_PASSWORD=changeme

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# API Keys
API_FOOTBALL_KEY=your_api_football_key
FOTMOB_API_KEY=your_fotmob_key
ODDS_API_KEY=your_odds_api_key

# LLM
LLM_PROVIDER=anthropic  # veya openai
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
LLM_MODEL=claude-3-sonnet-20240229
MAX_TOKENS=4096

# Auth
JWT_SECRET=your_super_secret_jwt_key_change_this
JWT_EXPIRY=15m
REFRESH_TOKEN_EXPIRY=7d

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Frontend URL
FRONTEND_URL=http://localhost:3000
MOBILE_DEEP_LINK=futvision://

# AWS (production)
AWS_REGION=eu-central-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

### docker-compose.yml (root)
```yaml
version: '3.8'

services:
  # Databases
  postgres:
    image: postgres:15-alpine
    container_name: futvision-postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-futvision}
      POSTGRES_USER: ${POSTGRES_USER:-futvision}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/go/internal/database/migrations:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-futvision}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: futvision-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  # Go Backend Services
  api-gateway:
    build:
      context: ./backend/go
      dockerfile: cmd/api-gateway/Dockerfile
    container_name: futvision-api-gateway
    environment:
      - APP_ENV=${APP_ENV:-development}
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - JWT_SECRET=${JWT_SECRET}
    ports:
      - "8080:8080"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - futvision-network

  auth-service:
    build:
      context: ./backend/go
      dockerfile: cmd/auth-service/Dockerfile
    container_name: futvision-auth-service
    environment:
      - APP_ENV=${APP_ENV:-development}
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - futvision-network

  data-ingestion:
    build:
      context: ./backend/go
      dockerfile: cmd/data-ingestion/Dockerfile
    container_name: futvision-data-ingestion
    environment:
      - APP_ENV=${APP_ENV:-development}
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - API_FOOTBALL_KEY=${API_FOOTBALL_KEY}
      - FOTMOB_API_KEY=${FOTMOB_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - futvision-network

  match-service:
    build:
      context: ./backend/go
      dockerfile: cmd/match-service/Dockerfile
    container_name: futvision-match-service
    environment:
      - APP_ENV=${APP_ENV:-development}
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - futvision-network

  prediction-orchestrator:
    build:
      context: ./backend/go
      dockerfile: cmd/prediction-orchestrator/Dockerfile
    container_name: futvision-prediction-orchestrator
    environment:
      - APP_ENV=${APP_ENV:-development}
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - ML_SERVICE_URL=http://ml-service:8000
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      ml-service:
        condition: service_started
    networks:
      - futvision-network

  odds-service:
    build:
      context: ./backend/go
      dockerfile: cmd/odds-service/Dockerfile
    container_name: futvision-odds-service
    environment:
      - APP_ENV=${APP_ENV:-development}
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - ODDS_API_KEY=${ODDS_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - futvision-network

  notification-service:
    build:
      context: ./backend/go
      dockerfile: cmd/notification-service/Dockerfile
    container_name: futvision-notification-service
    environment:
      - APP_ENV=${APP_ENV:-development}
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - futvision-network

  # Python Services
  ml-service:
    build:
      context: ./backend/python/ml-service
      dockerfile: Dockerfile
    container_name: futvision-ml-service
    environment:
      - APP_ENV=${APP_ENV:-development}
      - POSTGRES_HOST=postgres
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - futvision-network

  llm-service:
    build:
      context: ./backend/python/llm-service
      dockerfile: Dockerfile
    container_name: futvision-llm-service
    environment:
      - APP_ENV=${APP_ENV:-development}
      - LLM_PROVIDER=${LLM_PROVIDER:-anthropic}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MAX_TOKENS=${MAX_TOKENS:-4096}
    ports:
      - "8001:8001"
    depends_on: []
    networks:
      - futvision-network

  # Frontend
  web:
    build:
      context: ./frontend/web
      dockerfile: Dockerfile
    container_name: futvision-web
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8080
    depends_on:
      - api-gateway
    networks:
      - futvision-network

volumes:
  postgres_data:
  redis_data:

networks:
  futvision-network:
    driver: bridge
```

### Makefile
```makefile
.PHONY: help build up down logs test clean

help:
	@echo "FutVision AI - Available commands:"
	@echo "  make build        - Build all Docker images"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - Show logs from all services"
	@echo "  make test         - Run all tests"
	@echo "  make clean        - Remove all containers and volumes"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	@echo "Running Go tests..."
	cd backend/go && go test ./...
	@echo "Running Python tests..."
	cd backend/python/ml-service && pytest
	@echo "Running frontend tests..."
	cd frontend/web && npm test -- --watchAll=false

clean:
	docker-compose down -v
	rm -rf backend/go/vendor
	rm -rf frontend/web/node_modules
	rm -rf frontend/mobile/node_modules
```

## 2. Backend Go Files

### backend/go/go.mod
```go
module github.com/futvision/go

go 1.21

require (
	github.com/gin-gonic/gin v1.9.1
	github.com/golang-jwt/jwt/v5 v5.0.0
	github.com/redis/go-redis/v9 v9.1.0
	github.com/lib/pq v1.10.7
	github.com/spf13/viper v1.13.0
	go.uber.org/zap v1.24.0
	golang.org/x/time v0.3.0
)

require (
	github.com/bytedance/sonic v1.9.1 // indirect
	github.com/cespare/xxhash/v2 v2.2.0 // indirect
	github.com/chenquan/go-orm v0.0.0-20230803132522-2d66b7d8b5f0 // indirect
	github.com/dgryski/go-rendezvous v0.0.0-20200823014737-9f7001d12a5f // indirect
	github.com/fsnotify/fsnotify v1.6.1 // indirect
	github.com/gabriel-vasile/mimetype v1.4.2 // indirect
	github.com/gin-contrib/sse v0.1.0 // indirect
	github.com/go-playground/locales v0.14.1 // indirect
	github.com/go-playground/universal-translator v0.18.1 // indirect
	github.com/go-playground/validator/v10 v10.14.0 // indirect
	github.com/goccy/go-json v0.10.2 // indirect
	github.com/jinzhu/inflection v1.0.0 // indirect
	github.com/jinzhu/now v1.1.5 // indirect
	github.com/klauspost/cpuid/v2 v2.0.9 // indirect
	github.com/leodido/go-urn v1.2.4 // indirect
	github.com/mattn/go-isatty v0.0.19 // indirect
	github.com/microsoft/go-sqlserver v0.12.3 // indirect
	github.com/modern-go/concurrent v0.0.0-20180306012644-bacd9c7ef1dd // indirect
	github.com/modern-go/reflect2 v1.0.2 // indirect
	github.com/pelletier/go-toml/v2 v2.0.8 // indirect
	github.com/twitchyliquid64/golang-asm v0.15.1 // indirect
	github.com/ugorji/go/codec v1.2.11 // indirect
	github.com/xrash/smetrics v0.0.0-20211216144743-858c3e2de7a4 // indirect
	go.uber.org/multierr v1.11.0 // indirect
	golang.org/x/arch v0.0.0-20210923205945-b38a25b6d060 // indirect
	golang.org/x/crypto v0.12.0 // indirect
	golang.org/x/net v0.14.0 // indirect
	golang.org/x/sys v0.11.0 // indirect
	golang.org/x/text v0.12.0 // indirect
	google.golang.org/protobuf v1.28.1 // indirect
	gopkg.in/check.v1 v1.0.0-20201130134442-10cb98267c6c // indirect
	gopkg.in/errgo.v2 v2.1.0 // indirect
	gopkg.in/yaml.v3 v3.0.1 // indirect
)
```

### backend/go/cmd/api-gateway/main.go
```go
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	"github.com/futvision/go/internal/config"
	"github.com/futvision/go/internal/http/middleware"
	"github.com/futvision/go/internal/http/responses"
)

func main() {
	// Load config
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// Initialize logger
	logger, err := zap.NewProduction()
	if err != nil {
		log.Fatalf("Failed to create logger: %v", err)
	}
	defer logger.Sync()
	undo := zap.RedirectStdLog(logger)
	defer undo()

	// Set Gin mode
	if cfg.AppEnv == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	// Create router
	router := gin.New()

	// Global middleware
	router.Use(gin.Recovery())
	router.Use(middleware.CORS())
	router.Use(middleware.Logging(logger))

	// Health check
	router.GET("/health", func(c *gin.Context) {
		responses.Success(c, gin.H{
			"status": "ok",
			"time":  time.Now().UTC().Format(time.RFC3339),
		})
	})

	// API routes v1
	v1 := router.Group("/api/v1")
	{
		// Public routes
		v1.GET("/matches", func(c *gin.Context) {
			responses.Success(c, gin.H{"message": "Matches endpoint"})
		})
		v1.GET("/predictions/:matchId", func(c *gin.Context) {
			responses.Success(c, gin.H{"message": "Prediction endpoint"})
		})

		// Auth routes
		auth := v1.Group("/auth")
		{
			auth.POST("/login", func(c *gin.Context) {
				responses.Success(c, gin.H{"message": "Login endpoint"})
			})
			auth.POST("/register", func(c *gin.Context) {
				responses.Success(c, gin.H{"message": "Register endpoint"})
			})
		}

		// Protected routes (example)
		protected := v1.Group("/")
		protected.Use(middleware.Auth(cfg.JWTSecret))
		{
			protected.GET("/user/profile", func(c *gin.Context) {
				userID, _ := c.Get("user_id")
				responses.Success(c, gin.H{"user_id": userID})
			})
		}
	}

	// Start server
	addr := fmt.Sprintf(":%d", cfg.APIPort)
	srv := &http.Server{
		Addr:    addr,
		Handler: router,
	}

	go func() {
		logger.Info("Starting API Gateway", zap.String("addr", addr))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("Failed to start server", zap.Error(err))
		}
	}()

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	logger.Info("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		logger.Fatal("Server forced to shutdown", zap.Error(err))
	}

	logger.Info("Server exiting")
}
```

### backend/go/internal/config/config.go
```go
package config

import (
	"log"
	"time"

	"github.com/spf13/viper"
)

type Config struct {
	AppEnv      string        `mapstructure:"APP_ENV"`
	LogLevel    string        `mapstructure:"LOG_LEVEL"`
	TimeZone    string        `mapstructure:"TIMEZONE"`
	APIPort     int           `mapstructure:"API_PORT"`
	Database    DatabaseConfig
	Redis       RedisConfig
	JWTSecret   string        `mapstructure:"JWT_SECRET"`
	JWTExpiry   time.Duration `mapstructure:"JWT_EXPIRY"`
	RefreshExpiry time.Duration `mapstructure:"REFRESH_TOKEN_EXPIRY"`
	APIKeys     APIKeysConfig
	LLM         LLMConfig
	FrontendURL string        `mapstructure:"FRONTEND_URL"`
}

type DatabaseConfig struct {
	Host     string `mapstructure:"POSTGRES_HOST"`
	Port     int    `mapstructure:"POSTGRES_PORT"`
	DBName   string `mapstructure:"POSTGRES_DB"`
	User     string `mapstructure:"POSTGRES_USER"`
	Password string `mapstructure:"POSTGRES_PASSWORD"`
	SSLMode  string `mapstructure:"POSTGRES_SSLMODE"`
}

type RedisConfig struct {
	Host     string `mapstructure:"REDIS_HOST"`
	Port     int    `mapstructure:"REDIS_PORT"`
	Password string `mapstructure:"REDIS_PASSWORD"`
	DB       int    `mapstructure:"REDIS_DB"`
}

type APIKeysConfig struct {
	APIFootball string `mapstructure:"API_FOOTBALL_KEY"`
	FotMob      string `mapstructure:"FOTMOB_API_KEY"`
	OddsAPI     string `mapstructure:"ODDS_API_KEY"`
}

type LLMConfig struct {
	Provider string `mapstructure:"LLM_PROVIDER"`
	AnthropicKey string `mapstructure:"ANTHROPIC_API_KEY"`
	OpenAIKey    string `mapstructure:"OPENAI_API_KEY"`
	Model        string `mapstructure:"LLM_MODEL"`
	MaxTokens    int    `mapstructure:"MAX_TOKENS"`
}

func Load() (*Config, error) {
	viper.SetConfigName("config")
	viper.SetConfigType("env")
	viper.AddConfigPath(".")
	viper.AutomaticEnv()

	// Set defaults
	viper.SetDefault("APP_ENV", "development")
	viper.SetDefault("LOG_LEVEL", "debug")
	viper.SetDefault("TIMEZONE", "Europe/Istanbul")
	viper.SetDefault("API_PORT", 8080)
	viper.SetDefault("POSTGRES_PORT", 5432)
	viper.SetDefault("POSTGRES_SSLMODE", "disable")
	viper.SetDefault("REDIS_PORT", 6379)
	viper.SetDefault("REDIS_DB", 0)
	viper.SetDefault("JWT_EXPIRY", "15m")
	viper.SetDefault("REFRESH_TOKEN_EXPIRY", "168h") // 7 days
	viper.SetDefault("LLM_PROVIDER", "anthropic")
	viper.SetDefault("MAX_TOKENS", 4096)

	if err := viper.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			return nil, err
		}
		// Config file not found; use env vars only
	}

	var cfg Config
	if err := viper.Unmarshal(&cfg); err != nil {
		return nil, err
	}

	// Parse durations
	var err error
	cfg.JWTExpiry, err = time.ParseDuration(cfg.JWTExpiry.String())
	if err != nil {
		return nil, err
	}
	cfg.RefreshExpiry, err = time.ParseDuration(cfg.RefreshExpiry.String())
	if err != nil {
		return nil, err
	}

	log.Printf("Loaded config for environment: %s", cfg.AppEnv)
	return &cfg, nil
}
```

### backend/go/internal/database/db.go
```go
package database

import (
	"context"
	"fmt"
	"time"

	"github.com/futvision/go/internal/config"
	"github.com/futvision/go/internal/utils/logger"
	"go.uber.org/zap"

	_ "github.com/lib/pq"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

type DB struct {
	*gorm.DB
}

func Connect(cfg config.DatabaseConfig) (*DB, error) {
	dsn := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=%s",
		cfg.Host, cfg.Port, cfg.User, cfg.Password, cfg.DBName, cfg.SSLMode)

	// Custom logger for GORM
	gormLogger := logger.Default
	if cfg.Host == "localhost" {
		gormLogger = logger.Default.LogMode(logger.Info)
	}

	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{
		Logger: gormLogger,
		NowFunc: func() time.Time {
			return time.Now().UTC()
		},
	})
	if err != nil {
		return nil, fmt.Errorf("failed to connect to database: %w", err)
	}

	// Connection pool settings
	sqlDB, err := db.DB()
	if err != nil {
		return nil, err
	}
	sqlDB.SetMaxIdleConns(10)
	sqlDB.SetMaxOpenConns(100)
	sqlDB.SetConnMaxLifetime(time.Hour)

	logger.Info("Database connection established",
		zap.String("host", cfg.Host),
		zap.String("db", cfg.DBName),
	)

	return &DB{db}, nil
}

func (db *DB) AutoMigrate(models ...interface{}) error {
	return db.DB.AutoMigrate(models...)
}

func (db *DB) WithContext(ctx context.Context) *gorm.DB {
	return db.DB.WithContext(ctx)
}

func (db *DB) Close() error {
	sqlDB, err := db.DB.DB()
	if err != nil {
		return err
	}
	return sqlDB.Close()
}
```

### backend/go/internal/database/models.go
```go
package database

import (
	"time"

	"github.com/google/uuid"
	"gorm.io/gorm"
)

type User struct {
	ID            uuid.UUID  `gorm:"type:uuid;primary_key;default:gen_random_uuid()"`
	Email         string     `gorm:"uniqueIndex;not null"`
	Username      string     `gorm:"uniqueIndex;not null"`
	PasswordHash  string     `gorm:"not null"`
	IsVerified    bool       `gorm:"default:false"`
	PreferredLang string     `gorm:"default:tr"`
	CreatedAt     time.Time
	UpdatedAt     time.Time
	DeletedAt     gorm.DeletedAt `gorm:"index"`
}

type Team struct {
	TeamID      string    `gorm:"primaryKey;not null"`
	Name        string    `gorm:"not null"`
	ShortName   string    `gorm:"not null"`
	LogoURL     string
	League      string    `gorm:"not null"`
	Country     string    `gorm:"not null"`
	EloRating   float64   `gorm:"default:1500"`
	CreatedAt   time.Time
	UpdatedAt   time.Time
}

type Match struct {
	MatchID     uuid.UUID `gorm:"type:uuid;primary_key;default:gen_random_uuid()"`
	HomeTeamID  string    `gorm:"not null"`
	AwayTeamID  string    `gorm:"not null"`
	KickoffTime time.Time `gorm:"not null"`
	Status      string    `gorm:"default:scheduled"` // scheduled, live, finished, cancelled
	Stadium     string
	Weather     string
	RefereeID   string
	League      string    `gorm:"not null"`
	Round       string
	Season      string    `gorm:"not null"`
	CreatedAt   time.Time
	UpdatedAt   time.Time

	// Relations
	HomeTeam Team `gorm:"foreignKey:HomeTeamID;references:TeamID"`
	AwayTeam Team `gorm:"foreignKey:AwayTeamID;references:TeamID"`
}

type Injury struct {
	InjuryID   uuid.UUID `gorm:"type:uuid;primary_key;default:gen_random_uuid()"`
	MatchID    uuid.UUID `gorm:"not null"`
	PlayerID   string    `gorm:"not null"`
	PlayerName string    `gorm:"not null"`
	TeamID     string    `gorm:"not null"`
	Status     string    `gorm:"not null"` // injured, suspended, available
	Type       string    // e.g., "muscle", "card_suspension"
	Severity   string    // low, medium, high, critical
	ImpactScore float64   `gorm:"default:0"` // 0-1 score
	CreatedAt  time.Time
	UpdatedAt  time.Time

	Match Match `gorm:"foreignKey:MatchID"`
}

type PlayerStat struct {
	PlayerID   string    `gorm:"primaryKey;not null"`
	TeamID     string    `gorm:"not null"`
	Season     string    `gorm:"primaryKey;not null"`
	Appearances int      `gorm:"default:0"`
	Goals      int       `gorm:"default:0"`
	Assists    int       `gorm:"default:0"`
	XG         float64   `gorm:"default:0"`
	PassCompletion float64 `gorm:"default:0"`
	CreatedAt  time.Time
	UpdatedAt  time.Time
}

type BettingOdd struct {
	OddID       uuid.UUID `gorm:"type:uuid;primary_key;default:gen_random_uuid()"`
	MatchID     uuid.UUID `gorm:"not null"`
	Provider    string    `gorm:"not null"`
	Odds1X2     JSONB     `gorm:"type:jsonb"` // { "1": 2.1, "X": 3.4, "2": 3.2 }
	OddsOverUnder25 JSONB `gorm:"type:jsonb"` // { "over": 1.9, "under": 1.9 }
	LastUpdated time.Time `gorm:"not null"`
	CreatedAt   time.Time

	Match Match `gorm:"foreignKey:MatchID"`
}

type Prediction struct {
	PredictionID uuid.UUID `gorm:"type:uuid;primary_key;default:gen_random_uuid()"`
	MatchID      uuid.UUID `gorm:"not null;uniqueIndex"` // one prediction per match
	UserID       *uuid.UUID `gorm:"index"`
	HomeWinProb  float64   `gorm:"not null"` // 0-1
	DrawProb     float64   `gorm:"not null"`
	AwayWinProb  float64   `gorm:"not null"`
	ScoreDist    JSONB     `gorm:"type:jsonb"` // map of "1-0":0.28, "2-1":0.12, etc.
	Over25Prob   float64   `gorm:"not null"`
	BothTeamsToScoreProb float64 `gorm:"not null"`
	Confidence   float64   `gorm:"not null"` // 0-100
	Explanation  string    `gorm:"type:text"`
	ModelAgreement float64 `gorm:"not null"` // 0-1
	FormScore    float64   `gorm:"not null"` // 0-1
	CreatedAt    time.Time
	UpdatedAt    time.Time

	Match Match `gorm:"foreignKey:MatchID"`
	User  User  `gorm:"foreignKey:UserID"`
}

// JSONB is a custom type for PostgreSQL JSONB
type JSONB map[string]interface{}

func (j JSONB) GormDataType() string {
	return "jsonb"
}

func (j JSONB) GormValue(ctx context.Context, db *gorm.DB) clause.Expr {
	return clause.Expr{
		SQL:  "?::jsonb",
		Vars: []interface{}{j},
	}
}
```

### backend/go/internal/database/migrations/001_initial.up.sql
```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    preferred_lang VARCHAR(10) DEFAULT 'tr',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Teams table
CREATE TABLE teams (
    team_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(50) NOT NULL,
    logo_url TEXT,
    league VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,
    elo_rating DECIMAL(8,2) DEFAULT 1500,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Matches table
CREATE TABLE matches (
    match_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_team_id VARCHAR(50) NOT NULL REFERENCES teams(team_id),
    away_team_id VARCHAR(50) NOT NULL REFERENCES teams(team_id),
    kickoff_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'scheduled',
    stadium VARCHAR(200),
    weather VARCHAR(100),
    referee_id VARCHAR(100),
    league VARCHAR(100) NOT NULL,
    round VARCHAR(50),
    season VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_status CHECK (status IN ('scheduled', 'live', 'finished', 'cancelled'))
);

-- Injuries table
CREATE TABLE injuries (
    injury_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES matches(match_id),
    player_id VARCHAR(100) NOT NULL,
    player_name VARCHAR(200) NOT NULL,
    team_id VARCHAR(50) NOT NULL REFERENCES teams(team_id),
    status VARCHAR(20) NOT NULL,
    type VARCHAR(100),
    severity VARCHAR(20),
    impact_score DECIMAL(3,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_injury_status CHECK (status IN ('injured', 'suspended', 'available'))
);

-- Player stats table
CREATE TABLE player_stats (
    player_id VARCHAR(100) NOT NULL,
    team_id VARCHAR(50) NOT NULL REFERENCES teams(team_id),
    season VARCHAR(20) NOT NULL,
    appearances INTEGER DEFAULT 0,
    goals INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    xg DECIMAL(5,2) DEFAULT 0,
    pass_completion DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (player_id, season)
);

-- Betting odds table
CREATE TABLE betting_odds (
    odd_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES matches(match_id),
    provider VARCHAR(100) NOT NULL,
    odds_1x2 JSONB NOT NULL,
    odds_over_under_25 JSONB NOT NULL,
    last_updated TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_match_provider UNIQUE(match_id, provider)
);

-- Predictions table
CREATE TABLE predictions (
    prediction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL UNIQUE REFERENCES matches(match_id),
    user_id UUID REFERENCES users(id),
    home_win_prob DECIMAL(5,4) NOT NULL,
    draw_prob DECIMAL(5,4) NOT NULL,
    away_win_prob DECIMAL(5,4) NOT NULL,
    score_dist JSONB NOT NULL,
    over_25_prob DECIMAL(5,4) NOT NULL,
    both_teams_to_score_prob DECIMAL(5,4) NOT NULL,
    confidence DECIMAL(5,2) NOT NULL,
    explanation TEXT,
    model_agreement DECIMAL(5,4) NOT NULL,
    form_score DECIMAL(5,4) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User favorites table
CREATE TABLE user_favorite_teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_id VARCHAR(50) NOT NULL REFERENCES teams(team_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_user_team UNIQUE(user_id, team_id)
);

-- User devices for push notifications
CREATE TABLE user_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_token TEXT NOT NULL,
    platform VARCHAR(20) NOT NULL, -- 'ios', 'android', 'web'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_device_token UNIQUE(device_token)
);

-- Audit logs
CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    actor_id UUID REFERENCES users(id),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    details JSONB
);

-- Indexes for performance
CREATE INDEX idx_matches_kickoff ON matches(kickoff_time);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_league ON matches(league);
CREATE INDEX idx_injuries_match ON injuries(match_id);
CREATE INDEX idx_injuries_team ON injuries(team_id);
CREATE INDEX idx_predictions_match ON predictions(match_id);
CREATE INDEX idx_predictions_user ON predictions(user_id);
CREATE INDEX idx_betting_odds_match ON betting_odds(match_id);
CREATE INDEX idx_user_favorites_user ON user_favorite_teams(user_id);
CREATE INDEX idx_user_devices_user ON user_devices(user_id);

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_matches_updated_at BEFORE UPDATE ON matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_injuries_updated_at BEFORE UPDATE ON injuries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_player_stats_updated_at BEFORE UPDATE ON player_stats
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_predictions_updated_at BEFORE UPDATE ON predictions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### backend/go/internal/prediction/models.go
```go
package prediction

import (
	"github.com/google/uuid"
	"time"
)

type PredictionRequest struct {
	MatchID uuid.UUID `json:"match_id" binding:"required"`
	UserID  *uuid.UUID `json:"user_id"`
}

type PredictionResponse struct {
	MatchID         uuid.UUID  `json:"match_id"`
	HomeWinProb     float64    `json:"home_win_probability"` // 0-1
	DrawProb        float64    `json:"draw_probability"`
	AwayWinProb     float64    `json:"away_win_probability"`
	ScoreDist       map[string]float64 `json:"score_distribution"` // "1-0": 0.28
	Over25Prob      float64    `json:"over_25_probability"`
	BothTeamsScoreProb float64 `json:"both_teams_to_score_probability"`
	Confidence      float64    `json:"confidence"` // 0-100
	Explanation     string     `json:"explanation"`
	ModelAgreement  float64    `json:"model_agreement"` // 0-1
	FormScore       float64    `json:"form_score"` // 0-1
	CreatedAt       time.Time  `json:"created_at"`
}

type TeamStats struct {
	TeamID         string    `json:"team_id"`
	Name           string    `json:"name"`
	ELO            float64   `json:"elo_rating"`
	Form           []int     `json:"form"` // last 5 match points: 3=win, 1=draw, 0=loss
	GoalsScored    int       `json:"goals_scored_last_5"`
	GoalsConceded  int       `json:"goals_conceded_last_5"`
	HomeAdvantage  float64   `json:"home_advantage"` // 1.0-1.5 multiplier
	InjuryImpact   float64   `json:"injury_impact"` // 0-1, 0=no impact, 1=full squad out
}

type MatchInput struct {
	MatchID        uuid.UUID `json:"match_id"`
	HomeTeam       TeamStats `json:"home_team"`
	AwayTeam       TeamStats `json:"away_team"`
	League         string    `json:"league"`
	KickoffTime    time.Time `json:"kickoff_time"`
	Weather        string    `json:"weather,omitempty"`
}

type PoissonResult struct {
	HomeGoalsLambda float64 `json:"home_goals_lambda"`
	AwayGoalsLambda float64 `json:"away_goals_lambda"`
	Probabilities   map[string]float64 `json:"probabilities"` // score probabilities
}

type ELOComparison struct {
	HomeELO     float64 `json:"home_elo"`
	AwayELO     float64 `json:"away_elo"`
	ExpectedWin float64 `json:"expected_home_win"` // 0-1
}

type EnsembleResult struct {
	HomeWinProb  float64 `json:"home_win_prob"`
	DrawProb     float64 `json:"draw_prob"`
	AwayWinProb  float64 `json:"away_win_prob"`
	Over25Prob   float64 `json:"over_25_prob"`
	BothTeamsProb float64 `json:"both_teams_prob"`
	Confidence   float64 `json:"confidence"`
}
```

### backend/go/internal/prediction/poisson.go
```go
package prediction

import (
	"math"
)

// Poisson probability mass function: P(k; λ) = (λ^k * e^-λ) / k!
func poissonPMF(k int, lambda float64) float64 {
	if lambda < 0 {
		lambda = 0
	}
	return (math.Pow(lambda, float64(k)) * math.Exp(-lambda)) / factorial(float64(k))
}

func factorial(n float64) float64 {
	if n <= 1 {
		return 1
	}
	result := 1.0
	for i := 2.0; i <= n; i++ {
		result *= i
	}
	return result
}

// CalculatePoissonProbabilities computes score probabilities for a match
func CalculatePoissonProbabilities(homeLambda, awayLambda float64) map[string]float64 {
	probs := make(map[string]float64)
	total := 0.0

	// Calculate for 0-5 goals per team (typically enough)
	for h := 0; h <= 5; h++ {
		for a := 0; a <= 5; a++ {
			prob := poissonPMF(h, homeLambda) * poissonPMF(a, awayLambda)
			key := fmt.Sprintf("%d-%d", h, a)
			probs[key] = prob
			total += prob
		}
	}

	// Normalize to ensure sum = 1
	for k := range probs {
		probs[k] /= total
	}

	// Also aggregate common results
	probs["home_win"] = 0.0
	probs["draw"] = 0.0
	probs["away_win"] = 0.0
	probs["over_2_5"] = 0.0
	probs["both_teams_score"] = 0.0

	for h := 0; h <= 5; h++ {
		for a := 0; a <= 5; a++ {
			prob := probs[fmt.Sprintf("%d-%d", h, a)]
			if h > a {
				probs["home_win"] += prob
			} else if h == a {
				probs["draw"] += prob
			} else {
				probs["away_win"] += prob
			}
			if h+a > 2 {
				probs["over_2_5"] += prob
			}
			if h > 0 && a > 0 {
				probs["both_teams_score"] += prob
			}
		}
	}

	return probs
}
```

### backend/go/cmd/prediction-orchestrator/main.go
```go
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	"github.com/futvision/go/internal/config"
	"github.com/futvision/go/internal/database"
	"github.com/futvision/go/internal/prediction"
	"github.com/futvision/go/internal/redis"
	"github.com/futvision/go/internal/utils/logger"
)

func main() {
	// Load config
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// Initialize logger
	logger, err := zap.NewProduction()
	if err != nil {
		log.Fatalf("Failed to create logger: %v", err)
	}
	defer logger.Sync()
	undo := zap.RedirectStdLog(logger)
	defer undo()

	// Connect to DB
	db, err := database.Connect(cfg.Database)
	if err != nil {
		logger.Fatal("Failed to connect to database", zap.Error(err))
	}
	defer db.Close()

	// Auto-migrate (in production, use proper migrations)
	if err := db.AutoMigrate(
		&database.Match{},
		&database.Injury{},
		&database.Prediction{},
	); err != nil {
		logger.Fatal("Auto-migration failed", zap.Error(err))
	}

	// Connect to Redis
	redisClient, err := redis.Connect(cfg.Redis)
	if err != nil {
		logger.Fatal("Failed to connect to Redis", zap.Error(err))
	}
	defer redisClient.Close()

	// Initialize prediction service
	predSvc := prediction.NewService(db, redisClient, logger)

	// Setup HTTP server
	router := gin.New()
	router.Use(gin.Recovery())
	router.Use(middleware.CORS())
	router.Use(middleware.Logging(logger))

	// Routes
	router.GET("/health", func(c *gin.Context) {
		logger.Info("Health check")
		c.JSON(200, gin.H{"status": "ok"})
	})

	router.POST("/predict", func(c *gin.Context) {
		var req prediction.PredictionRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			logger.Warn("Invalid request", zap.Error(err))
			c.JSON(400, gin.H{"error": err.Error()})
			return
		}

		// Check cache first
		cacheKey := fmt.Sprintf("prediction:%s", req.MatchID.String())
		if cached, err := redisClient.Get(c, cacheKey).Bytes(); err == nil {
			var resp prediction.PredictionResponse
			if err := json.Unmarshal(cached, &resp); err == nil {
				logger.Info("Cache hit", zap.String("match_id", req.MatchID.String()))
				c.JSON(200, resp)
				return
			}
		}

		// Generate prediction
		ctx, cancel := context.WithTimeout(c.Request.Context(), 30*time.Second)
		defer cancel()

		resp, err := predSvc.GeneratePrediction(ctx, req)
		if err != nil {
			logger.Error("Prediction failed", zap.Error(err), zap.String("match_id", req.MatchID.String()))
			c.JSON(500, gin.H{"error": "Failed to generate prediction"})
			return
		}

		// Cache for 1 hour (predictions don't change often)
		data, _ := json.Marshal(resp)
		redisClient.SetEx(c, cacheKey, data, 3600)

		c.JSON(200, resp)
	})

	// Start server
	addr := fmt.Sprintf(":%d", cfg.APIPort)
	srv := &http.Server{
		Addr:    addr,
		Handler: router,
	}

	go func() {
		logger.Info("Starting Prediction Orchestrator", zap.String("addr", addr))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("Failed to start server", zap.Error(err))
		}
	}()

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	logger.Info("Shutting down...")

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		logger.Fatal("Server forced to shutdown", zap.Error(err))
	}

	logger.Info("Server exited")
}
```

### backend/go/internal/prediction/orchestrator.go
```go
package prediction

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	"github.com/futvision/go/internal/database"
	"github.com/futvision/go/internal/redis"
	"go.uber.org/zap"

	"github.com/google/uuid"
)

type Service struct {
	db     *database.DB
	redis  *redis.Client
	logger *zap.Logger
	// Add ML and LLM clients later
}

func NewService(db *database.DB, redisClient *redis.Client, logger *zap.Logger) *Service {
	return &Service{
		db:     db,
		redis:  redisClient,
		logger: logger,
	}
}

func (s *Service) GeneratePrediction(ctx context.Context, req PredictionRequest) (*PredictionResponse, error) {
	start := time.Now()

	// 1. Fetch match data with teams
	match, err := s.getMatchWithTeams(ctx, req.MatchID)
	if err != nil {
		return nil, fmt.Errorf("failed to get match: %w", err)
	}

	// 2. Fetch injuries for both teams
	injuries, err := s.getInjuriesForMatch(ctx, req.MatchID)
	if err != nil {
		s.logger.Warn("Failed to get injuries", zap.Error(err))
		// Continue without injuries
	}

	// 3. Calculate team stats
	homeStats, err := s.calculateTeamStats(ctx, match.HomeTeamID, req.MatchID, injuries, true)
	if err != nil {
		return nil, fmt.Errorf("failed to calculate home stats: %w", err)
	}

	awayStats, err := s.calculateTeamStats(ctx, match.AwayTeamID, req.MatchID, injuries, false)
	if err != nil {
		return nil, fmt.Errorf("failed to calculate away stats: %w", err)
	}

	// 4. Run statistical models
	poissonResult := CalculatePoissonProbabilities(
		homeStats.GoalsScoredAvg+homeStats.HomeAdvantage,
		awayStats.GoalsScoredAvg+awayStats.HomeAdvantage,
	)

	eloComparison := calculateELOComparison(homeStats.ELO, awayStats.ELO)

	formScore := calculateFormScore(homeStats.Form, awayStats.Form)

	// 5. Ensemble the models (Phase 5: Final Tahmin)
	ensemble := s.ensembleModels(poissonResult, eloComparison, formScore, homeStats.InjuryImpact, awayStats.InjuryImpact)

	// 6. Generate explanation (simplified for MVP - will call LLM in Sprint 2)
	explanation := s.generateExplanation(match, homeStats, awayStats, ensemble, poissonResult, eloComparison)

	// 7. Build response
	resp := &PredictionResponse{
		MatchID:         req.MatchID,
		HomeWinProb:     ensemble.HomeWinProb,
		DrawProb:        ensemble.DrawProb,
		AwayWinProb:     ensemble.AwayWinProb,
		ScoreDist:       poissonResult,
		Over25Prob:      ensemble.Over25Prob,
		BothTeamsScoreProb: ensemble.BothTeamsProb,
		Confidence:      ensemble.Confidence,
		Explanation:     explanation,
		ModelAgreement:  ensemble.ModelAgreement,
		FormScore:       formScore,
		CreatedAt:       time.Now(),
	}

	// 8. Save prediction to DB
	if err := s.savePrediction(ctx, req, resp); err != nil {
		s.logger.Error("Failed to save prediction", zap.Error(err))
	}

	s.logger.Info("Prediction generated",
		zap.String("match_id", req.MatchID.String()),
		zap.Duration("duration", time.Since(start)),
		zap.Float64("confidence", resp.Confidence),
	)

	return resp, nil
}

func (s *Service) getMatchWithTeams(ctx context.Context, matchID uuid.UUID) (*database.Match, error) {
	var match database.Match
	if err := s.db.WithContext(ctx).
		Preload("HomeTeam").
		Preload("AwayTeam").
		First(&match, "match_id = ?", matchID).Error; err != nil {
		return nil, err
	}
	return &match, nil
}

func (s *Service) getInjuriesForMatch(ctx context.Context, matchID uuid.UUID) ([]database.Injury, error) {
	var injuries []database.Injury
	if err := s.db.WithContext(ctx).
		Where("match_id = ?", matchID).
		Find(&injuries).Error; err != nil {
		return nil, err
	}
	return injuries, nil
}

func (s *Service) calculateTeamStats(ctx context.Context, teamID string, matchID uuid.UUID, injuries []database.Injury, isHome bool) (*TeamStats, error) {
	// Simplified - in production, fetch from player_stats and calculate aggregates
	// For now, return mock data
	stats := &TeamStats{
		TeamID: teamID,
		ELO:    1500 + float64(len(teamID))*10, // dummy
		Form:   []int{3, 1, 0, 3, 1},           // dummy
		GoalsScoredAvg: 1.5,
		HomeAdvantage: 1.2,
		InjuryImpact: 0.0,
	}

	// Calculate injury impact
	for _, inj := range injuries {
		if inj.TeamID == teamID {
			stats.InjuryImpact += inj.ImpactScore
		}
	}
	if stats.InjuryImpact > 1.0 {
		stats.InjuryImpact = 1.0
	}

	return stats, nil
}

func (s *Service) ensembleModels(poisson map[string]float64, elo ELOComparison, formScore float64, homeInjury, awayInjury float64) EnsembleResult {
	// Phase 5: Poisson×0.6 + ELO×0.4
	homeWinFromPoisson := poisson["home_win"]
	drawFromPoisson := poisson["draw"]
	awayWinFromPoisson := poisson["away_win"]

	// Adjust with ELO
	eloHomeAdv := (elo.ExpectedWin - 0.5) * 2 // normalize to -1 to 1
	homeWin := homeWinFromPoisson*0.6 + (0.5 + eloHomeAdv*0.4)*0.4
	draw := drawFromPoisson*0.6 + 0.25*0.4 // simplified
	awayWin := awayWinFromPoisson*0.6 + (0.5 - eloHomeAdv*0.4)*0.4

	// Normalize to sum 1
	total := homeWin + draw + awayWin
	homeWin /= total
	draw /= total
	awayWin /= total

	// Confidence calculation
	modelAgreement := 1.0 - (abs(homeWinFromPoisson-elo.ExpectedWin) + abs(drawFromPoisson-0.25) + abs(awayWinFromPoisson-(1-elo.ExpectedWin-0.25)))/3
	confidence := modelAgreement*0.6 + formScore*0.2 + 0.2 // scaled to 0-1, then *100

	// Injury penalty
	injuryPenalty := (homeInjury + awayInjury) / 2
	confidence *= (1 - injuryPenalty*0.5)

	if confidence < 0.1 {
		confidence = 0.1
	}
	if confidence > 0.95 {
		confidence = 0.95
	}

	return EnsembleResult{
		HomeWinProb:  homeWin,
		DrawProb:     draw,
		AwayWinProb:  awayWin,
		Over25Prob:   poisson["over_2_5"],
		BothTeamsProb: poisson["both_teams_score"],
		Confidence:   confidence * 100,
		ModelAgreement: modelAgreement,
	}
}

func (s *Service) generateExplanation(match *database.Match, home, away *TeamStats, ensemble EnsembleResult, poisson map[string]float64, elo ELOComparison) string {
	// Simple template-based explanation for MVP
	// In Sprint 2, this will be replaced by LLM
	explanation := fmt.Sprintf(
		"Model analizi: %s ev sahibi avantajlı. ELO farkı: %.0f, form skoru: %.2f. "+
			"İstatistiksel model %s galibiyet olasılığı %.1f%% hesapladı. "+
			"Güven skoru: %.1f%%.",
		match.HomeTeam.Name,
		home.ELO-away.ELO,
		calculateFormScore(home.Form, away.Form),
		match.HomeTeam.Name,
		ensemble.HomeWinProb*100,
		ensemble.Confidence,
	)
	return explanation
}

func (s *Service) savePrediction(ctx context.Context, req PredictionRequest, resp *PredictionResponse) error {
	pred := &database.Prediction{
		MatchID:      req.MatchID,
		UserID:       req.UserID,
		HomeWinProb:  resp.HomeWinProb,
		DrawProb:     resp.DrawProb,
		AwayWinProb:  resp.AwayWinProb,
		ScoreDist:    resp.ScoreDist,
		Over25Prob:   resp.Over25Prob,
		BothTeamsToScoreProb: resp.BothTeamsScoreProb,
		Confidence:   resp.Confidence,
		Explanation:  resp.Explanation,
		ModelAgreement: resp.ModelAgreement,
		FormScore:    resp.FormScore,
	}

	return s.db.WithContext(ctx).Create(pred).Error
}

func abs(x float64) float64 {
	if x < 0 {
		return -x
	}
	return x
}

func calculateFormScore(homeForm, awayForm []int) float64 {
	// Simple average of last 5 matches (3=win, 1=draw, 0=loss)
	homePoints := 0.0
	for _, p := range homeForm {
		homePoints += float64(p)
	}
	awayPoints := 0.0
	for _, p := range awayForm {
		awayPoints += float64(p)
	}
	homeAvg := homePoints / 5.0 / 3.0 // normalize to 0-1
	awayAvg := awayPoints / 5.0 / 3.0
	return (homeAvg - awayAvg + 1) / 2 // return difference normalized to 0-1
}

func calculateELOComparison(homeELO, awayELO float64) ELOComparison {
	expected := 1.0 / (1.0 + math.Pow(10, (awayELO-homeELO)/400.0))
	return ELOComparison{
		HomeELO:     homeELO,
		AwayELO:     awayELO,
		ExpectedWin: expected,
	}
}
```

### backend/go/internal/redis/client.go
```go
package redis

import (
	"context"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/futvision/go/internal/config"
	"go.uber.org/zap"
)

type Client struct {
	*redis.Client
	logger *zap.Logger
}

func Connect(cfg config.RedisConfig) (*Client, error) {
	addr := fmt.Sprintf("%s:%d", cfg.Host, cfg.Port)
	client := redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: cfg.Password,
		DB:       cfg.DB,
	})

	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect to redis: %w", err)
	}

	return &Client{Client: client}, nil
}

func (c *Client) Close() error {
	return c.Client.Close()
}
```

### backend/go