# Chart Type Implementation Pattern

## Real-World Chart Definition Patterns

Based on standard data visualization principles and how analysts actually build charts, here are the field placement patterns that define different chart types:

### 📊 **Universal Chart Definition Rules**

#### **Bar Charts**
```python
# Vertical Bar Chart (most common)
ROWS: categorical_dimension(s)     # What to group by
COLUMNS: measure(s)                # What to measure
COLOR: (optional) categorical_dimension  # How to break down further

# Horizontal Bar Chart
ROWS: measure(s)                   # What to measure
COLUMNS: categorical_dimension(s)  # What to group by
```

#### **Line Charts**
```python
# Time Series (most common line chart pattern)
ROWS: measure(s)                   # What to track over time
COLUMNS: date_dimension            # Time progression
COLOR: (optional) categorical_dimension  # Multiple series

# Trend Analysis
ROWS: measure
COLUMNS: continuous_dimension      # Any ordered dimension
```

#### **Scatter Plots**
```python
# Correlation Analysis
ROWS: measure_1                    # Y-axis metric
COLUMNS: measure_2                 # X-axis metric
COLOR: (optional) categorical_dimension  # Point grouping
SIZE: (optional) measure_3         # Bubble size
```

#### **Pie Charts**
```python
# Part-to-Whole Analysis
ROWS: (empty)
COLUMNS: (empty)
COLOR: categorical_dimension       # Pie slices
ANGLE: measure                     # Slice sizes (usually implicit)
```

#### **Heatmaps**
```python
# 2D Categorical Analysis
ROWS: categorical_dimension_1      # Y-axis categories
COLUMNS: categorical_dimension_2   # X-axis categories
COLOR: measure                     # Heat intensity
```

#### **Text Tables**
```python
# Detailed Data View
ROWS: categorical_dimension(s)     # Row grouping
COLUMNS: categorical_dimension(s) OR measure(s)  # Column data
TEXT: measure(s)                   # Cell values
```

## Implementation Strategy with Confidence Scoring

### **Tier 1: Direct Pattern Matching (Confidence: 0.90-0.95)**

```python
class ChartTypeDetector:
    def __init__(self):
        self.real_world_patterns = {
            # Bar chart patterns (most common in business)
            'vertical_bar': {
                'rows': ['dimension'],
                'columns': ['measure'],
                'confidence': 0.95,
                'indicators': ['categorical_on_rows', 'quantitative_on_columns']
            },
            'horizontal_bar': {
                'rows': ['measure'],
                'columns': ['dimension'],
                'confidence': 0.95,
                'indicators': ['quantitative_on_rows', 'categorical_on_columns']
            },
            'grouped_bar': {
                'rows': ['dimension'],
                'columns': ['measure'],
                'color': ['dimension'],
                'confidence': 0.93,
                'indicators': ['multiple_series_by_color']
            },

            # Line chart patterns (time series focus)
            'time_series': {
                'rows': ['measure'],
                'columns': ['date'],
                'confidence': 0.95,
                'indicators': ['date_on_axis', 'measure_trending']
            },
            'multi_line': {
                'rows': ['measure'],
                'columns': ['date'],
                'color': ['dimension'],
                'confidence': 0.93,
                'indicators': ['date_on_axis', 'multiple_series']
            },

            # Scatter plot patterns
            'scatter': {
                'rows': ['measure'],
                'columns': ['measure'],
                'confidence': 0.90,
                'indicators': ['measure_vs_measure', 'correlation_analysis']
            },
            'bubble': {
                'rows': ['measure'],
                'columns': ['measure'],
                'size': ['measure'],
                'confidence': 0.92,
                'indicators': ['three_measures', 'size_encoding']
            },

            # Pie chart patterns
            'pie': {
                'rows': [],
                'columns': [],
                'color': ['dimension'],
                'confidence': 0.85,
                'indicators': ['part_to_whole', 'categorical_breakdown']
            },

            # Heatmap patterns
            'heatmap': {
                'rows': ['dimension'],
                'columns': ['dimension'],
                'color': ['measure'],
                'confidence': 0.88,
                'indicators': ['categorical_grid', 'measure_intensity']
            },

            # Text table patterns
            'text_table': {
                'rows': ['dimension'],
                'columns': ['dimension', 'measure'],
                'confidence': 0.85,
                'indicators': ['detailed_breakdown', 'multiple_columns']
            }
        }

    def detect_by_field_placement(self, worksheet_data):
        """
        Tier 1: Real-world pattern matching with high confidence
        """
        fields = worksheet_data.get('fields', [])

        # Analyze field placement
        placement = self._analyze_field_placement(fields)

        # Match against real-world patterns
        for chart_type, pattern in self.real_world_patterns.items():
            if self._matches_pattern(placement, pattern):
                return {
                    'chart_type': chart_type,
                    'confidence': pattern['confidence'],
                    'method': 'field_placement_pattern',
                    'reasoning': f"Matches {chart_type} pattern: {pattern['indicators']}"
                }

        return None

    def _analyze_field_placement(self, fields):
        """
        Analyze how fields are placed on different shelves
        """
        placement = {
            'rows': {'dimensions': [], 'measures': [], 'dates': []},
            'columns': {'dimensions': [], 'measures': [], 'dates': []},
            'color': {'dimensions': [], 'measures': []},
            'size': {'dimensions': [], 'measures': []},
            'detail': {'dimensions': [], 'measures': []}
        }

        for field in fields:
            shelf = field.get('shelf', 'unknown')
            role = field.get('role', 'unknown')
            datatype = field.get('datatype', 'unknown')
            name = field.get('name', '').lower()

            if shelf in placement:
                if datatype in ['date', 'datetime']:
                    placement[shelf]['dates'].append(field)
                elif role == 'dimension':
                    placement[shelf]['dimensions'].append(field)
                elif role == 'measure':
                    placement[shelf]['measures'].append(field)

        return placement

    def _matches_pattern(self, placement, pattern):
        """
        Check if field placement matches a real-world pattern
        """
        for shelf, expected_types in pattern.items():
            if shelf in ['confidence', 'indicators']:
                continue

            actual = placement.get(shelf, {})

            for expected_type in expected_types:
                if expected_type == 'dimension' and not actual.get('dimensions'):
                    return False
                elif expected_type == 'measure' and not actual.get('measures'):
                    return False
                elif expected_type == 'date' and not actual.get('dates'):
                    return False

        return True
```

