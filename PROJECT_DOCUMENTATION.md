# P SQUARE - INTELLIGENT HYBRID RAG CHATBOT

## 📋 PROJECT OVERVIEW

**Project Name:** P Square Intelligent Chatbot
**Type:** Local Hybrid RAG (Retrieval-Augmented Generation) System
**Purpose:** A privacy-focused chatbot that intelligently switches between querying structured SQL data and unstructured PDF documents using local AI.
**Status:** ✅ COMPLETED & PRODUCTION READY

---

## 🎯 KEY FEATURES

### 1. Hybrid Intelligence
The system automatically classifies user intent to choose the best data source:
- **Structured Data (SQL):** Generates SQL queries for database questions (e.g., "How many passengers survived?").
- **Unstructured Data (PDF):** Uses Vector Search for policy/document questions (e.g., "What is the vacation policy?").
- **Conversational:** Handles greetings and general chit-chat.

### 2. Fully Local AI Stack
- **No External APIs:** Runs entirely on your machine.
- **LLM:** Uses **Ollama** running `gemma3:1b` for reasoning and generation.
- **Embeddings:** Uses `nomic-embed-text` for high-quality vector representations.
- **Privacy:** Zero data leakage to cloud providers.

### 3. Advanced RAG Pipeline
- **Ingestion:** Automated PDF text extraction, chunking, and embedding.
- **Storage:** PostgreSQL with `pgvector` extension for efficient similarity search.
- **Retrieval:** Cosine similarity search to find relevant document chunks.

---

## 🔧 TECHNOLOGY STACK

### Backend Technologies
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.x | Backend programming language |
| **Django** | 4.2.7 | Web framework |
| **Django REST Framework** | 3.14.0 | RESTful API creation |
| **PostgreSQL** | Latest | Primary database with `pgvector` |
| **Ollama** | Latest | Local AI Server |
| **PyPDF2** | 3.0.1 | PDF Text Extraction |

### Frontend Technologies
| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 19.2.3 | UI framework |
| **lucide-react** | 0.563.0 | Icon library |

