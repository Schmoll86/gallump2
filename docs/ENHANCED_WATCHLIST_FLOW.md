# Enhanced Watchlist System Architecture

## Data Flow Diagram

```mermaid
graph TD
    subgraph "Frontend"
        UI[EnhancedWatchlist Component]
        Store[Zustand Store]
        API_Service[API Service]
    end
    
    subgraph "Backend API"
        Routes[API Routes]
        Storage[Storage Layer]
        Context[Context Builder]
        Prompt[Prompt Builder]
    end
    
    subgraph "Database"
        DB[(SQLite DB)]
        WL[Watchlist Table]
    end
    
    subgraph "AI Processing"
        Brain[Brain/Claude]
        MCP[MCP Analytics]
    end
    
    %% User interactions
    UI -->|Add Symbol| Store
    UI -->|Set Primary| Store
    UI -->|Update Thesis| Store
    UI -->|Set Category| Store
    
    %% Store to API
    Store -->|Sync| API_Service
    API_Service -->|POST /api/watchlist/sync| Routes
    API_Service -->|PATCH /api/watchlist/:symbol| Routes
    
    %% Backend processing
    Routes -->|Save| Storage
    Storage -->|SQL| DB
    DB -->|Enhanced Fields| WL
    
    %% Context flow
    Routes -->|Get Watchlist| Storage
    Storage -->|Enhanced Data| Context
    Context -->|Smart Extraction| Prompt
    
    %% AI integration
    Prompt -->|With Metadata| Brain
    Context -->|Prioritized Data| MCP
    
    %% Response flow
    Brain -->|Recommendations| Routes
    MCP -->|Analysis| Routes
    Routes -->|Enhanced Response| API_Service
    API_Service -->|Update| Store
    Store -->|Render| UI
```

## Enhanced Watchlist Data Structure

```mermaid
classDiagram
    class WatchlistItem {
        +String symbol
        +String thesis
        +Boolean is_primary
        +String category
        +DateTime added_at
        +DateTime last_discussed
        +to_dict() Dict
    }
    
    class WatchlistCategory {
        <<enumeration>>
        LONG
        SHORT
        VOLATILE
    }
    
    class Watchlist {
        +List~WatchlistItem~ items
        +String format
        +String primary_symbol
        +to_dict() Dict
    }
    
    class Context {
        +String symbol
        +List watchlist
        +Dict watchlist_metadata
        +String primary_symbol
    }
    
    WatchlistItem --> WatchlistCategory : uses
    Watchlist --> WatchlistItem : contains
    Context --> Watchlist : includes
```

## Smart Symbol Extraction Flow

```mermaid
flowchart LR
    Input[User Message] --> Extract[extract_symbol_from_thesis]
    Extract --> Check1{Direct Mention?}
    Check1 -->|Yes +100pts| Score[Scoring System]
    Check1 -->|No| Check2{Category Match?}
    Check2 -->|Yes +40pts| Score
    Check2 -->|No| Check3{Thesis Match?}
    Check3 -->|Yes +30pts×words| Score
    Check3 -->|No| Check4{Is Primary?}
    Check4 -->|Yes +10pts| Score
    Check4 -->|No| Pattern[Pattern Match]
    
    Score --> Best[Select Highest Score]
    Pattern --> Best
    Best --> Symbol[Selected Symbol]
    
    style Score fill:#f9f,stroke:#333,stroke-width:2px
    style Best fill:#9f9,stroke:#333,stroke-width:2px
```

## Category-Based Prioritization

```mermaid
graph TD
    Symbol[Symbol Data] --> Category{Category?}
    
    Category -->|Long| Long_Priority[Standard Priority]
    Category -->|Short| Short_Priority[High Priority]
    Category -->|Volatile| Vol_Priority[Critical Priority]
    
    Long_Priority --> Long_Data[Support Levels<br/>Bullish Patterns<br/>Call Options]
    Short_Priority --> Short_Data[Resistance<br/>Bearish Signals<br/>Put Options<br/>Borrow Rates]
    Vol_Priority --> Vol_Data[Options Flow<br/>IV Rank<br/>Greeks<br/>Straddle Prices]
    
    Long_Data --> Context[Context Package]
    Short_Data --> Context
    Vol_Data --> Context
    
    Context --> MCP[MCP Analytics]
    Context --> Brain[Claude AI]
    
    style Short_Priority fill:#f99,stroke:#333,stroke-width:2px
    style Vol_Priority fill:#ff9,stroke:#333,stroke-width:2px
    style Long_Priority fill:#9f9,stroke:#333,stroke-width:2px
```

## API Endpoint Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Storage
    participant Context
    participant Claude
    
    User->>Frontend: Update watchlist item
    Frontend->>API: PATCH /api/watchlist/AAPL
    Note right of API: {"thesis": "Bounce play",<br/>"is_primary": true,<br/>"category": "Long"}
    
    API->>Storage: update_watchlist_item()
    Storage->>Storage: ALTER watchlist SET...
    Storage-->>API: Success
    
    API-->>Frontend: Updated item
    Frontend->>Frontend: Update UI
    
    User->>Frontend: Send chat message
    Frontend->>API: POST /api/strategies/generate
    Note right of API: {"prompt": "Looking for bounce",<br/>"watchlist": [...enhanced...]}
    
    API->>Storage: get_enhanced_watchlist()
    Storage-->>API: Enhanced watchlist
    
    API->>Context: build(watchlist, prompt)
    Context->>Context: extract_symbol_from_thesis()
    Note right of Context: Smart scoring:<br/>- Thesis match: 60pts<br/>- Primary: 10pts<br/>→ Select AAPL
    
    Context-->>API: Context with AAPL focus
    API->>Claude: Analyze with context
    Claude-->>API: Recommendations
    API-->>Frontend: Response with AAPL strategies
```

## Backward Compatibility

```mermaid
graph LR
    Input[API Request] --> Check{Format?}
    
    Check -->|Array| Simple[Simple Format]
    Check -->|Objects| Enhanced[Enhanced Format]
    
    Simple --> Convert[Convert to Basic]
    Enhanced --> Process[Process Metadata]
    
    Convert --> Handler[Unified Handler]
    Process --> Handler
    
    Handler --> Response[API Response]
    
    style Check fill:#ff9,stroke:#333,stroke-width:2px
    style Handler fill:#9f9,stroke:#333,stroke-width:2px
```