### **Tier 2: Contextual Analysis (Confidence: 0.70-0.85)**

```python
def detect_by_context(self, worksheet_data):
    """
    Tier 2: Business context and field relationships
    """
    fields = worksheet_data.get('fields', [])
    viz_config = worksheet_data.get('visualization', {})

    # Business context indicators
    context_score = 0
    chart_hints = []

    # Time series indicators (very common in business)
    if self._has_time_dimension(fields):
        if self._has_trending_measure(fields):
            chart_hints.append(('line', 0.80, 'time_series_pattern'))
            context_score += 0.2

    # Comparison indicators
    if self._has_categorical_breakdown(fields):
        if self._has_multiple_measures(fields):
            chart_hints.append(('grouped_bar', 0.75, 'comparison_analysis'))
        else:
            chart_hints.append(('bar', 0.78, 'categorical_comparison'))
        context_score += 0.15

    # Correlation indicators
    if self._has_multiple_measures_on_axes(fields):
        chart_hints.append(('scatter', 0.82, 'correlation_analysis'))
        context_score += 0.25

    # Distribution indicators
    if self._has_single_measure_breakdown(fields):
        chart_hints.append(('pie', 0.70, 'distribution_analysis'))
        context_score += 0.1

    # Return highest confidence hint
    if chart_hints:
        best_hint = max(chart_hints, key=lambda x: x[1])
        return {
            'chart_type': best_hint[0],
            'confidence': best_hint[1] * (1 + context_score),
            'method': 'contextual_analysis',
            'reasoning': best_hint[2]
        }

    return None

def _has_time_dimension(self, fields):
    """Check if worksheet has time-based analysis"""
    return any(f['datatype'] in ['date', 'datetime'] and
              f['shelf'] in ['rows', 'columns']
              for f in fields)

def _has_trending_measure(self, fields):
    """Check if measures are positioned for trending"""
    return any(f['role'] == 'measure' and
              f['shelf'] in ['rows', 'columns']
              for f in fields)

def _has_categorical_breakdown(self, fields):
    """Check for categorical analysis pattern"""
    cat_dims = [f for f in fields if f['role'] == 'dimension' and
                f['datatype'] == 'string']
    return len(cat_dims) >= 1

def _has_multiple_measures(self, fields):
    """Check for multi-measure analysis"""
    measures = [f for f in fields if f['role'] == 'measure']
    return len(measures) >= 2

def _has_multiple_measures_on_axes(self, fields):
    """Check for measure vs measure analysis"""
    axis_measures = [f for f in fields if f['role'] == 'measure' and
                    f['shelf'] in ['rows', 'columns']]
    return len(axis_measures) >= 2
```

