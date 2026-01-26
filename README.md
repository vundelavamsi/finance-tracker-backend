# Finance Tracker

A finance tracking application that extracts transaction data from payment screenshots and invoices using AI (Gemini API) and stores them via a Telegram Bot interface.

## Features

- 📸 **Low-friction input**: Share payment screenshots/invoices via Telegram Bot
- 🤖 **AI-powered parsing**: Uses Google Gemini API to extract transaction details
- 💾 **Multi-tenant database**: SaaS-ready architecture with PostgreSQL
- 🔌 **Pluggable parser**: Easy to switch from Gemini to local OCR in the future
- ✅ **Real-time confirmation**: Get instant feedback when transactions are tracked

## Architecture

- **Ingestion Layer**: Telegram Bot (handles auth and file upload for free)
- **Backend**: FastAPI with async capabilities
- **Brain**: Gemini 1.5 Flash API for invoice parsing
- **Database**: PostgreSQL with multi-tenant design
- **Parser**: Strategy pattern for easy switching between parsing methods

## Prerequisites

- Python 3.9+
- PostgreSQL database
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Google Gemini API Key (from [Google AI Studio](https://makersuite.google.com/app/apikey))
- ngrok (for local development webhook testing)

## Setup Instructions

### 1. Clone and Install Dependencies

```bash
# Navigate to project directory
cd "Finance Tracker V1"

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup PostgreSQL Database

#### Option A: Install PostgreSQL on macOS (Recommended for Development)

**Step 1: Install PostgreSQL**

Using Homebrew (recommended):
```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install PostgreSQL
brew install postgresql@15

# Start PostgreSQL service
brew services start postgresql@15
```

Or download from [PostgreSQL official website](https://www.postgresql.org/download/macosx/):
- Download the installer for macOS
- Run the installer and follow the setup wizard
- Note the password you set for the `postgres` user during installation

**Step 2: Verify Installation**

```bash
# Check if PostgreSQL is running
brew services list | grep postgresql

# Or check the version
psql --version
```

**Step 3: Access PostgreSQL**

```bash
# Connect to PostgreSQL as the default user
psql postgres

# You should see a prompt like: postgres=#
```

**Step 4: Create Database and User**

Once connected to PostgreSQL, run these SQL commands:

```sql
-- Create a new user (optional, you can use 'postgres' user for development)
CREATE USER finance_user WITH PASSWORD 'your_password_here';

-- Create the database
CREATE DATABASE finance_tracker;

-- Grant privileges to the user
GRANT ALL PRIVILEGES ON DATABASE finance_tracker TO finance_user;

-- Exit psql
\q
```

**Step 5: Test the Connection**

```bash
# Test connection with the new user
psql -U finance_user -d finance_tracker

# Or if using default postgres user
psql -U postgres -d finance_tracker
```

**Step 6: Update .env File**

Update your `.env` file with the database connection string:

```env
# If using custom user
DATABASE_URL=postgresql://finance_user:your_password_here@localhost:5432/finance_tracker

# Or if using default postgres user
DATABASE_URL=postgresql://postgres:your_postgres_password@localhost:5432/finance_tracker
```

**Troubleshooting:**

If you get "command not found: psql":
```bash
# Add PostgreSQL to your PATH (add to ~/.zshrc or ~/.bash_profile)
echo 'export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

If PostgreSQL won't start:
```bash
# Check if it's already running
pg_isready

# Restart the service
brew services restart postgresql@15

# Check logs
tail -f /opt/homebrew/var/log/postgresql@15.log
```

#### Option B: Using Docker (Alternative Method)

If you prefer using Docker:

**Step 1: Install Docker Desktop**

Download from [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)

**Step 2: Run PostgreSQL Container**

```bash
docker run --name finance-tracker-db \
  -e POSTGRES_USER=finance_service_user \
  -e POSTGRES_PASSWORD=your_password_here \
  -e POSTGRES_DB=finance_tracker \
  -p 5432:5432 \
  -d postgres:15
```

**Step 3: Verify Container is Running**

```bash
# Check running containers
docker ps

# Check logs
docker logs finance-tracker-db
```

**Step 4: Connect to Database**

```bash
# Connect using psql (if installed) or Docker
docker exec -it finance-tracker-db psql -U finance_service_user -d finance_tracker

# Or from your local machine (if psql is installed)
psql -h localhost -U finance_service_user -d finance_tracker
```

**Step 5: Update .env File**

```env
DATABASE_URL=postgresql://finance_service_user:your_password_here@localhost:5432/finance_tracker
```

**Useful Docker Commands:**

```bash
# Stop the container
docker stop finance-tracker-db

# Start the container
docker start finance-tracker-db

# Remove the container (data will be lost)
docker rm -f finance-tracker-db

# Access PostgreSQL shell
docker exec -it finance-tracker-db psql -U finance_service_user -d finance_tracker
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/finance_tracker
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
PARSER_TYPE=GEMINI
```

### 4. Create Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Copy the bot token and add it to `.env` as `TELEGRAM_BOT_TOKEN`

### 5. Get Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key and add it to `.env` as `GEMINI_API_KEY`

### 6. Setup Webhook for Local Development

Telegram requires HTTPS for webhooks. Use ngrok for local development:

```bash
# Install ngrok (if not installed)
# macOS: brew install ngrok
# Or download from https://ngrok.com/

# Start your FastAPI server
uvicorn app.main:app --reload

# In another terminal, start ngrok
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

#### ngrok setup complete
ngrok is installed. Next steps:
1. Get your authtoken
    - Sign up at https://dashboard.ngrok.com/signup (free)
    - Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken
2. Authenticate ngrok

      ```bash
      ngrok config add-authtoken YOUR_AUTHTOKEN_HERE
      ```
3. Use ngrok
    
    Once authenticated, you can use ngrok to expose your FastAPI server:

    ```bash
    # Start your FastAPI server first (in one terminal)
    uvicorn app.main:app --reload
    
    # Then start ngrok (in another terminal)
    ngrok http 8000
    ```
  ngrok will give you a public HTTPS URL (like https://abc123.ngrok-free.app) that you can use as your Telegram webhook URL.
  
  Quick test
   - After authentication, test it:
    
    ngrok http 8000

### 7. Configure Telegram Webhook

Set your webhook URL using Telegram Bot API:

```bash
# Replace YOUR_BOT_TOKEN and YOUR_NGROK_URL
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook" \
  -d "url=https://YOUR_NGROK_URL/webhook/telegram"
```

Or use the Telegram web interface:
- Visit: `https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook?url=https://YOUR_NGROK_URL/webhook/telegram`

Verification
 
 ```bash
 curl "https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo"
 ```

### 8. Run the Application

```bash
# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use Python directly
python -m app.main
```

The API will be available at `http://localhost:8000`

## Usage

1. Find your bot on Telegram (search for the bot name you created)
2. Send a payment screenshot or invoice image to the bot
3. The bot will process the image and extract transaction details
4. You'll receive a confirmation message: "✅ Tracked ₹450 at Starbucks (Coffee)"

## API Endpoints

- `GET /` - Root endpoint (health check)
- `GET /health` - Health check endpoint
- `POST /webhook/telegram` - Telegram webhook endpoint (handles bot messages)

## Project Structure

```
finance-tracker/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration management
│   ├── database.py             # Database connection
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py
│   │   └── transaction.py
│   ├── services/               # Business logic
│   │   ├── parser_service.py   # Parser interface
│   │   ├── gemini_parser.py    # Gemini implementation
│   │   └── telegram_service.py # Telegram integration
│   ├── api/                    # API routes
│   │   └── webhooks.py
│   └── schemas/                 # Pydantic schemas
│       └── transaction.py
├── requirements.txt
├── .env.example
└── README.md
```

## Future Enhancements

- [ ] Local OCR parser implementation (Tesseract/PaddleOCR)
- [ ] Web dashboard for viewing transactions and analytics
- [ ] Category management and auto-categorization improvements
- [ ] Multi-currency support
- [ ] Export functionality (CSV, PDF reports)
- [ ] Budget tracking and alerts
- [ ] Image storage for invoices

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running
- Check `DATABASE_URL` in `.env` matches your database configuration
- Verify database exists: `psql -l | grep finance_tracker`

### Telegram Webhook Issues
- Ensure ngrok is running and URL is accessible
- Verify webhook is set correctly: `curl https://api.telegram.org/botYOUR_BOT_TOKEN/getWebhookInfo`
- Check that webhook URL uses HTTPS

### Gemini API Issues
- Verify `GEMINI_API_KEY` is set correctly in `.env`
- Check API quota/limits in Google AI Studio
- Review logs for specific error messages

## License

MIT
