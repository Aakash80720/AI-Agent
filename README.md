# 🤖 Context-Aware SQL Agent for CRUD Operations

An **intelligent conversational SQL assistant** that revolutionizes database interactions by converting natural language into precise SQL operations. Built with **LangGraph** for advanced conversation flow management and **context-aware field collection**.

---

## 🎯 Core Mission

Transform complex database operations into simple conversations. Whether you're a business analyst, data scientist, or developer, interact with your database using plain English and let AI handle the SQL complexity.

## ⚡ Key Features

### 🧠 **Context-Aware Intelligence**
- **Smart Context Retention**: Remembers conversation history and adapts responses
- **Intent Recognition**: Understands whether you want to Create, Read, Update, or Delete data
- **Dynamic Schema Analysis**: Automatically explores database structure for optimal query generation
- **Relationship Mapping**: Intelligently handles table joins and foreign key relationships

### 🔄 **Complete CRUD Operations**

#### **CREATE (Insert Data)**
```
💬 "Add a new employee John Smith in Engineering with salary 85000"
🤖 "Please provide a value for: hire_date"
💬 "2024-01-15" 
🤖 ✅ Employee successfully created with ID 26
```

#### **READ (Query Data)**
```
💬 "Show me all high-performing employees earning above 75000"
🤖 📊 [Interactive Table with 12 employees] - Click to edit any cell
```

#### **UPDATE (Modify Data)**
```
💬 "Update Sarah's salary to 90000"
🤖 "Which Sarah? I found 2 employees: Sarah Johnson (HR), Sarah Williams (Engineering)"
💬 "Sarah from Engineering"
🤖 ✅ Sarah Williams' salary updated from 78000 to 90000
```

#### **DELETE (Remove Data)**
```
💬 "Remove the project Alpha that ended last year"
🤖 ⚠️ This will delete Project Alpha (Budget: $150K). Confirm? (yes/no)
💬 "yes"
🤖 ✅ Project Alpha successfully removed
```

### 💬 **Interactive Missing Field Collection**
- **Progressive Data Gathering**: Asks for missing required fields one by one
- **Smart Validation**: Uses Pydantic models to ensure data integrity
- **Context Memory**: Remembers partial inputs across conversation turns
- **Graceful Error Recovery**: Never breaks on incomplete information

### 🎨 **Modern Streamlit UI**
- **Real-time Data Editing**: Click any cell in result tables to edit directly
- **Visual Query Builder**: Generate complex queries through conversation
- **Dark Theme Interface**: Professional, easy-on-eyes design
- **Responsive Layout**: Works perfectly on desktop and mobile

### 🔒 **Enterprise-Ready Features**
- **Local Processing**: All AI computation happens locally via Ollama
- **Data Privacy**: No data sent to external APIs
- **Schema Validation**: Prevents SQL injection and ensures data consistency
- **Error Handling**: Comprehensive error management with user-friendly messages

---

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit UI  │◄──►│  Chat Manager    │◄──►│   SQL Agent     │
│                 │    │  (LangGraph)     │    │                 │
│ • User Input    │    │ • State Mgmt     │    │ • Query Gen     │
│ • Data Display  │    │ • Flow Control   │    │ • Validation    │
│ • Real-time     │    │ • Context Track  │    │ • Execution     │
│   Editing       │    │ • Memory         │    │ • Schema Info   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                    ┌──────────────────┐
                    │   SQLite DB      │
                    │                  │
                    │ • Employee Table │
                    │ • Project Table  │
                    │ • 25+ Records    │
                    └──────────────────┘
```

### 🧩 **Core Components**

1. **SQLAgent** (`sqlagent.py`)
   - Natural language to SQL conversion
   - Query optimization and validation
   - Schema-aware query generation
   - Pydantic model validation

2. **Chat Manager** (`sqlagent.py` - Chat class)
   - LangGraph-based conversation flow
   - State management across interactions
   - Missing field collection workflow
   - Context retention and memory

3. **Streamlit UI** (`chat_ui.py`)
   - Modern conversational interface
   - Interactive data tables with editing
   - Real-time query results
   - Visual feedback and loading states

4. **Data Models**
   - `Employee`: name, department, salary, hire_date
   - `Project`: name, start_date, end_date, budget, department, description

---

## 🚀 Quick Start

### Prerequisites
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull the required AI model
ollama pull devstral
```

### Installation
```bash
# 1. Clone and navigate to project
git clone <repository-url>
cd AI-Agent

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Launch the application
python main.py
```

