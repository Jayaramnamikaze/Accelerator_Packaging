# Tableau to LookML Migration System - Code Architecture & Understanding

## **Project Overview**

A comprehensive Tableau workbook (.twb/.twbx) to LookML migration system with plugin architecture, supporting complete dashboard and worksheet conversion.

### **Key Directories**
```
src/tableau_to_looker_parser/
├── core/                    # Core orchestration components
├── handlers/                # Element-specific processors
├── generators/              # LookML file generators
├── converters/              # Formula parsing & chart detection
├── models/                  # Pydantic data schemas
└── templates/               # Jinja2 LookML templates

tests/                       # Comprehensive test suite
docs/                        # Architecture & implementation guides
sample_twb_files/            # Test workbooks with generated output
```

---

## **Core Architecture Components**

### **1. MigrationEngine** (`core/migration_engine.py`)
**Main orchestrator** - Manages entire conversion pipeline

```python
class MigrationEngine:
    def __init__(self, use_v2_parser: bool = True)  # v2 enables Phase 3
    def migrate_file(tableau_file, output_dir) -> Dict
```

**Processing Flow:**
1. **XML Parsing** (v2 parser for enhanced features)
2. **Handler Routing** (via PluginRegistry with priorities)
3. **JSON Generation** (structured intermediate format)
4. **Phase 3 Processing** (worksheets & dashboards if v2)
5. **Output Generation** (processed_pipeline_output.json)

**Handler Registration (Priority Order):**
```python
RelationshipHandler()     # Priority 1
ConnectionHandler()       # Priority 2
DimensionHandler()        # Priority 3
MeasureHandler()          # Priority 4
ParameterHandler()        # Priority 5
CalculatedFieldHandler()  # Priority 6
WorksheetHandler()        # Priority 7 (Phase 3)
DashboardHandler()        # Priority 8 (Phase 3)
```

### **2. XML Parsers**

#### **XMLParser v1** (`core/xml_parser.py`)
- Legacy parser for basic elements
- Connections, dimensions, measures, relationships

#### **XMLParser v2** (`core/xml_parser_v2.py`) ⭐ **Enhanced**
- **Metadata-first approach** with enhanced field coverage
- **Phase 3 support**: `extract_worksheets()`, `extract_dashboards()`
- **Layout detection**: newspaper, grid, free_form layouts
- **Position normalization**: 100k scale → 0-1 normalized coordinates
- **Field mapping**: Tableau names → LookML-safe names with labels

### **3. Plugin Registry** (`core/plugin_registry.py`)
**Handler routing system** with confidence-based selection

```python
class PluginRegistry:
    def register_handler(handler, priority)
    def get_handler(element) -> BaseHandler
    def get_handlers_by_priority() -> List[BaseHandler]
```

---

## **Handler System**

### **Base Handler** (`handlers/base_handler.py`)
**Abstract base class** for all element processors

```python
class BaseHandler:
    def can_handle(element_data) -> float      # Confidence 0.0-1.0
    def convert_to_json(element_data) -> Dict  # Transform to JSON
```

### **Core Handlers (Phase 1-2)**

#### **ConnectionHandler** (`handlers/connection_handler.py`)
- **Supports**: PostgreSQL, MySQL, SQL Server, Oracle, BigQuery, Snowflake
- **Extracts**: Server, database, credentials, SSL settings
- **Confidence**: 0.9 for supported DBs, 0.5 for unknown

#### **DimensionHandler** (`handlers/dimension_handler.py`)
- **Supports**: string, integer, real, boolean, date, datetime
- **Features**: Field name cleaning, hidden fields, captions
- **Date dimensions**: Timeframe generation for date fields

#### **MeasureHandler** (`handlers/measure_handler.py`)
- **Supports**: SUM, COUNT, AVG, MIN, MAX aggregations
- **Features**: Value formatting, drill-down capabilities
- **✅ Enhanced**: Two-step pattern generation (hidden dimension + measure)
- **✅ Multi-Aggregation**: Generates multiple measures per field (total_sales, avg_sales, count_quantity)

