# Current Academic Settings Guide

## Overview

The Current Academic Settings feature provides a simple and advanced method for setting the current academic year and term for your school system. This eliminates the need to go through the school information edit template, making the process much more efficient.

## Features

- **Dedicated Dashboard**: Centralized location for managing current settings
- **Quick Set Options**: Set academic year only, term only, or both at once
- **Real-time Updates**: Changes take effect immediately across the system
- **Smart Validation**: Ensures term belongs to selected academic year
- **Visual Feedback**: Clear display of current settings with status indicators
- **Multiple Access Points**: Available from dashboard, academic year list, and main menu

## How to Access

### Method 1: Direct Access

1. Navigate to **Academics** → **Current Settings** in the main menu
2. Or go directly to `/current-settings/` URL

### Method 2: From Academic Year Management

1. Go to **Academics** → **Academic Years**
2. Click the **"Quick Set Current"** button in the header

### Method 3: From Admin Dashboard

1. Go to the **Admin Dashboard**
2. Click **"Quick Set Current"** in the System Status card

## Using the Current Settings Dashboard

### Current Settings Display

The dashboard shows:

- **Current Academic Year**: Name, duration, and status
- **Current Term**: Term name, duration, and status
- **Visual Indicators**: Green badges for active settings, warnings for missing settings

### Quick Set Options

#### 1. Set Both Academic Year and Term

- Select both academic year and term from dropdowns
- Click **"Set Current Settings"**
- System validates that term belongs to selected academic year
- Both settings are updated simultaneously

#### 2. Set Academic Year Only

- Select academic year from dropdown
- Click **"Set Academic Year Only"**
- Current term is cleared if it doesn't belong to new academic year
- Useful when changing academic years

#### 3. Set Term Only

- Select term from dropdown
- Click **"Set Term Only"**
- Academic year is automatically set to match the term's academic year
- Useful for quick term changes within same academic year

### Smart Features

#### Automatic Term Filtering

- When you select an academic year, the term dropdown automatically filters to show only terms from that academic year
- This prevents invalid combinations

#### Validation

- System ensures term belongs to selected academic year
- Prevents setting invalid combinations
- Shows clear error messages for invalid selections

#### Immediate Effect

- Changes take effect immediately across the entire system
- All reports, records, and features use the new current settings
- No need to refresh or restart anything

## Best Practices

### Setting Up New Academic Year

1. **Create Academic Year**: First create the academic year in Academic Years management
2. **Create Terms**: Add terms for the new academic year
3. **Set Current**: Use Current Settings dashboard to set both academic year and term

### Changing Terms Within Same Academic Year

1. Use **"Set Term Only"** option
2. Select the new term from dropdown
3. Academic year remains unchanged

### End of Academic Year

1. Use **"Set Academic Year Only"** to switch to new academic year
2. Then set the appropriate term for the new year

## Technical Details

### Database Updates

- Updates `SchoolInformation.current_academic_year` field
- Updates `SchoolInformation.current_term` field
- Changes are immediately reflected in all system queries

### System Integration

- All reports use current settings automatically
- Student promotion system uses current settings
- Score entry system uses current settings
- Report card generation uses current settings

### Security

- Admin-only access with proper authentication
- School-based isolation (multi-tenancy)
- CSRF protection on all forms
- Input validation and sanitization

## Troubleshooting

### Common Issues

**"No terms found for this academic year"**

- Ensure terms have been created for the academic year
- Check that terms are assigned to the correct academic year
- Verify school association for terms

**"Term does not belong to selected academic year"**

- Select a term that belongs to the chosen academic year
- Use the filtered dropdown to see valid options
- Check term assignments in Academic Years management

**Settings not taking effect**

- Refresh the page after making changes
- Check that you have admin permissions
- Verify school association

### Performance Tips

- Use "Set Both" option for most reliable setup
- Avoid frequent changes during active periods
- Set up academic years and terms in advance

## API Endpoints

The system provides AJAX endpoints for programmatic access:

- `POST /api/set-current-academic-year/` - Set current academic year
- `POST /api/set-current-term/` - Set current term
- `POST /api/set-current-settings-both/` - Set both at once
- `GET /api/get-terms-for-academic-year/<id>/` - Get terms for academic year

## Future Enhancements

Planned improvements include:

- Bulk term creation from templates
- Academic year templates
- Automatic term progression
- Integration with calendar systems
- Historical settings tracking
- Audit logs for changes

## Support

If you encounter issues:

1. Check the browser console for error messages
2. Verify your admin permissions
3. Ensure academic years and terms are properly created
4. Contact system administrator for technical support

## Migration Notes

This feature replaces the need to:

- Edit school information to change current settings
- Navigate through multiple forms
- Manually update multiple fields

The old method still works but is no longer recommended for regular use.
