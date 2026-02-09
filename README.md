# P Square Intelligent Chatbot

An intelligent chatbot system that connects React frontend with Django backend, integrated with Gemini AI and PostgreSQL database.

## Features

- **Natural Language Processing**: Uses Google Gemini AI to understand user queries
- **Database Integration**: Connects to PostgreSQL with state data and Titanic dataset
- **Intelligent Query Processing**: Converts natural language to SQL queries
- **Real-time Chat Interface**: Modern React-based chat UI
- **Multi-table Support**: Handles queries for both state_data and titanic tables

## Architecture

```
Frontend (React) ↔ Backend (Django) ↔ Gemini AI ↔ PostgreSQL
```

## Quick Start

1. **Setup (First time only)**:
   ```bash
   setup.bat
   ```

2. **Start Application**:
   ```bash
   start_application.bat
   ```

3. **Access the Application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/api/chat/

## Sample Queries

### State Data Queries
- "What is the population of Maharashtra?"
- "Show me the income of Karnataka"
- "List all states with population over 50000"
- "Which state has the highest income?"

### Titanic Data Queries
- "How many passengers survived?"
- "What was the average age of passengers?"
- "How many first-class passengers were there?"
- "Show me survival rate by gender"

## Database Schema

### state_data table
- `state`: Name of Indian state
- `population`: Population in thousands
- `income`: Average income in rupees

### titanic table
- `passenger_id`: Unique ID
- `survived`: 0=died, 1=survived
- `pclass`: Passenger class (1,2,3)
- `name`: Passenger name
- `sex`: Gender
- `age`: Age in years
- `fare`: Ticket fare
- And more...

## Configuration

### Environment Variables (.env)
```
DB_NAME=LLM
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
GEMINI_API_KEY=your_gemini_api_key
```

## Testing

Test the API functionality:
```bash
python test_api.py
```

## How It Works

1. **User Input**: User types a question in the React frontend
2. **API Call**: Frontend sends POST request to Django backend
3. **Gemini Processing**: Backend uses Gemini AI to:
   - Understand the natural language query
   - Generate appropriate SQL query
   - Create response template
4. **Database Query**: Execute SQL query on PostgreSQL
5. **Response**: Format and return natural language response
6. **Display**: Frontend displays the response in chat interface

## Technology Stack

- **Frontend**: React.js with modern UI components
- **Backend**: Django REST Framework
- **AI**: Google Gemini AI API
- **Database**: PostgreSQL
- **Additional**: CORS handling, Environment variables

## Troubleshooting

1. **Database Connection Issues**:
   - Verify PostgreSQL is running
   - Check .env file credentials
   - Run `python test_connection.py`

2. **Gemini API Issues**:
   - Verify GEMINI_API_KEY in .env
   - Check API quota and billing

3. **Frontend-Backend Connection**:
   - Ensure both servers are running
   - Check CORS settings
   - Verify API endpoint URLs

## Development

The system is designed to be easily extensible:
- Add new database tables in `models.py`
- Extend Gemini prompts in `gemini.py`
- Modify frontend components as needed
- No changes needed to existing frontend code

## Security Notes

- API keys are stored in environment variables
- SQL injection protection through parameterized queries
- CORS properly configured for development
- Only SELECT queries allowed (no data modification)