#### **CalculatedFieldHandler** (`handlers/calculated_field_handler.py`)
- **Coverage**: 48/150 Tableau functions (32% coverage)
- **Features**: AST parsing, formula conversion, dependency extraction
- **Supported**: IF-THEN-ELSE, LOD expressions, window functions, string/math/date functions

### **Phase 3 Handlers** ⭐

#### **WorksheetHandler** (`handlers/worksheet_handler.py`)
- **Processes**: Tableau worksheet elements
- **Features**: Field usage extraction, chart type detection, visualization config
- **Integration**: Enhanced chart type detector (91.3% confidence)
- **✅ Multi-Aggregation**: Identifies worksheet-specific field aggregations (AVG, COUNT, etc.)
- **✅ XML Parsing**: Extracts `<column-instance derivation='Avg'>` for precise aggregation detection
- **Output**: WorksheetSchema with field references and visualization metadata

#### **DashboardHandler** (`handlers/dashboard_handler.py`)
- **Processes**: Tableau dashboard elements
- **Features**: Zone processing, layout analysis, element positioning
- **Layout Types**: newspaper, grid, free_form detection
- **Output**: DashboardSchema with normalized positioning

---

## **Enhanced Chart Type Detection** (`converters/enhanced_chart_type_detector.py`)

**5-Tier Detection System:**
1. **Name-based Dual-Axis**: 92% confidence for dual-axis patterns
2. **Field Placement**: Real-world business chart patterns (90% confidence)
3. **Contextual Analysis**: Time series, correlation, comparison patterns
4. **Tableau Mark Mapping**: Fallback to XML mark classes
5. **Default Fallback**: Conservative defaults for edge cases

**Results**: 91.3% average confidence, 100% dual-axis detection success

**Supported Chart Types**: 20+ including bar_and_line, bar_and_area, time_series, scatter, etc.

---

## **Formula Processing System**

### **FormulaParser** (`converters/formula_parser.py`)
**3-Phase Pipeline**: Tokenization → Classification → AST Construction

#### **Phase 1: Tokenization**
- **Regex-based tokenization** with pattern priority order
- **Token Types**: STRING, FIELD_REF, INTEGER, REAL, IF/THEN/ELSE, IDENTIFIER, operators
- **Critical**: Container patterns first, specific before general, long before short

#### **Phase 2: Token Classification**
- **Categories**: Literals, References, Operators, Control Flow, Structure
- **Special Processing**: Quote removal, bracket extraction, case normalization

#### **Phase 3: AST Construction**
- **Recursive descent parsing** with precedence levels
- **Node Types**: LITERAL, FIELD_REF, CONDITIONAL, FUNCTION, ARITHMETIC, COMPARISON

### **Current Function Coverage** (Phase 2 Complete)
- **Conditional Logic**: 100% (IF-THEN-ELSE, CASE-WHEN)
- **LOD Expressions**: 90% (FIXED, INCLUDE, EXCLUDE)
- **Window Functions**: 100% (RUNNING_*, WINDOW_*, RANK, LAG/LEAD)
- **String Functions**: 93% (14/15 functions)
- **Math Functions**: 50% (6/12 functions)
- **Date Functions**: 33% (5/15 functions)

---

## **Data Models (Pydantic Schemas)**

### **Worksheet Models** (`models/worksheet_models.py`)
```python
class WorksheetSchema:
    name: str
    datasource_id: str
    field_usage: Dict[str, List[FieldReference]]
    visualization: VisualizationConfig
    sorting: List[SortConfig]
    filters: List[FilterConfig]

class FieldReference:
    name: str              # LookML-safe name
    original_name: str     # Tableau format [Field Name]
    tableau_instance: str  # [sum:Sales:qk]
    display_label: str     # User-friendly label
    datatype: str
    role: str             # dimension/measure
    shelf: str            # rows/columns/color/size
```

