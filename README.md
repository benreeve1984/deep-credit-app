# OpenAI Background Processing with FastHTML + Webhook Demo

A minimal FastHTML web application demonstrating the "queue-with-background + webhook callback" pattern using OpenAI's API. Submit long-running prompts that process in the background and receive real-time updates via webhooks.

## 🚀 Features

- **Background Processing**: Queue long-running OpenAI tasks without blocking the UI
- **Webhook Callbacks**: Secure webhook verification for OpenAI completion notifications  
- **Real-time Updates**: HTMX-powered polling shows live progress without page refreshes
- **Minimal UI**: Clean, responsive interface built entirely with FastHTML + HTMX
- **Vercel Ready**: Zero-config deployment to Vercel with extended function timeouts

## 📋 Project Structure

```
/
├── app.py              # FastHTML application with all endpoints
├── openai_client.py    # OpenAI SDK wrapper + webhook verification
├── requirements.txt    # Python dependencies  
├── vercel.json         # Vercel deployment configuration
├── env.example         # Environment variable template
└── README.md           # This file
```

## 🛠️ Local Development Setup

### 1. Clone and Install Dependencies

```bash
# Clone the repository (or create the files manually)
git clone <your-repo-url>
cd deep-credit-app

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

```bash
# Copy the example environment file
cp env.example .env

# Edit .env and add your OpenAI API key:
# OPENAI_API_KEY=your_actual_openai_api_key_here
# OPENAI_WEBHOOK_SECRET=get_this_from_openai_dashboard
```

### 3. Run the Application

```bash
# Start the development server
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Or run directly with Python
python app.py
```

The application will be available at: http://localhost:8000

## ☁️ Vercel Deployment

### 1. Deploy to Vercel

```bash
# Install Vercel CLI (if not already installed)
npm i -g vercel

# Deploy to Vercel
vercel --prod

# Or simply:
# - Push to GitHub
# - Connect your repo to Vercel dashboard
# - Click "Deploy"
```

### 2. Configure OpenAI Webhook (Optional)

If you're using actual OpenAI background processing (not the demo simulation):

1. Go to your **OpenAI Dashboard** → **Webhooks**
2. Click **"Create Webhook"**
3. Configure:
   - **URL**: `https://deep-credit-app.vercel.app/api/webhook`
   - **Events**: Select `response.completed`, `response.failed`, etc.
4. **Copy the generated secret** - OpenAI automatically generates this for you

### 3. Set Environment Variables in Vercel

1. Go to your Vercel project → Settings → Environment Variables
2. Add these variables:

```
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_WEBHOOK_SECRET=secret_copied_from_openai_dashboard
```

**Note**: The `OPENAI_WEBHOOK_SECRET` comes from your OpenAI webhook configuration (Step 2), not something you generate yourself.

## 🎯 How It Works

### The Flow

1. **User submits prompt** → Form posts to `/api/queue`
2. **Queue endpoint** → Calls OpenAI API with background processing + webhook URL
3. **HTMX polling** → Browser polls `/api/status/<id>` every 2 seconds
4. **Webhook callback** → OpenAI posts completion to `/api/webhook` 
5. **Status updates** → Polling picks up completed result and displays it

### Key Endpoints

- **`GET /`** - Main web interface with HTMX form
- **`POST /api/queue`** - Queue new background task
- **`POST /api/webhook`** - Receive OpenAI webhook callbacks (with signature verification)
- **`GET /api/status/<id>`** - Check task status and get results
- **`GET /health`** - Health check for monitoring

### Security Features

- **Webhook Signature Verification**: All webhook requests are verified using HMAC-SHA256
- **Environment Variable Protection**: No secrets in code - all sensitive data via env vars
- **Request Validation**: Proper input validation and error handling

## 🔧 Technical Details

### Framework Stack

- **FastHTML**: Modern Python web framework with built-in HTMX support
- **OpenAI SDK**: Async Python client for OpenAI API
- **HTMX**: Frontend interactivity without JavaScript
- **Starlette**: ASGI framework (FastHTML builds on this)

### Background Processing

Currently uses simulated background processing for demonstration. In production, you would:

1. Use OpenAI's actual background processing API (when available)
2. Or implement your own async task queue (Celery, RQ, etc.)
3. Or use serverless functions with queues (AWS SQS, etc.)

### Storage

Uses in-memory storage for simplicity. For production, replace with:
- **Redis** for fast, temporary task storage
- **PostgreSQL** for persistent task history
- **DynamoDB** for serverless storage on AWS

## 🧪 Testing the Application

### Test the Web Interface

1. Open http://localhost:8000
2. Enter a prompt like: "Write a short story about a robot learning to paint"
3. Click "Queue Task"
4. Watch the real-time status updates as it processes
5. See the completed result appear automatically

### Test the API Directly

```bash
# Queue a task
curl -X POST http://localhost:8000/api/queue \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "prompt=Hello%20world"

# Check task status (replace with actual task ID)
curl http://localhost:8000/api/status/resp_123456

# Health check
curl http://localhost:8000/health
```

## 🐛 Troubleshooting

### Common Issues

**"OpenAI API key not found"**
- Ensure `OPENAI_API_KEY` is set in your environment variables
- Check that your `.env` file is properly loaded

**"Webhook signature verification failed"**
- Ensure `OPENAI_WEBHOOK_SECRET` matches between your app and OpenAI dashboard
- Generate a new secret with `openssl rand -hex 32`

**"Module not found" errors**
- Run `pip install -r requirements.txt`
- Ensure you're using Python 3.11+

**Vercel deployment issues**
- Check that `vercel.json` is present in your repository
- Verify environment variables are set in Vercel dashboard
- Check Vercel function logs for detailed error messages

### Local Development Tips

- Use `uvicorn app:app --reload` for automatic reloading during development
- Check browser network tab to see HTMX requests and responses
- Use `python -c "import openssl; print(openssl.rand.hex(32))"` if `openssl` command is not available

## 📚 Next Steps

To extend this demo:

1. **Add persistence**: Replace in-memory storage with Redis/PostgreSQL
2. **Add authentication**: Implement user accounts and API keys
3. **Add rate limiting**: Prevent abuse with request throttling
4. **Add monitoring**: Implement logging and metrics collection
5. **Add real background processing**: Use actual OpenAI background API or implement async task queues

## 📄 License

This project is provided as-is for demonstration purposes. 