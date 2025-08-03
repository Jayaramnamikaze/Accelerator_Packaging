# Chart Type Identification Strategy

## Overview

This document outlines the comprehensive strategy for accurately identifying Tableau chart types during the migration to LookML. Tableau's chart type detection is complex because it often uses "Automatic" marks, and the actual visualization depends on multiple factors including encodings, field types, and dual-axis configurations.

## Current Problem Analysis

### Issues with Basic Detection
- **Limited Accuracy**: Current system only detects "bar" (83.9%) and "unknown" (16.1%)
- **Missing Dual-Axis Context**: Not considering secondary pane mark types
- **No Encoding Analysis**: Missing size, shape, detail encodings that affect chart appearance
- **No Field Context**: Not using field types/shelf positions for intelligent inference

### Tableau Mark Classes Found in Bar_charts.twb
```
38 × Bar          - Standard bar charts
5 × Automatic     - Needs inference
1 × Area          - Area charts
1 × Circle        - Scatter plots
1 × GanttBar      - Gantt charts
1 × Heatmap       - Heatmaps (Square marks)
1 × Line          - Line charts
1 × Pie           - Pie charts
1 × Polygon       - Map visualizations
1 × Shape         - Symbol charts
1 × Square        - Heatmaps
1 × Text          - Text tables
```

## Multi-Layer Detection Strategy

### Layer 1: Direct Mark Class Detection

**Primary Mark Type Mapping:**
```python
TABLEAU_MARK_MAPPING = {
    'Bar': 'bar',
    'Line': 'line',
    'Area': 'area',
    'Circle': 'scatter',
    'Square': 'heatmap',
    'Pie': 'pie',
    'Text': 'text',
    'GanttBar': 'gantt',
    'Polygon': 'map',
    'Shape': 'symbol',
    'Automatic': 'auto'  # Requires Layer 3 inference
}
```

**Confidence Levels:**
- Direct mark class match: 0.95
- Inferred from encodings: 0.80
- Field-based inference: 0.65

### Layer 2: Dual-Axis Chart Detection

**Dual-Axis Pattern Recognition:**
```python
def detect_dual_axis_type(panes):
    """
    Handle dual-axis charts like "Bar_in_area_dual_axis"
    """
    if len(panes) >= 2:
        primary_mark = panes[0].get('mark_class', 'Bar')
        secondary_mark = panes[1].get('mark_class', 'Bar')

        if primary_mark != secondary_mark:
            primary_type = TABLEAU_MARK_MAPPING.get(primary_mark, 'unknown')
            secondary_type = TABLEAU_MARK_MAPPING.get(secondary_mark, 'unknown')

            return {
                'chart_type': f"{primary_type}_and_{secondary_type}",
                'is_dual_axis': True,
                'primary_type': primary_type,
                'secondary_type': secondary_type,
                'confidence': 0.90
            }

    return None
```

**Expected Dual-Axis Detections:**
| Worksheet Name | Primary Mark | Secondary Mark | Result |
|----------------|--------------|----------------|--------|
| `Bar_in_area_dual_axis` | Bar | Area | `bar_and_area` |
| `Bar_in_pie_dual_axis` | Bar | Pie | `bar_and_pie` |
| `Bar_in_circle_dual_axis` | Bar | Circle | `bar_and_scatter` |
| `Bar_in_line_dual_axis` | Bar | Line | `bar_and_line` |

### Layer 3: Encoding-Based Inference

**For "Automatic" Mark Types:**
```python
def infer_from_encodings(encodings, field_usage):
    """
    Infer chart type when mark class is "Automatic"
    """

    # Pie chart indicators
    if (has_angle_encoding(encodings) or
        (has_color_by_dimension(encodings) and single_measure_on_shelf(field_usage))):
        return 'pie'

    # Scatter plot indicators
    if (has_size_encoding(encodings) or
        has_both_measures_on_axes(field_usage)):
        return 'scatter'

    # Heatmap indicators
    if (has_dense_categorical_grid(field_usage) and
        has_color_by_measure(encodings)):
        return 'heatmap'

    # Line chart indicators
    if (has_date_dimension_on_axis(field_usage) and
        single_measure_trend_pattern(field_usage)):
        return 'line'

    # Text table indicators
    if has_only_text_encodings(encodings):
        return 'text'

    # Default fallback
    return 'bar'
```

### Layer 4: Field Configuration Analysis

