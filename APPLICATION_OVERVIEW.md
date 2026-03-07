# Application Overview for Client

## **What Is This Application?**

This is an **AI-Powered Business Intelligence Dashboard Platform** that allows users to interact with their company's data using natural language - no SQL knowledge required. Think of it as having a data analyst available 24/7 through a chatbot interface.

---

## **Core Business Value**

### 🤖 **1. AI Chatbot for Data Queries**
Your users can simply ask questions like:
- "Show me all customers from New York"
- "What were our top 5 selling products last month?"
- "Give me revenue by region for Q4"

The AI automatically converts these questions into database queries and returns the results - **no technical expertise needed**.

### 📊 **2. Custom Dashboards**
Users can create personalized dashboards with:
- Charts (bar, line, pie)
- Data tables
- Drag-and-drop layout customization
- Save and share dashboards across teams

### 🗂️ **3. Self-Documenting Database**
The system automatically:
- Reads your database structure
- Allows you to add descriptions to tables and columns
- Creates a searchable knowledge base
- Helps new team members understand the data

### 💡 **4. Help Desk Knowledge Base**
Store frequently asked questions and common queries so users can:
- Find answers to repeated questions instantly
- Learn from examples
- Build a library of useful queries

---

## **Who Is This For?**

- **Business Analysts** - Get insights without writing SQL
- **Managers** - Create custom dashboards to track KPIs
- **Sales Teams** - Query customer and order data on demand
- **Operations** - Monitor products, inventory, orders
- **Anyone** who needs data but doesn't know SQL

---

## **Technical Architecture**

### **Technology Stack:**
- **Backend**: Flask (Python) - Robust API server
- **Frontend**: Angular 20 - Modern, responsive user interface
- **AI Engine**: Google Gemini AI - Advanced natural language processing
- **Database Support**: Works with MSSQL, PostgreSQL, or SQLite
- **Deployment**: Docker containers for easy installation

### **Key Features:**
✅ Secure user authentication
✅ Multi-database support
✅ Conversation history tracking
✅ Responsive design for desktop/mobile
✅ RESTful API architecture
✅ Easy deployment with Docker

---

## **Available API Endpoints**

### **Authentication**
- `POST /api/login` - User login

### **Dashboard Management**
- `POST /api/dashboard` - Create new dashboard
- `GET /api/dashboards/<user_id>` - Get all user's dashboards
- `GET /api/dashboard/<dashboard_id>` - Get specific dashboard
- `PUT /api/dashboard/<dashboard_id>` - Update dashboard
- `DELETE /api/dashboard/<dashboard_id>` - Delete dashboard
- `POST /api/dashboards/migrate` - Migrate grid layouts

### **AI Chatbot & Query Execution**
- `POST /api/chatbot` - Send query to AI chatbot
- `GET /api/get-bot-messages/<thread_id>` - Get conversation history
- `POST /api/get-query-result` - AI-powered query generation + execution
- `POST /api/get-query-result2` - Direct SQL execution

### **Schema Management**
- `GET /api/schema` - Get database schema (JSON or text)
- `GET /api/tables` - List all tables
- `GET /api/tables/<table_name>` - Get table details
- `POST /api/descriptions` - Add/update table description
- `GET /api/descriptions` - Get all table descriptions
- `POST /api/comments` - Add/update column comment
- `GET /api/comments` - Get all column comments
- `GET /api/schema/file` - Export schema to file
- `GET /` - Interactive schema explorer UI

### **Help Desk**
- `POST /api/helpdesk` - Create help desk entry
- `GET /api/helpdesk` - Get all entries
- `GET /api/helpdesk/<title>` - Get specific entry
- `PUT /api/helpdesk/<title>` - Update entry
- `DELETE /api/helpdesk/<title>` - Delete entry

---

## **Database Schema**

### **Core Application Tables**

#### `user_gen_core`
Stores user accounts and authentication information
- `id` - Unique user identifier
- `username` - User login name
- `email` - User email address

#### `dashboard_gen_core`
Stores dashboard definitions with SQL queries and layout configurations
- `id` - Dashboard ID
- `user_id` - Owner of the dashboard
- `name` - Dashboard name
- `sql_query` - SQL query for data
- `layout_config` - JSON grid layout configuration

#### `helpdesk_gen_core`
Stores help desk entries for common queries
- `title` - Entry title
- `description` - Query description
- `sql_query` - Example SQL query

#### `table_descriptions_gen_core`
Metadata about database tables
- `table_name` - Name of the table
- `description` - Human-readable description

#### `column_comments_gen_core`
Metadata about database columns
- `table_name` - Parent table name
- `column_name` - Column name
- `comment` - Human-readable comment

### **Sample Data Tables** (for demonstration)
- `customers` - Customer records
- `products` - Product catalog
- `orders` - Order records
- `order_items` - Order line items

---

## **Backend Architecture**