### AI Models (Local)
- **Generation**: `gemma3:1b` (Google's lightweight open model)
- **Embedding**: `nomic-embed-text` (768-dimensional vectors)

---

## 📊 DATABASE SCHEMA

### 1. Titanic Model (Structured Data)
```python
class Titanic:
    passenger_id = IntegerField (Primary Key)
    survived = IntegerField (0 or 1)
    pclass = IntegerField (1, 2, or 3)
    name = TextField
    sex = TextField
    age = FloatField (Nullable)
    sibsp = IntegerField (Siblings/Spouses)
    parch = IntegerField (Parents/Children)
    ticket = TextField
    fare = FloatField
    cabin = TextField (Nullable)
    embarked = TextField (Nullable)
```

---

## 🔄 COMPLETE APPLICATION FLOW

### 1. User Authentication Flow
```
User Opens App
    ↓
Check localStorage for token
    ↓
├─ Token Found → Load User Data → Show Chat Interface
└─ No Token → Show Home Screen with Login/Signup Options
    ↓
User Clicks Login/Signup
    ↓
Auth Component Renders
    ↓
User Enters Credentials OR Uses Google OAuth
    ↓
POST /api/login/ or /api/signup/ or /api/google-auth/
    ↓
Backend Validates Credentials
    ↓
├─ Valid → Generate Token → Return {token, user}
└─ Invalid → Return Error
    ↓
Frontend Stores Token & User in localStorage
    ↓
Load User's Chat History from /api/user-chats/
    ↓
Redirect to Chat Interface
```

### 2. Chat Message Flow
```
User Types Message in Input Field
    ↓
User Presses Enter or Clicks Send
    ↓
Check if User is Authenticated
    ↓
├─ Not Authenticated → Show Login Prompt
└─ Authenticated → Continue
    ↓
Add User Message to Chat UI
    ↓
Show "Solven is thinking..." Loading State
    ↓
POST /api/chat/ with {question: "user message"}
    ↓
Backend Receives Request
    ↓
Verify Token Authentication
    ↓
Extract Question from Request
    ↓
Call process_user_query(question) in gemini.py
    ↓
Check if Greeting/General Question
    ↓
├─ Yes → Return Predefined Response
└─ No → Continue to AI Processing
    ↓
Build Prompt with Database Schema + User Question
    ↓
Send to Google Gemini API
    ↓
Gemini Generates SQL Query
    ↓
Clean & Validate SQL Query
    ↓
Execute SQL on PostgreSQL Database
    ↓
Fetch Results (columns + rows)
    ↓
Format Results with Gemini AI
    ↓
Return Natural Language Response
    ↓
Backend Returns {answer: "formatted response"}
    ↓
Frontend Receives Response
    ↓
Add Bot Message to Chat UI
    ↓
Save Chat to Database via /api/user-chats/
    ↓
Update Chat History in Sidebar
```

### 3. Chat History Management Flow
```
User Clicks "New Chat"
    ↓
Reset activeChatId to null
    ↓
Show Welcome Screen

User Clicks on Chat in Sidebar
    ↓
Load Chat Messages from history
    ↓
Display Messages in Chat Interface

User Deletes Chat
    ↓
DELETE /api/user-chats/?chat_id={id}
    ↓
Remove from Sidebar
    ↓
If Active Chat → Show Welcome Screen
```

---

## 🔌 API ENDPOINTS

### Authentication Endpoints

#### 1. Signup
```
POST /api/signup/
Body: {
    "username": "string",
    "email": "string",
    "password": "string"
}
Response: {
    "token": "string",
    "user": {
        "id": "uuid",
        "username": "string",
        "email": "string",
        "profile_picture": "url"
    }
}
```

#### 2. Login
```
POST /api/login/
Body: {
    "login": "email or username",
    "password": "string"
}
Response: {
    "token": "string",
    "user": {...}
}
```

#### 3. Google OAuth
```
POST /api/google-auth/
Body: {
    "email": "string",
    "name": "string",
    "picture": "url",
    "google_id": "string"
}
Response: {
    "token": "string",
    "user": {...}
}
```

### Chat Endpoints

#### 4. Send Message
```
POST /api/chat/
Headers: {
    "Authorization": "Token {token}"
}
Body: {
    "question": "string"
}
Response: {
    "answer": "string"
}
```

### Chat History Endpoints

#### 5. Get User Chats
```
GET /api/user-chats/
Headers: {
    "Authorization": "Token {token}"
}
Response: [
    {
        "id": "uuid",
        "title": "string",
        "messages": [...]
    }
]
```

#### 6. Create Chat
```
POST /api/user-chats/
Headers: {
    "Authorization": "Token {token}"
}
Body: {
    "title": "string",
    "messages": []
}
Response: {
    "id": "uuid",
    "title": "string",
    "messages": []
}
```

#### 7. Update Chat
```
PUT /api/user-chats/
Headers: {
    "Authorization": "Token {token}"
}
Body: {
    "chat_id": "uuid",
    "messages": [...]
}
Response: {
    "success": true
}
```

#### 8. Delete Chat
```
DELETE /api/user-chats/?chat_id={uuid}
Headers: {
    "Authorization": "Token {token}"
}
Response: {
    "success": true
}
```

---

## 🧠 GEMINI AI INTEGRATION DETAILS

### File: backend/api/gemini.py

#### Key Functions:

**1. process_user_query(user_question)**
- Main entry point for query processing
- Checks for greetings first
- Generates SQL using Gemini
- Executes SQL on database
- Formats response naturally

**2. is_greeting_or_general(user_question)**
- Detects greetings: "hi", "hello", "hey", etc.
- Detects help requests
- Returns boolean

**3. handle_greeting_or_general(user_question)**
- Returns predefined friendly responses
- Explains chatbot capabilities

**4. execute_sql_query(sql_query)**
- Safely executes SQL on PostgreSQL
- Returns columns and results
- Error handling

**5. get_database_schema()**
- Returns schema information for Gemini
- Includes table names and column types

**6. format_response_with_gemini(question, columns, results)**
- Uses Gemini to convert SQL results to natural language
- Limits results to 10 rows
- Fallback formatting if Gemini fails

### Gemini Configuration:
```python
model = genai.GenerativeModel("models/gemini-2.5-flash")
response = model.generate_content(
    prompt,
    generation_config=genai.types.GenerationConfig(
        temperature=0.1,  # Low for SQL generation
        max_output_tokens=200
    )
)
```

### Example Prompts:

**SQL Generation Prompt:**
```
Convert this natural language question into a PostgreSQL query.

Database Schema:
Available tables:
1. state_data: state (text), population (integer), income (decimal)
2. titanic: passenger_id (int), survived (int), pclass (int), name (text), sex (text), age (float), fare (float)

User Question: {user_question}

Rules:
1. Generate only SELECT queries
2. Use proper PostgreSQL syntax
3. Handle complex conditions (age ranges, combined counts, etc.)
4. For state data: use state_data table
5. For Titanic data: use titanic table
6. Return ONLY the SQL query

SQL Query:
```

**Response Formatting Prompt:**
```
Convert this database result into a natural, conversational response for the user's question.

User Question: {question}
Database Results:
{data_text}

Instructions:
1. Write a clear, natural response
2. Include specific numbers and names from the data
3. Keep it concise but complete
4. Don't mention technical database terms
5. If there are many results, summarize the key findings

Response:
```

---

## 🎨 FRONTEND ARCHITECTURE

### Component Hierarchy:
```
App.js (Main Container)
├── Auth.js (Authentication Wrapper)
│   ├── LoginForm.js
│   ├── SignupForm.js
│   └── GoogleAuth.js
│
├── Sidebar.js (Chat History & Navigation)
│   ├── Brand Logo
│   ├── Auth Buttons (Login/Signup/Logout)
│   ├── New Chat Button
│   ├── Navigation Items
│   ├── Recent Conversations List
│   └── User Profile Section
│
└── Chatbot.js (Main Chat Interface)
    ├── Welcome Screen (No Active Chat)
    │   ├── Greeting
    │   ├── Input Field
    │   ├── Quick Action Chips
    │   └── Weather Widget
    │
    └── Chat Conversation (Active Chat)
        ├── Message List
        │   ├── User Messages
        │   └── Bot Messages
        ├── Loading Indicator
        └── Sticky Input Container
```

### State Management:
```javascript
// App.js State
const [history, setHistory] = useState([]);           // Chat history
const [activeChatId, setActiveChatId] = useState(null); // Current chat
const [user, setUser] = useState(null);               // User data
const [isAuthenticated, setIsAuthenticated] = useState(false);
const [showAuth, setShowAuth] = useState(false);
const [authView, setAuthView] = useState('login');
const [loading, setLoading] = useState(true);

// Chatbot.js State
const [text, setText] = useState("");                 // Input text
const [loading, setLoading] = useState(false);        // Loading state
```

### Key Frontend Functions:

**1. handleAuthSuccess(userData)**
- Stores user data
- Sets authentication state
- Loads chat history
- Closes auth modal

**2. handleSend()**
- Validates authentication
- Adds user message to UI
- Calls API
- Adds bot response
- Saves chat to database

**3. createNewChat()**
- Resets active chat
- Shows welcome screen

**4. updateChat(chatId, chatTitle, updatedMessages)**
- Updates existing chat OR creates new
- Syncs with backend
- Updates sidebar

**5. removeHistory(id)**
- Deletes chat from backend
- Removes from sidebar
- Resets if active

---

## 🔐 AUTHENTICATION SYSTEM

### Token-Based Authentication

**Backend (Django):**
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
}

