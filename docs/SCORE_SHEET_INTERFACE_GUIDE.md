# Score Sheet Interface

## Overview

The Score Sheet Interface provides school administrators with a comprehensive, interactive tool for viewing detailed class score sheets with dynamic filtering capabilities. This feature enables efficient analysis of student performance and professional report generation with minimal effort.

## Features

### 1. Dynamic Score Sheet Interface

- **Single Interface**: One dedicated screen for all score sheet viewing needs
- **Real-time Updates**: Content automatically adapts based on administrator selections
- **Professional Layout**: Clean, standardized template for both individual and comprehensive views

### 2. Advanced Filtering System

- **Class Selection**: Dropdown/searchable field to select specific classes
- **Subject Filtering**: Dropdown/searchable field to select specific subjects
- **All Subjects Option**: Comprehensive view showing all subjects for selected class
- **Instant Updates**: Dynamic filtering with immediate data refresh

### 3. Comprehensive Score Display

- **Detailed Score Data**: Complete assessment information for each student
- **Automatic Ranking**: Student positions calculated and displayed (highest to lowest)
- **Grade Display**: Color-coded grade presentation with professional styling
- **Score Breakdown**: Individual component scores (class work, exams) when viewing single subjects

### 4. Export and Print Functionality

- **PDF Export**: Professional PDF generation with school branding
- **Excel Export**: Structured Excel files for further analysis
- **Print Support**: Print-optimized layouts with proper formatting
- **Consistent Output**: Exported documents replicate on-screen preview exactly

## Technical Implementation

### Files Created/Modified

#### Views

- `shs_system/views/score_sheet.py` - Main view logic and AJAX endpoints
- `shs_system/urls.py` - URL routing for score sheet functionality

#### Templates

- `shs_system/templates/scores/score_sheet.html` - Main interface template
- `shs_system/templates/scores/partials/score_sheet_content.html` - Dynamic content partial
- `shs_system/templates/scores/print/score_sheet_pdf.html` - PDF print template

#### Utilities

- `shs_system/utils/pdf_generator.py` - PDF generation utilities
- `shs_system/utils/excel_generator.py` - Excel generation utilities
- `shs_system/templatetags/custom_filters.py` - Custom template filters

#### Tests

- `shs_system/tests/test_score_sheet.py` - Comprehensive test suite

#### Navigation

- `shs_system/templates/dashboard/admin_dashboard.html` - Added score sheet link

### Key Functions

#### `score_sheet_view(request)`

Main view function that renders the score sheet interface with initial data.

#### `get_score_sheet_data_ajax(request)`

AJAX endpoint for dynamic data loading based on selected filters.

#### `get_score_sheet_data(school, selected_class, selected_subject, current_term)`

Helper function that retrieves and formats score data for display.

#### `export_score_sheet_pdf(request)` / `export_score_sheet_excel(request)`

Export functions for PDF and Excel generation.

## Usage Instructions

### Accessing the Score Sheet

1. Log in as a school administrator
2. Navigate to the Admin Dashboard
3. Click on "Score Sheet" in the Quick Actions section
4. Or directly access via URL: `/score-sheet/`

### Using the Interface

1. **Select Class**: Choose a class from the dropdown menu
2. **Select Subject**: Choose a specific subject or "All Subjects" for comprehensive view
3. **View Results**: The score sheet will automatically update with filtered data
4. **Export Options**: Use Print, Export PDF, or Export Excel buttons as needed

### Filter Options

- **Class Filter**: Shows all classes for the current academic year
- **Subject Filter**:
  - "All Subjects" - Shows comprehensive view with all subjects
  - Individual subjects - Shows detailed breakdown for specific subject

### Export Features

- **Print**: Opens browser print dialog with optimized layout
- **PDF Export**: Downloads professional PDF with school branding
- **Excel Export**: Downloads structured Excel file for analysis

## Data Structure

### Score Data Format

```python
{
    'student': Student object,
    'subjects': {
        'Subject Name': {
            'score': float,
            'grade': str,
            'position': int,
            'class_score': float,
            'exam_score': float
        }
    },
    'total_score': float,
    'average_score': float,
    'position': int,
    'grade': str,
    'remarks': str
}
```

### Template Context

- `classes`: Available classes for current academic year
- `subjects`: Available subjects for the school
- `selected_class`: Currently selected class
- `selected_subject`: Currently selected subject (None for "All Subjects")
- `score_data`: Formatted score data for display
- `current_academic_year`: Current academic year
- `current_term`: Current term
- `school`: School information

## Dependencies

### Required Packages

- `weasyprint` - For high-quality PDF generation
- `openpyxl` - For Excel file generation
- `reportlab` - Fallback PDF generation

### Installation

```bash
pip install weasyprint openpyxl reportlab
```

## Styling and Customization

### CSS Classes

- `.score-sheet-container` - Main container styling
- `.filter-section` - Filter controls section
- `.score-table` - Table styling with responsive design
- `.grade-cell` - Grade-specific styling (A, B, C, D, F)
- `.position-cell` - Position highlighting
- `.student-name` - Student name formatting

### Responsive Design

- Mobile-friendly layout with collapsible filters
- Print-optimized styles for professional output
- Adaptive table sizing for different screen sizes

## Testing

### Test Coverage

The test suite covers:

- Authentication requirements
- View rendering with correct context
- AJAX data loading functionality
- Export functionality (PDF and Excel)
- Error handling for invalid requests
- Template context validation

### Running Tests

```bash
python manage.py test shs_system.tests.test_score_sheet
```

## Security Considerations

- **Authentication Required**: All views require user login
- **School Context**: Data is filtered by user's school context
- **Input Validation**: AJAX endpoints validate input parameters
- **Error Handling**: Graceful error handling for invalid requests

## Performance Optimizations

- **Database Queries**: Optimized queries with select_related
- **AJAX Loading**: Dynamic content loading reduces initial page load
- **Caching**: Template caching for improved performance
- **Lazy Loading**: Data loaded only when needed

## Future Enhancements

### Potential Improvements

1. **Advanced Filtering**: Date range, grade level, performance criteria
2. **Comparative Analysis**: Side-by-side class/subject comparisons
3. **Trend Analysis**: Historical performance tracking
4. **Custom Reports**: User-defined report templates
5. **Bulk Operations**: Mass export/print capabilities
6. **Real-time Updates**: WebSocket integration for live updates

### Integration Opportunities

- **Gradebook Integration**: Direct link to gradebook entry
- **Parent Portal**: Student-specific score sharing
- **Analytics Dashboard**: Performance metrics and insights
- **Mobile App**: Mobile-optimized interface

## Troubleshooting

### Common Issues

1. **No Data Display**: Ensure students are enrolled and scores are entered
2. **Export Failures**: Check PDF/Excel generation dependencies
3. **Filter Issues**: Verify class and subject assignments
4. **Performance Issues**: Check database indexes and query optimization

### Debug Mode

Enable debug mode in settings to see detailed error messages and query information.

## Support

For technical support or feature requests, please contact the development team or refer to the system documentation.