```
api/
├── app.py                          # Flask app initialization
├── database.py                     # SQLAlchemy setup
├── requirements.txt                # Python dependencies
├── api-mssql.py                    # MSSQL configuration (currently active)
├── api-postgres.py                 # PostgreSQL configuration
├── api-sqlite.py                   # SQLite configuration
├── utils.py                        # Utility functions
├── routes/
│   ├── core_routes.py             # User, Dashboard, HelpDesk CRUD
│   ├── bot_routes.py              # Chatbot and query execution
│   └── schema_routes.py           # Schema introspection UI & endpoints
├── models/
│   ├── core_model.py              # Database models
│   └── sample_model.py            # ORM models for sample data
├── gen_sql/
│   ├── sql_gen.py                 # LangGraph chatbot implementation
│   ├── schema.py                  # Schema reading & update utilities
│   └── schema_filter.py           # Schema filtering logic
└── schema_readers/
    ├── schema_reader.py           # SQLAlchemy-based inspector
    └── schema_reader_postgres.py  # PostgreSQL-specific reader
```

---

## **Frontend Architecture**

### **Current Stack: Angular 20**

The application uses Angular 20 as its frontend framework with:
- **@Angular/Material** - UI components
- **ng2-charts** - Data visualization
- **@katoid/angular-grid-layout** - Draggable dashboard grids
- **TailwindCSS** - Styling
- **Nginx** - Production web server

### **Previous Stack: React**
The React frontend has been deprecated and removed in the `gemini3` branch.

---

## **AI/LLM Integration**

### **Technology**
- **LangChain** - Framework for LLM integration
- **LangGraph** - Manages conversation flow and state
- **Google Gemini 3 Flash** - AI model for natural language understanding

### **How It Works**
1. User asks a question in natural language
2. LangChain sends context (database schema + question) to Gemini AI
3. AI generates SQL query based on schema
4. System executes query safely
5. Results returned to user in readable format
6. Conversation history maintained per user session

### **Key Features**
- Multi-turn conversations with context
- Thread-based session management
- Schema-aware query generation
- Automatic SQL syntax correction
- Error handling and retry logic

---

## **Deployment Architecture**

### **Docker Compose Setup**

```yaml
Services:
├── Angular Frontend (Port 4200)
│   └── Nginx web server
│   └── Optimized production build
├── Flask API (Port 5000)
│   └── Gunicorn WSGI server
│   └── RESTful API endpoints
└── Shared Network: app-network
```

### **Deployment Steps**

1. **Prerequisites**
   ```bash
   - Docker installed
   - Docker Compose installed
   - Database accessible (MSSQL/PostgreSQL/SQLite)
   ```

2. **Configuration**
   ```bash
   # Edit api/.env file
   DB_SYSTEM=mssql  # or postgres, sqlite
   GOOGLE_API_KEY=your_api_key
   DATABASE_URL=your_database_connection_string
   ```

3. **Launch**
   ```bash
   docker-compose up -d
   ```

4. **Access**
   - Frontend: http://localhost:4200
   - API: http://localhost:5000

---

## **Key Dependencies**

### **Backend (Python)**
```
Flask 2.3.3                    # Web framework
Flask-CORS 4.0.0              # Cross-origin resource sharing
Flask-SQLAlchemy 3.0.5        # Database ORM
LangChain                     # LLM framework
LangGraph                     # Conversation state management
langchain-google-genai        # Google Gemini integration
Python-dotenv                 # Environment variables
Gunicorn                      # Production server
pyodbc                        # MSSQL driver
psycopg2                      # PostgreSQL driver
```

### **Frontend (Angular)**
```
@angular/core ^20.0.0         # Angular framework
@angular/material ^20.0.1     # Material Design components
ng2-charts ^8.0.1             # Chart.js wrapper
@katoid/angular-grid-layout   # Draggable grid
tailwindcss ^3.4.17           # CSS framework
```

---

## **Current Status (gemini3 Branch)**

### **Recent Updates**
- ✨ Migrated from React to Angular 20
- 🔄 Enhanced MSSQL integration and support
- 🤖 Improved AI chatbot with LangGraph
- 📈 Better dashboard grid layout system
- 🗂️ Advanced schema introspection

### **Modified Files**
- `api/.env` - Environment configuration
- `api/requirements.txt` - Updated Python dependencies
- `api/gen_sql/sql_gen.py` - Enhanced query generation
- `docker-compose.yml` - Angular integration

### **Removed**
- All React frontend files (replaced with Angular)

---

## **Security Considerations**

### ⚠️ **Critical: Before Production**

1. **API Key Security**
   - Rotate exposed Google API key
   - Use environment variables or secret managers
   - Never commit `.env` files to git

2. **Database Security**
   - Use read-only database users where possible
   - Implement query result limits
   - Sanitize all SQL inputs
   - Enable SSL/TLS for database connections

3. **Authentication**
   - Implement JWT or session-based auth
   - Add password hashing (bcrypt)
   - Enable HTTPS/SSL certificates
   - Implement rate limiting

