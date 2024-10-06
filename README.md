# Zen Beauty Salon Assistant

## Overview

Zen Beauty Salon Assistant is an AI-powered application designed to streamline appointment booking, service inquiries, and customer support for a beauty salon. The system integrates a FastAPI backend, a Gradio web interface, and a Telegram bot to provide a versatile and user-friendly experience for both customers and salon staff.

## Features

- **AI-powered Chat Interface**: Utilizes advanced language models to understand and respond to customer queries.
- **Appointment Booking**: Allows customers to check availability, book, reschedule, and cancel appointments.
- **Service Information**: Provides detailed information about salon services and specialists.
- **Multi-platform Support**: Accessible via web interface and Telegram bot.
- **Google Calendar Integration**: Syncs appointments with Google Calendar for efficient management.
- **FAQ Handling**: Answers common questions about the salon using a vector database.

## Technology Stack

- **Backend**: FastAPI, Python 3.11
- **AI Model**: LangChain with various LLM providers (OpenAI, Anthropic, Google, Meta)
- **Database**: Pinecone (Vector Database)
- **Frontend**: Gradio (Web Interface)
- **Messaging**: Telegram Bot API
- **Scheduling**: Google Calendar API
- **Data Processing**: Pandas
- **Environment Management**: Docker 

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/zen-beauty-salon-assistant.git
   cd zen-beauty-salon-assistant
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file in the root directory and add the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   GOOGLE_SERVICE_ACCOUNT_JSON=your_google_service_account_json
   TIMEZONE=America/New_York
   ```

## Usage

To start the application, run:

```
python main.py
```

This will start the FastAPI server, Gradio interface, and Telegram bot.

- Access the web interface at `http://localhost:5000`
- Interact with the Telegram bot by searching for your bot on Telegram

## Project Structure

- `main.py`: Entry point of the application
- `src/`: Contains the core application logic
  - `agent.py`: Implements the AI agent using LangChain
  - `agent_tools.py`: Defines tools for the AI agent
  - `telegram_bot.py`: Implements the Telegram bot
  - `google_calendar_service.py`: Handles Google Calendar integration
  - `vector_database/`: Manages the Pinecone vector database
- `data/`: Stores JSON data for services and FAQ
- `validators/`: Contains Pydantic models for data validation

## Key Components

### AI Agent

The AI agent is implemented in `src/agent.py`. It uses LangChain to create a conversational AI that can understand user queries and perform actions using various tools.

### Agent Tools

The `src/agent_tools.py` file defines various tools that the AI agent can use to perform actions such as checking availability, booking appointments, and retrieving information.

### Telegram Bot

The Telegram bot is implemented in `src/telegram_bot.py`, allowing users to interact with the AI assistant through Telegram.

### Google Calendar Integration

The `src/google_calendar_service.py` file handles the integration with Google Calendar, allowing the system to manage appointments in sync with Google Calendar.

## Contributing

Contributions to the Zen Beauty Salon Assistant are welcome! Please follow these steps:

1. Fork the repository
2. Create a new branch: `git checkout -b feature-branch-name`
3. Make your changes and commit them: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-branch-name`
5. Submit a pull request

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.