**Field Pattern Detection:**
```python
def analyze_field_context(field_usage):
    """
    Analyze field patterns to support chart type inference
    """
    dimensions = [f for f in field_usage if f['role'] == 'dimension']
    measures = [f for f in field_usage if f['role'] == 'measure']

    patterns = {
        # Temporal patterns
        'has_date_dimension': any(f['datatype'] in ['date', 'datetime'] for f in dimensions),
        'date_on_columns': any(f['shelf'] == 'columns' and f['datatype'] in ['date', 'datetime'] for f in dimensions),

        # Geographic patterns
        'has_geography': any(geo_keyword in f['name'].lower()
                           for f in dimensions
                           for geo_keyword in ['country', 'state', 'city', 'latitude', 'longitude']),

        # Measure patterns
        'single_measure': len(measures) == 1,
        'multiple_measures': len(measures) > 1,
        'measures_on_same_shelf': len(set(m['shelf'] for m in measures)) == 1,

        # Dimension patterns
        'high_cardinality_dim': any(f.get('estimated_cardinality', 0) > 100 for f in dimensions),
        'categorical_grid': len([d for d in dimensions if d['shelf'] in ['rows', 'columns']]) >= 2,

        # Shelf patterns
        'empty_shelves': len([f for f in field_usage if f['shelf'] in ['rows', 'columns']]) == 0
    }

    return patterns
```

### Layer 5: Chart Variant Detection

**Detailed Variant Analysis:**
```python
def detect_chart_variants(base_type, encodings, field_context, style_config):
    """
    Detect specific chart variants and styling
    """
    variants = []

    if base_type == 'pie':
        # Donut vs Standard Pie
        if has_inner_radius_setting(style_config):
            variants.append('donut')
        else:
            variants.append('standard')

        # Single vs Multi-level
        if multiple_categorical_dimensions(field_context):
            variants.append('nested')

    elif base_type == 'bar':
        # Stacking behavior
        if has_color_by_dimension(encodings):
            stack_type = detect_stack_type(encodings, style_config)
            variants.append(stack_type)  # 'stacked', 'grouped', 'percent_stacked'
        else:
            variants.append('single_series')

        # Orientation
        orientation = detect_bar_orientation(field_context)
        variants.append(orientation)  # 'horizontal', 'vertical'

        # Special bar types
        if field_context.get('has_date_dimension'):
            variants.append('timeline')

    elif base_type == 'line':
        # Series count
        if has_color_by_dimension(encodings):
            variants.append('multi_series')
        else:
            variants.append('single_series')

        # Line style
        line_style = detect_line_style(style_config)
        variants.append(line_style)  # 'smooth', 'step', 'straight'

        # Area fill
        if has_area_fill(style_config):
            variants.append('area_filled')

    elif base_type == 'scatter':
        # Bubble chart detection
        if has_size_encoding(encodings):
            variants.append('bubble')

        # Trend line detection
        if has_trend_line(style_config):
            variants.append('with_trendline')

    return variants
```

## Implementation Architecture

### Enhanced Chart Type Detector Class

```python
class EnhancedChartTypeDetector:
    """
    Multi-layer chart type detection system
    """

    def __init__(self):
        self.mark_mapping = TABLEAU_MARK_MAPPING
        self.confidence_thresholds = {
            'high': 0.85,
            'medium': 0.65,
            'low': 0.45
        }

    def detect_chart_type(self, worksheet_data):
        """
        Main detection method using all layers
        """
        result = {
            'chart_type': 'unknown',
            'variants': [],
            'confidence': 0.0,
            'detection_method': 'unknown',
            'is_dual_axis': False
        }

        # Layer 1: Direct mark detection
        direct_result = self._detect_from_marks(worksheet_data)
        if direct_result['confidence'] >= self.confidence_thresholds['high']:
            return direct_result

        # Layer 2: Dual-axis detection
        dual_result = self._detect_dual_axis(worksheet_data)
        if dual_result and dual_result['confidence'] >= self.confidence_thresholds['high']:
            return dual_result

        # Layer 3: Encoding inference
        encoding_result = self._infer_from_encodings(worksheet_data)
        if encoding_result['confidence'] >= self.confidence_thresholds['medium']:
            return encoding_result

        # Layer 4: Field context fallback
        field_result = self._infer_from_fields(worksheet_data)
        return field_result

    def _detect_from_marks(self, worksheet_data):
        # Implementation for Layer 1
        pass

    def _detect_dual_axis(self, worksheet_data):
        # Implementation for Layer 2
        pass

    def _infer_from_encodings(self, worksheet_data):
        # Implementation for Layer 3
        pass

    def _infer_from_fields(self, worksheet_data):
        # Implementation for Layer 4
        pass
```