### **Tier 3: Tableau Mark Analysis (Confidence: 0.60-0.80)**

```python
def detect_by_tableau_marks(self, worksheet_data):
    """
    Tier 3: Tableau-specific mark analysis
    """
    viz_config = worksheet_data.get('visualization', {})
    raw_config = viz_config.get('raw_config', {})

    # Direct mark mapping
    tableau_marks = {
        'Bar': ('bar', 0.80),
        'Line': ('line', 0.75),
        'Area': ('area', 0.75),
        'Circle': ('scatter', 0.70),
        'Square': ('heatmap', 0.65),
        'Pie': ('pie', 0.70),
        'Text': ('text_table', 0.75),
        'GanttBar': ('gantt', 0.65),
        'Polygon': ('map', 0.60)
    }

    # Check for dual axis
    if viz_config.get('is_dual_axis'):
        primary_mark = raw_config.get('primary_mark', 'Bar')
        secondary_mark = raw_config.get('secondary_mark', 'Bar')

        if primary_mark != secondary_mark:
            primary_type = tableau_marks.get(primary_mark, ('unknown', 0))[0]
            secondary_type = tableau_marks.get(secondary_mark, ('unknown', 0))[0]

            return {
                'chart_type': f"{primary_type}_and_{secondary_type}",
                'confidence': 0.75,
                'method': 'dual_axis_detection',
                'is_dual_axis': True,
                'primary_type': primary_type,
                'secondary_type': secondary_type
            }

    # Single mark type
    chart_type = viz_config.get('chart_type', 'unknown')
    if chart_type in tableau_marks:
        mapped_type, confidence = tableau_marks[chart_type]
        return {
            'chart_type': mapped_type,
            'confidence': confidence,
            'method': 'tableau_mark_mapping'
        }

    return None
```

### **Tier 4: Gemini AI Fallback (Confidence: 0.40-0.70)**

```python
def detect_by_ai_fallback(self, worksheet_data):
    """
    Tier 4: Gemini AI analysis for complex/unknown cases
    """
    try:
        # Prepare context for Gemini
        context = self._prepare_ai_context(worksheet_data)

        # Call Gemini API
        prompt = f"""
        Analyze this Tableau worksheet configuration and determine the most likely chart type.

        Worksheet: {worksheet_data.get('name', 'Unknown')}

        Field Configuration:
        {context['field_summary']}

        Visualization Settings:
        {context['viz_summary']}

        Based on standard data visualization best practices, what chart type is this most likely to be?

        Respond with JSON:
        {{
            "chart_type": "bar|line|scatter|pie|heatmap|text_table|area",
            "confidence": 0.0-1.0,
            "reasoning": "explanation of why this chart type fits the data pattern",
            "variants": ["optional", "chart", "variants"]
        }}
        """

        response = self._call_gemini_api(prompt)

        if response and response.get('chart_type'):
            return {
                'chart_type': response['chart_type'],
                'confidence': min(response.get('confidence', 0.5), 0.70),  # Cap AI confidence
                'method': 'ai_analysis',
                'reasoning': response.get('reasoning', 'AI analysis'),
                'variants': response.get('variants', []),
                'ai_provider': 'gemini'
            }

    except Exception as e:
        self.logger.warning(f"AI fallback failed: {e}")

    return None

def _prepare_ai_context(self, worksheet_data):
    """Prepare structured context for AI analysis"""
    fields = worksheet_data.get('fields', [])
    viz = worksheet_data.get('visualization', {})

    # Field summary
    field_summary = []
    for field in fields:
        field_summary.append(f"- {field['name']} ({field['role']}, {field['datatype']}) on {field['shelf']}")

    # Visualization summary
    viz_summary = {
        'chart_type': viz.get('chart_type', 'unknown'),
        'is_dual_axis': viz.get('is_dual_axis', False),
        'x_axis_fields': len(viz.get('x_axis', [])),
        'y_axis_fields': len(viz.get('y_axis', [])),
        'has_color_encoding': bool(viz.get('color')),
        'has_size_encoding': bool(viz.get('size'))
    }

    return {
        'field_summary': '\n'.join(field_summary),
        'viz_summary': json.dumps(viz_summary, indent=2)
    }

def _call_gemini_api(self, prompt):
    """Call Gemini API with proper error handling"""
    import google.generativeai as genai

    try:
        # Configure Gemini (API key from environment)
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-pro')

        response = model.generate_content(prompt)

        # Parse JSON response
        import json
        return json.loads(response.text)

    except Exception as e:
        self.logger.error(f"Gemini API call failed: {e}")
        return None
```