### **Dashboard Models** (`models/dashboard_models.py`)
```python
class DashboardSchema:
    name: str
    canvas_size: CanvasSize
    elements: List[DashboardElement]
    layout_type: str      # newspaper/grid/free_form
    responsive_config: Dict

class DashboardElement:
    element_id: str
    element_type: str     # worksheet/filter/parameter
    position: Position    # Normalized 0-1 coordinates
    worksheet_config: Optional[WorksheetConfig]
```

---

## **LookML Generation System**

### **LookMLGenerator** (`generators/lookml_generator.py`)
**Main coordinator** for all LookML file generation

```python
def generate_project_files(migration_data, output_dir) -> Dict:
    # Returns: {"views": [files], "model": file, "connection": file}
```

### **Specialized Generators**

#### **DashboardGenerator** (`generators/dashboard_generator.py`) ⭐
- **Position Translation**: Tableau 100k scale → LookML 24-column grid
- **Layout Optimization**: Per layout type (newspaper/grid/free_form)
- **Chart Type Mapping**: Tableau → Looker chart types
- **Dual-Axis Support**: Y_axes configuration with series colors
- **✅ Field Synchronization**: Perfect sync with view measures based on worksheet aggregations
- **✅ Dynamic Field Mapping**: AVG→avg_sales, SUM→total_sales, COUNT→count_quantity
- **Template**: dashboard.j2 (YAML format)

#### **ViewGenerator** (`generators/view_generator.py`)
- **Complete view files** with dimensions, measures, calculated fields
- **Field ordering** and grouping by type
- **User-friendly labels** from Tableau captions/names

#### **ModelGenerator** (`generators/model_generator.py`)
- **Explores and joins** from relationship data
- **Include statements** for view files
- **Connection references**

### **Template Engine** (`generators/template_engine.py`)
**Jinja2-based rendering** with custom filters

**Templates**:
- `connection.j2` - Database connection files
- `basic_view.j2` - View files with dimensions/measures
- `model.j2` - Model files with explores
- `dashboard.j2` - Dashboard files (YAML format) ⭐

---

## **🎯 Multi-Aggregation Support Architecture**

### **Problem Solved**
In Tableau, different worksheets can use different aggregations on the same field:
- Worksheet A: `SUM(Sales)`
- Worksheet B: `AVG(Sales)`
- Worksheet C: `COUNT(Quantity)`

LookML requires separate measures for each aggregation type.

### **Solution Flow**
```
XML Parser → WorksheetHandler → MeasureHandler → ViewGenerator
                ↓                    ↓
           identifies            generates         ↓
           AVG(Sales)           avg_sales      view.lkml
                ↓                    ↓
           DashboardHandler → DashboardGenerator
                ↓                    ↓
           references           orders.avg_sales
           worksheet fields     (perfect sync!)
```

### **Key Components**

#### **1. WorksheetHandler Enhancement**
```python
def _identify_worksheet_measures(self, fields, datasource_id):
    # Parses: <column-instance column='[Sales]' derivation='Avg'>
    # Returns: [{"name": "sales", "aggregation": "avg", ...}]
```

#### **2. MeasureHandler Routing**
```python
# Migration Engine routes identified measures
for measure_data in worksheet.identified_measures:
    json_data = measure_handler.convert_to_json(measure_data)
    # Generates: avg_sales, count_quantity, etc.
```

#### **3. Dashboard Field Mapping**
```python
def _add_measure_aggregation_type(self, field_name, field):
    if field.aggregation.lower() == "avg":
        return f"avg_{field_name.lower()}"  # avg_sales
    elif field.aggregation.lower() == "sum":
        return f"total_{field_name.lower()}"  # total_sales
```

### **Results**
```yaml
# View File (orders.view.lkml)
measure: total_sales { type: sum }     # Base SUM measure
measure: avg_sales { type: average }   # Worksheet-specific AVG
measure: count_quantity { type: count } # Worksheet-specific COUNT

# Dashboard File
fields: [orders.avg_sales, orders.category]  # Perfect sync!
```