## Expected Chart Type Results

### Bar_charts.twb Analysis

| Current Detection | Expected Enhanced | Confidence | Method |
|------------------|-------------------|------------|---------|
| bar (26) | bar_variants (20) | 0.95 | Direct mark |
| unknown (5) | mixed_types (5) | 0.80 | Encoding inference |
| | dual_axis_combinations (6) | 0.90 | Dual-axis detection |

### Specific Worksheet Predictions

| Worksheet Name | Expected Chart Type | Variants | Confidence |
|----------------|-------------------|----------|------------|
| `Bar_in_area_dual_axis` | `bar_and_area` | `[dual_axis, vertical]` | 0.95 |
| `Bar_with_clusters` | `bar` | `[grouped, horizontal]` | 0.90 |
| `Simple_bar_with_single_dimension` | `bar` | `[single_series, vertical]` | 0.95 |
| `Median_with_quartile_table` | `text` | `[statistics_table]` | 0.85 |
| `Bar_with_totals` | `bar` | `[with_totals, vertical]` | 0.90 |

## LookML Chart Type Mapping

### Dashboard Element Types
```python
LOOKML_CHART_MAPPING = {
    # Basic types
    'bar': 'looker_column',
    'line': 'looker_line',
    'area': 'looker_area',
    'pie': 'looker_pie',
    'scatter': 'looker_scatterplot',
    'text': 'looker_table',
    'heatmap': 'looker_heatmap',

    # Dual-axis combinations
    'bar_and_line': 'looker_combo',
    'bar_and_area': 'looker_combo',

    # Variants
    'bar_horizontal': 'looker_bar',
    'donut': 'looker_donut',
    'bubble': 'looker_scatterplot'  # with size dimension
}
```

## Performance Considerations

### Optimization Strategies
1. **Lazy Evaluation**: Only run expensive analysis when confidence is low
2. **Caching**: Cache field analysis results for reuse
3. **Early Exit**: Return immediately on high-confidence direct matches
4. **Parallel Processing**: Analyze multiple worksheets concurrently

### Memory Efficiency
- Use generators for large worksheet collections
- Store only essential detection metadata
- Clean up temporary analysis objects

## Testing Strategy

### Unit Tests
- Each detection layer independently
- Edge cases (empty worksheets, malformed data)
- Confidence score validation

### Integration Tests
- End-to-end detection on Bar_charts.twb
- Comparison with manual chart type analysis
- Performance benchmarks

### Validation Criteria
- **Accuracy Target**: 90%+ correct chart type detection
- **Coverage Target**: 95%+ of worksheets get a confident classification
- **Performance Target**: <100ms per worksheet analysis

## Migration Impact

### Benefits for LookML Generation
1. **Accurate Dashboard Elements**: Proper chart types for LookML dashboards
2. **Better User Experience**: Charts render as expected in Looker
3. **Reduced Manual Fixes**: Less post-migration cleanup required
4. **Enhanced Metadata**: Rich chart variant information for future features

### Backward Compatibility
- Fallback to basic detection for unsupported cases
- Graceful degradation when confidence is low
- Maintain existing API contracts

## Future Enhancements

### Advanced Features
1. **Custom Chart Types**: Support for extension-based visualizations
2. **Interactive Elements**: Detect actions, filters, parameters
3. **Style Migration**: Color palettes, fonts, sizing
4. **Performance Optimization**: ML-based chart type prediction

### Integration Opportunities
1. **Tableau Server API**: Real-time chart type validation
2. **Looker API**: Automatic dashboard creation
3. **Version Control**: Track chart type changes over time

---

## Implementation Checklist

- [ ] Create `EnhancedChartTypeDetector` class
- [ ] Implement Layer 1: Direct mark detection
- [ ] Implement Layer 2: Dual-axis detection
- [ ] Implement Layer 3: Encoding inference
- [ ] Implement Layer 4: Field context analysis
- [ ] Implement Layer 5: Variant detection
- [ ] Add comprehensive unit tests
- [ ] Update WorksheetHandler integration
- [ ] Validate against Bar_charts.twb
- [ ] Performance optimization
- [ ] Documentation and examples

---

*Last updated: August 2025*
*Status: Design Complete - Ready for Implementation*