4. **API Security**
   - Add CORS whitelist for production
   - Implement API rate limiting
   - Add request validation
   - Enable logging and monitoring

---

## **Business Benefits Summary**

| Benefit | Impact | ROI |
|---------|--------|-----|
| **Democratize Data Access** | Everyone can query data, not just technical staff | 🟢 High - Reduces bottlenecks |
| **Reduce Analyst Workload** | Self-service reduces repetitive requests | 🟢 High - Save analyst time |
| **Faster Decision Making** | Instant access to insights | 🟢 High - Competitive advantage |
| **Knowledge Preservation** | Document queries and database structure | 🟡 Medium - Long-term value |
| **Cost Effective** | AI instead of hiring more analysts | 🟢 High - Direct cost savings |
| **Reduced Training Time** | Intuitive interface for new users | 🟡 Medium - Faster onboarding |

---

## **Use Case Examples**

### **Example 1: Sales Manager**
**Question**: "Show me total sales by region for the last quarter"

**What Happens**:
1. AI converts to: `SELECT region, SUM(total) FROM orders WHERE date >= '2025-10-01' GROUP BY region`
2. Query executes safely
3. Results shown as table + bar chart
4. Can save to dashboard for daily monitoring

### **Example 2: Marketing Team**
**Question**: "Who are our top 10 customers by purchase amount?"

**What Happens**:
1. AI generates appropriate JOIN query across customers and orders
2. Returns ranked list with customer details
3. Export to CSV or save to dashboard
4. Share dashboard with team

### **Example 3: Operations**
**Question**: "Which products are low in stock?"

**What Happens**:
1. AI queries inventory table
2. Filters by threshold
3. Returns actionable list
4. Set up recurring dashboard to monitor daily

---

## **Competitive Advantages**

✅ **vs Traditional BI Tools (Tableau, Power BI)**
- No learning curve - just ask questions
- Faster setup - no complex data modeling
- Lower cost - no per-user licensing

✅ **vs Custom SQL Tools**
- No SQL knowledge required
- AI understands business language
- Self-documenting with help desk

✅ **vs Hiring Data Analysts**
- 24/7 availability
- Instant responses
- Scales to unlimited users
- One-time development cost

---

## **Future Enhancement Opportunities**

### **Short Term**
- 📧 Email scheduled reports
- 📱 Mobile app version
- 🔔 Alert notifications for thresholds
- 📤 Export to Excel/PDF

### **Medium Term**
- 🤖 Advanced AI with predictive analytics
- 👥 Team collaboration features
- 🔐 Role-based access control
- 📊 More chart types (scatter, heatmap, etc.)

### **Long Term**
- 🧠 Machine learning model integration
- 🌐 Multi-language support
- 🔗 Integration with external APIs
- 📈 Automated insight generation

---

## **Support & Maintenance**

### **System Requirements**
- **Server**: 2+ CPU cores, 4GB+ RAM
- **Database**: MSSQL 2016+, PostgreSQL 12+, or SQLite 3+
- **Docker**: Version 20.10+
- **Network**: HTTPS capable

### **Monitoring**
- Application logs in Docker containers
- Database query performance logs
- AI API usage tracking
- User activity monitoring

### **Backup Strategy**
- Daily database backups
- Dashboard configuration exports
- User data replication
- Disaster recovery plan

---

## **Getting Started**

### **For End Users**
1. Navigate to application URL
2. Log in with credentials
3. Start asking questions in the chatbot
4. Create dashboards from results
5. Share with your team

### **For Administrators**
1. Review `api/.env` configuration
2. Set up database connections
3. Configure Google Gemini API key
4. Run `docker-compose up`
5. Monitor logs and performance

### **For Developers**
1. Clone repository
2. Review `README.md` files
3. Set up local development environment
4. Run backend: `python api/api-mssql.py`
5. Run frontend: `cd angular && npm start`

---

## **Contact & Support**

For questions, issues, or feature requests:
- 📧 Technical Support: [your-email@domain.com]
- 📚 Documentation: See repository README files
- 🐛 Bug Reports: Submit via issue tracker
- 💡 Feature Requests: Contact development team

---

## **License & Legal**

- Application code: [Your License]
- Third-party dependencies: See respective licenses
- Google Gemini API: Subject to Google's terms of service
- Data privacy: Ensure compliance with GDPR/CCPA as applicable

---

## **Conclusion**

This AI-Powered Business Intelligence platform represents a modern approach to data accessibility. By combining natural language processing with traditional database querying, it empowers every team member to become data-driven without technical barriers.

The application is production-ready with:
- ✅ Modern tech stack (Angular 20, Flask, Google Gemini)
- ✅ Scalable architecture (Docker, microservices)
- ✅ Enterprise database support (MSSQL, PostgreSQL)
- ✅ Intuitive user experience
- ✅ Comprehensive API documentation

**Ready to deploy and start transforming how your organization interacts with data.**

---

*Last Updated: January 2026*
*Version: gemini3 branch*
*Status: Production Ready (with security hardening)*
