# Agent System

A research paper ingestion and analysis system that automatically processes arXiv papers and generates daily research reports.

> **Note**: The system name is configurable via the `SYSTEM_NAME` environment variable. By default, it uses "TORRI" but can be customized to any name you prefer.

## Features

- **Automatic Paper Ingestion**: Fetches papers from arXiv feeds
- **PDF Processing**: Extracts and analyzes PDF content
- **LLM Analysis**: Generates summaries using local LLM models (Ollama)
- **Daily Reports**: Creates comprehensive research summaries
- **Email Notifications**: Sends reports via email (Gmail)
- **Database Storage**: Stores papers and analysis in Qdrant vector database

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Environment

The easiest way to configure the system is using the `.env` file:

```bash
# Run the setup script
python setup_env.py

# Or manually copy and edit the template
cp env.example .env
nano .env
```

### 3. Configure Email (Optional)

To enable email reports, set these in your `.env` file:

```bash
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-16-char-app-password
RECIPIENT_EMAIL=recipient@example.com
```

**Note**: Use Gmail App Passwords, not your regular password. See [EMAIL_SETUP.md](EMAIL_SETUP.md) for detailed instructions.

### 4. Start Services

```bash
# Start Qdrant database
docker run -p 6333:6333 qdrant/qdrant

# Start Ollama with your preferred model
ollama run llama4:latest
```

### 5. Run the System

```bash
# Test the system
python test_email.py

# Run daily report generation
python src/daily_report.py

# Or use the main Agent class
python -c "
from src.agent import Agent
agent = Agent()
agent.initialize()
agent.generate_daily_report()
"
```

## Configuration

The system uses environment variables for configuration. You can set them in two ways:

### Option 1: .env file (Recommended)
Create a `.env` file in the system root directory. See `env.example` for a template.

### Option 2: System environment variables
```bash
export QDRANT_HOST=127.0.0.1
export OLLAMA_URL=http://127.0.0.1:11434
export SENDER_EMAIL=your-email@gmail.com
# ... etc
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_HOST` | `127.0.0.1` | Qdrant database host |
| `QDRANT_PORT` | `6333` | Qdrant database port |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama API endpoint |
| `SENDER_EMAIL` | - | Gmail sender address |
| `SENDER_PASSWORD` | - | Gmail app password |
| `RECIPIENT_EMAIL` | - | Email recipient address |
| `MAX_PAPERS` | `20` | Maximum papers per report |
| `PDF_CHUNK_SIZE` | `800` | PDF text chunk size |

## Project Structure

```
agent/
├── src/                    # Source code
│   ├── agent.py          # Main Agent class
│   ├── llm.py            # LLM analysis
│   ├── database.py       # Database operations
│   ├── config.py         # Configuration management
│   └── routines/         # Core routines
│       ├── reporter.py   # Report generation
│       ├── ingester.py   # Paper ingestion
│       └── downloader.py # PDF downloading
├── config/                # Configuration files
├── prompts/               # LLM prompt templates
├── data/                  # Data storage
├── systemd/               # Systemd service files
├── .env                   # Environment variables (create from env.example)
├── env.example            # Environment template
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Email Setup

For detailed email configuration instructions, see [EMAIL_SETUP.md](EMAIL_SETUP.md).

## Development

### Testing

```bash
# Test email functionality
python test_email.py

# Test full workflow
python test_full_workflow.py
```

### Adding New Features

1. Follow the existing code structure
2. Add configuration options to `src/config.py`
3. Update `requirements.txt` for new dependencies
4. Add tests for new functionality

## Troubleshooting

### Common Issues

- **"yagmail not installed"**: Run `pip install yagmail`
- **"No .env file found"**: Copy `env.example` to `.env` and configure
- **Email authentication failed**: Check your Gmail app password
- **Database connection failed**: Ensure Qdrant is running on the correct port

### Getting Help

1. Check the configuration with `python test_email.py`
2. Review the logs for error messages
3. Verify all services are running (Qdrant, Ollama)
4. Check your `.env` file configuration

## License

This project is open source. Please see the LICENSE file for details.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request