---

## **Position Translation System**

### **Coordinate System Conversion**
```python
# Tableau (100,000 scale) → Normalized (0-1) → LookML (24-column grid)
normalized_x = tableau_x / 100000
lookml_col = int(normalized_x * 24)
lookml_width = max(1, int(normalized_width * 24))
```

### **Layout-Specific Optimizations**
- **free_form**: Minimal adjustments, preserve proportions
- **grid**: Snap to 3-column boundaries for alignment
- **newspaper**: Snap to 4-column boundaries for readability

---

## **Current Implementation Status**

### **✅ Phase 1-2 Complete**
- Core architecture with plugin system
- All basic handlers (connection, dimension, measure, calculated fields)
- Formula parsing with 48/150 functions (32% coverage)
- JSON intermediate format with validation

### **✅ Phase 3 Complete**
- Enhanced XML parser v2 with worksheet/dashboard extraction
- WorksheetHandler & DashboardHandler with 90%+ confidence
- Chart type detection (91.3% average confidence)
- Position translation system with layout optimization
- Dashboard generator with YAML template
- Complete LookML generation pipeline

### **Current Test Results**
- **Bar_charts.twb Processing**: 31 worksheets, 10 dashboards extracted
- **Field Coverage**: 16 dimensions, 4 measures, 3 calculated fields
- **Confidence Levels**: 90%+ for worksheets, 100% for dashboards
- **Generated Files**: Connection, view, model, dashboard LookML files

---

## **Testing Architecture**

### **Test Structure**
```
tests/
├── test_migration_engine_integration.py    # End-to-end pipeline
├── test_lookml_generator_book*.py          # LookML generation
├── test_worksheet_dashboard_handlers.py    # Phase 3 handlers
├── test_xml_parser_worksheets_dashboards.py # XML extraction
└── test_formula_conversion.py              # Calculated fields
```

### **Integration Testing**
- **Complete pipeline**: XML → JSON → LookML
- **File validation**: Syntax and structure checks
- **Field mapping**: Tableau → LookML name conversion
- **Position accuracy**: Layout translation validation

---

## **Next Steps: Looker Validation**

### **What's Needed**
1. **Syntax Validation**: Ensure generated LookML files are syntactically correct
2. **Looker Import Testing**: Import files into actual Looker instance
3. **Functionality Testing**: Verify explores, dashboards, connections work
4. **Visual Validation**: Check dashboard layouts render properly
5. **Performance Testing**: Query execution and dashboard loading

### **Generated File Structure**
```
output/
├── connection.lkml          # Database connections
├── model.lkml              # Explores and joins
├── views/
│   └── orders.view.lkml    # Dimensions and measures
└── dashboards/
    ├── bar_chart_analytics.dashboard.lkml
    └── [other_dashboards].dashboard.lkml
```

---

## **Key Implementation Files Reference**

### **Core Files**
- `core/migration_engine.py` - Main orchestrator
- `core/xml_parser_v2.py` - Enhanced XML parser
- `core/plugin_registry.py` - Handler routing

### **Phase 3 Implementation**
- `handlers/worksheet_handler.py` - Worksheet processing
- `handlers/dashboard_handler.py` - Dashboard processing
- `generators/dashboard_generator.py` - Dashboard LookML generation
- `converters/enhanced_chart_type_detector.py` - Chart detection

### **Data Models**
- `models/worksheet_models.py` - Worksheet schemas
- `models/dashboard_models.py` - Dashboard schemas
- `models/migration_models.py` - Migration result structure

### **Documentation**
- `docs/CODE_ARCHITECTURE.md` - Complete architecture guide
- `docs/TABLEAU_TO_LOOKML_POSITIONING_GUIDE.md` - Position translation
- `docs/TOKENIZATION_AND_PARSING.md` - Formula processing
- `docs/CHART_TYPE_IDENTIFICATION.md` - Chart detection strategy

---

**Status**: Phase 3 implementation complete, ready for Looker validation testing.
