# AI Agent SQL Assistant

An intelligent SQL assistant that converts natural language queries into SQL and handles interactive conversations for missing data fields.

## Features

✅ **Fixed Issues:**
- **Human Conversation Chain**: Now properly handles missing field collection through interactive chat
- **Chat UI Integration**: Fully connected with the SQL Agent conversation flow  
- **Error Handling**: Graceful handling of missing values without throwing errors or infinite loops
- **State Management**: Proper conversation state tracking using LangGraph
- **Visual Feedback**: Clear indicators when system is waiting for user input

## Key Improvements

### 1. Interactive Missing Field Collection
- When INSERT/UPDATE queries have missing required fields, the system asks for them one by one
- User provides missing values through the chat interface
- System validates and continues the process until all fields are complete

### 2. Enhanced Chat UI
- Visual indicators when waiting for additional input
- Proper conversation flow management
- Better error handling and user feedback
- Support for both complete and incomplete queries

### 3. Robust State Management
- Uses LangGraph for conversation flow control
- Maintains conversation state across multiple interactions
- Supports resuming conversations after collecting missing data

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure Ollama is running with the required model:
```bash
ollama pull devstral
```

## Usage

### Option 1: Launch with Main Script
```bash
python main.py
```

### Option 2: Direct Streamlit Launch  
```bash
streamlit run ai_agent_service/chat_ui.py
```

### Option 3: Test Integration
```bash
python test_integration.py
```

## Example Conversations

### Complete Query (Works Immediately)
**User**: "Show all employees with salary greater than 50000"
**AI**: Executes query and shows results in a table

### Incomplete Query (Interactive Collection)
**User**: "Insert a new employee with name John Doe and salary 70000"
**AI**: "Please provide a value for the missing field: department"
**User**: "Engineering"  
**AI**: "Please provide a value for the missing field: hire_date"
**User**: "2024-01-15"
**AI**: Executes the complete INSERT query

## Architecture

- **SQLAgent**: Core logic for SQL generation and validation
- **Chat**: LangGraph-based conversation flow manager
- **Chat UI**: Streamlit-based web interface
- **State Management**: TypedDict state with conversation tracking

## Database Schema

The system works with:
- **employee** table: name, department, salary, hire_date
- **project** table: name, start_date, end_date, budget, department, description

## Error Handling

- Missing field validation using Pydantic models
- Graceful error messages instead of exceptions
- Conversation state recovery
- SQL execution error handling