### **Tier 5: Default Fallback (Confidence: 0.30-0.50)**

```python
def detect_by_default_rules(self, worksheet_data):
    """
    Tier 5: Conservative fallback based on most common patterns
    """
    fields = worksheet_data.get('fields', [])

    # Default business chart hierarchy (based on real usage)
    dimensions = [f for f in fields if f['role'] == 'dimension']
    measures = [f for f in fields if f['role'] == 'measure']

    # Most common case: categorical comparison
    if dimensions and measures:
        return {
            'chart_type': 'bar',
            'confidence': 0.45,
            'method': 'default_fallback',
            'reasoning': 'Default to bar chart for categorical + measure data'
        }

    # Only measures: likely trend analysis
    if measures and not dimensions:
        return {
            'chart_type': 'line',
            'confidence': 0.40,
            'method': 'default_fallback',
            'reasoning': 'Default to line chart for measure-only data'
        }

    # Only dimensions: likely text table
    if dimensions and not measures:
        return {
            'chart_type': 'text_table',
            'confidence': 0.35,
            'method': 'default_fallback',
            'reasoning': 'Default to text table for dimension-only data'
        }

    # Ultimate fallback
    return {
        'chart_type': 'bar',
        'confidence': 0.30,
        'method': 'ultimate_fallback',
        'reasoning': 'Bar chart is most common business visualization'
    }
```

## **Complete Detection Pipeline**

```python
class EnhancedChartTypeDetector:
    def __init__(self, enable_ai_fallback=True):
        self.enable_ai_fallback = enable_ai_fallback
        self.confidence_threshold = 0.60  # Minimum acceptable confidence

    def detect_chart_type(self, worksheet_data):
        """
        Main detection pipeline with tiered approach
        """
        # Tier 1: Real-world field placement patterns (90-95% confidence)
        result = self.detect_by_field_placement(worksheet_data)
        if result and result['confidence'] >= 0.85:
            return result

        # Tier 2: Business context analysis (70-85% confidence)
        result = self.detect_by_context(worksheet_data)
        if result and result['confidence'] >= 0.70:
            return result

        # Tier 3: Tableau mark analysis (60-80% confidence)
        result = self.detect_by_tableau_marks(worksheet_data)
        if result and result['confidence'] >= 0.60:
            return result

        # Tier 4: AI fallback (40-70% confidence)
        if self.enable_ai_fallback:
            result = self.detect_by_ai_fallback(worksheet_data)
            if result and result['confidence'] >= 0.40:
                return result

        # Tier 5: Default fallback (30-50% confidence)
        return self.detect_by_default_rules(worksheet_data)

    def get_detection_summary(self, worksheets):
        """
        Analyze detection quality across multiple worksheets
        """
        results = []
        confidence_distribution = {'high': 0, 'medium': 0, 'low': 0}
        method_usage = {}

        for ws in worksheets:
            result = self.detect_chart_type(ws)
            results.append(result)

            # Track confidence distribution
            if result['confidence'] >= 0.80:
                confidence_distribution['high'] += 1
            elif result['confidence'] >= 0.60:
                confidence_distribution['medium'] += 1
            else:
                confidence_distribution['low'] += 1

            # Track method usage
            method = result['method']
            method_usage[method] = method_usage.get(method, 0) + 1

        return {
            'total_worksheets': len(worksheets),
            'results': results,
            'confidence_distribution': confidence_distribution,
            'method_usage': method_usage,
            'average_confidence': sum(r['confidence'] for r in results) / len(results)
        }
```

This implementation pattern provides:

1. **Real-World Accuracy**: Based on how analysts actually build charts
2. **Field Placement Intelligence**: Considers rows/columns/color/size placement
3. **Confidence-Based Fallbacks**: Clear tier system with Gemini AI backup
4. **Business Context**: Understands time series, comparisons, correlations
5. **Comprehensive Coverage**: Handles edge cases and unknown patterns

Would you like me to implement this detection system now, or would you prefer to see specific examples with the Bar_charts.twb data first?