### Alternative Launch Methods
```bash
# Direct Streamlit launch
streamlit run ai_agent_service/chat_ui.py

# Test integration
python test_integration.py
```

---

## 💡 Usage Examples

### 📊 **Data Analytics Queries**
```
🔍 "What's the average salary by department?"
🔍 "Show me projects with budget over 200K"
🔍 "List employees hired in the last 6 months"
🔍 "Which department has the highest total project budget?"
```

### 🏢 **Business Operations**
```
➕ "Hire a new software engineer named Alex Chen with 95K salary"
📝 "Promote Maria to Senior Developer with 15% salary increase"
🗑️ "Remove the cancelled Project Beta from our records"
🔄 "Transfer all Marketing projects to the Sales department"
```

### 📈 **Complex Analysis**
```
📊 "Compare average salaries between Engineering and Marketing"
📅 "Show projects ending this quarter with their remaining budget"
🏆 "Find the top 5 highest-paid employees and their departments"
📋 "List all employees working on projects with budget > 100K"
```

---

## 🎛️ Advanced Features

### **Smart Context Understanding**
- Recognizes ambiguous queries and asks for clarification
- Maintains conversation context across multiple turns
- Suggests related queries based on current data

### **Data Integrity Protection**
- **Safe Deletes**: Always confirms destructive operations
- **Update Validation**: Ensures data types and constraints
- **Referential Integrity**: Handles foreign key relationships
- **Rollback Capability**: Supports transaction management

### **Query Optimization**
- Automatically optimizes complex queries
- Uses appropriate indexes and joins
- Limits result sets for performance
- Explains query execution plans

---

## 🛠️ Configuration

### Database Configuration
```python
# Default: SQLite local database
DB_URI = "sqlite:///test.db"

# Supported: PostgreSQL, MySQL, SQLite
# DB_URI = "postgresql://user:pass@localhost/dbname"
```

### AI Model Configuration
```python
# Default model
MODEL = "devstral"

# Alternative models
# MODEL = "codellama"
# MODEL = "llama3"
```

### UI Customization
```python
# Streamlit configuration in chat_ui.py
THEME = "dark"
PAGE_TITLE = "SQL Assistant"
LAYOUT = "centered"
```

---

## 🧪 Testing

### **Automated Tests**
```bash
# Run integration tests
python test_integration.py

# Test conversation flows
python -m pytest tests/
```

### **Manual Testing Scenarios**
1. **Complete Query Flow**: Test immediate execution
2. **Incomplete Query Flow**: Test missing field collection
3. **Error Handling**: Test invalid inputs and constraints
4. **UI Responsiveness**: Test real-time editing features

---

## 🔍 Troubleshooting

### **Common Issues**

**🚨 Model Not Found**
```bash
# Solution: Pull the required model
ollama pull devstral
```

**🚨 Database Connection Error**
```bash
# Solution: Ensure database file exists
python test.py  # Creates test.db with sample data
```

**🚨 Streamlit Not Loading**
```bash
# Solution: Install missing dependencies
pip install streamlit langchain-community
```

---

## 🎯 Use Cases

### **Business Intelligence**
- **Executive Dashboards**: Generate KPI queries through conversation
- **Report Generation**: Create complex reports with natural language
- **Data Exploration**: Discover insights through guided questioning

### **Data Management**
- **Employee Onboarding**: Add new employees with guided data collection
- **Project Tracking**: Manage project lifecycles through conversational updates
- **Inventory Management**: Track and update inventory through natural language

### **Development & Testing**
- **Database Seeding**: Add test data through conversational interface
- **Schema Exploration**: Understand database structure through questions
- **Query Development**: Prototype complex queries through iteration

---

## 🚀 Future Enhancements

- **Multi-Database Support**: Connect to multiple databases simultaneously
- **Advanced Analytics**: Statistical analysis and visualization generation
- **Voice Interface**: Speech-to-SQL capabilities
- **API Integration**: RESTful API for programmatic access
- **Collaboration Features**: Share queries and results with teams
- **Export Capabilities**: Generate reports in PDF, Excel, and other formats

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on:
- Code style and standards
- Testing requirements
- Pull request process
- Feature development guidelines

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**🌟 Transform Your Database Interactions Today! 🌟**

*Built with ❤️ using LangChain, LangGraph, Streamlit, and Ollama*

[📖 Documentation](docs/) • [🐛 Report Bug](issues/) • [💡 Request Feature](issues/) • [💬 Community](discussions/)

</div>