# views.py
class ChatBotAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
```

**Frontend (authService.js):**
```javascript
authenticatedFetch: async (url, options = {}) => {
    const token = authService.getToken();
    
    const config = {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Token ${token}`,
            ...options.headers,
        },
    };

    const response = await fetch(`${API_BASE_URL}${url}`, config);
    
    if (response.status === 401) {
        authService.logout();
        window.location.reload();
    }
    
    return response;
}
```

### Google OAuth Flow:
1. User clicks "Sign in with Google"
2. Google OAuth popup opens
3. User authorizes
4. Frontend receives: email, name, picture, google_id
5. POST to /api/google-auth/
6. Backend creates/finds user
7. Returns token
8. Frontend stores token & user

---

## 🎨 UI/UX DESIGN

### Design System:
- **Style**: Glassmorphism (frosted glass effect)
- **Color Scheme**: Dark theme with purple accents
- **Typography**: Modern sans-serif
- **Icons**: Lucide React icons

### Key UI Features:
1. **Glassmorphism Effects**
   - Backdrop blur
   - Semi-transparent backgrounds
   - Subtle borders

2. **Responsive Design**
   - Mobile-friendly
   - Flexible layouts
   - Adaptive components

3. **Interactive Elements**
   - Hover effects
   - Smooth transitions
   - Loading animations

4. **User Feedback**
   - Loading indicators
   - Error messages
   - Success confirmations

---

## 🚀 SETUP & DEPLOYMENT

### Prerequisites:
- Python 3.x
- Node.js & npm
- PostgreSQL
- Google Gemini API Key

### Environment Variables:

**Backend (.env):**
```
DB_NAME=LLM
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
GEMINI_API_KEY=your_gemini_api_key
```

**Frontend (.env):**
```
REACT_APP_API_URL=http://localhost:8000
```

### Installation Steps:

**1. Run Setup Script:**
```bash
setup.bat
```
This will:
- Install Python dependencies
- Run database migrations
- Test database connection
- Install Node.js dependencies

**2. Start Application:**
```bash
start_application.bat
```
This will:
- Start Django backend on port 8000
- Start React frontend on port 3000
- Open in browser automatically

### Manual Setup:

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py runserver 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm start
```

---

## 🧪 TESTING

### Backend Tests:
```bash
# Test database connection
python backend/test_connection.py

# Test Gemini API
python backend/test_gemini.py

# Test API endpoints
python test_api.py

# Check Titanic data
python backend/check_titanic.py
```

### Sample Test Queries:

**State Data:**
- "What is the population of Maharashtra?"
- "Show me the income of Karnataka"
- "List all states with population over 50000"
- "Which state has the highest income?"

**Titanic Data:**
- "How many passengers survived?"
- "What was the average age of passengers?"
- "How many first-class passengers were there?"
- "Show me survival rate by gender"
- "Combined count of male and female between age 20-40"

---

## 🔒 SECURITY FEATURES

1. **Token Authentication**: Secure API access
2. **Password Hashing**: Django's built-in password hashing
3. **CORS Protection**: Configured allowed origins
4. **SQL Injection Prevention**: Parameterized queries
5. **Environment Variables**: Sensitive data not in code
6. **HTTPS Ready**: Production-ready configuration
7. **SELECT Only**: No data modification queries allowed

---

## 📈 PERFORMANCE OPTIMIZATIONS

1. **Gemini API**:
   - Low temperature (0.1) for consistent SQL
   - Limited output tokens (200 for SQL, 1000 for responses)
   - Fallback formatting if API fails

2. **Database**:
   - Indexed primary keys
   - Efficient query execution
   - Connection pooling

3. **Frontend**:
   - React hooks for efficient re-renders
   - Lazy loading of components
   - Optimized state management

4. **API**:
   - Token-based auth (no session overhead)
   - JSON responses (lightweight)
   - CORS optimization

---

## 🐛 ERROR HANDLING

### Backend:
```python
try:
    result = process_user_query(question)
    return Response({"answer": result})
except Exception as e:
    return Response({"answer": f"Sorry, I couldn't process your question. Error: {str(e)}"})
```

### Frontend:
```javascript
try {
    const data = await authService.sendMessage(userQuestion);
    const botMsg = { type: "bot", content: data.answer };
    updateChat(chatId, title, [...messagesWithUser, botMsg]);
} catch (error) {
    updateChat(chatId, title, [...messagesWithUser, { 
        type: "bot", 
        content: "Error: Connection failed." 
    }]);
}
```

---

## 📝 KEY FEATURES SUMMARY

### ✅ Completed Features:
1. ✅ Natural language to SQL conversion
2. ✅ Multi-table database support
3. ✅ User authentication & authorization
4. ✅ Google OAuth integration
5. ✅ Chat history persistence
6. ✅ Real-time chat interface
7. ✅ Intelligent response formatting
8. ✅ Greeting detection
9. ✅ Error handling & fallbacks
10. ✅ Responsive UI design
11. ✅ Token-based security
12. ✅ CORS configuration
13. ✅ Automated setup scripts
14. ✅ Database testing utilities
15. ✅ API documentation

---

## 🎓 LEARNING OUTCOMES

### Technologies Mastered:
1. **Django REST Framework**: API development
2. **React.js**: Modern frontend development
3. **PostgreSQL**: Relational database management
4. **Google Gemini AI**: AI/ML integration
5. **Token Authentication**: Security implementation
6. **OAuth 2.0**: Third-party authentication
7. **CORS**: Cross-origin resource sharing
8. **Environment Management**: Configuration best practices
9. **Full-Stack Integration**: Frontend-Backend communication
10. **UI/UX Design**: Modern design patterns

---

## 🔮 FUTURE ENHANCEMENTS (Optional)

1. **Voice Input**: Speech-to-text integration
2. **Export Chat**: Download chat history as PDF
3. **Multi-language Support**: Internationalization
4. **Advanced Analytics**: Query statistics dashboard
5. **Custom Datasets**: User-uploaded data support
6. **Real-time Collaboration**: Multi-user chat rooms
7. **Mobile App**: React Native version
8. **Advanced AI**: Fine-tuned models for specific domains
9. **Caching**: Redis for faster responses
10. **Deployment**: AWS/Azure/GCP hosting

---

## 📞 PROJECT METADATA

**Developer:** Sumit  
**Project Type:** Full-Stack AI Application  
**Duration:** Complete  
**Status:** Production Ready  
**License:** Private  

**Tech Stack Summary:**
- Backend: Django 4.2.7 + DRF + PostgreSQL
- Frontend: React 19.2.3 + Lucide Icons
- AI: Google Gemini 2.5 Flash
- Auth: Token + OAuth 2.0
- Database: PostgreSQL with 2 datasets

**Lines of Code (Approximate):**
- Backend: ~1,500 lines
- Frontend: ~1,200 lines
- Total: ~2,700 lines

---

## 🎉 CONCLUSION

This is a **COMPLETE, PRODUCTION-READY** intelligent chatbot application that successfully integrates:
- Modern web technologies (React + Django)
- AI/ML capabilities (Google Gemini)
- Secure authentication (Token + OAuth)
- Database management (PostgreSQL)
- Professional UI/UX design

The application is fully functional, well-structured, and ready for deployment or further enhancement.

---

**Last Updated:** 2024  
**Documentation Version:** 1.0  
**Project Status:** ✅ COMPLETED
