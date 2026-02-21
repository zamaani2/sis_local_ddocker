# Style Guidelines for SHS System Templates

This document outlines the style guidelines and best practices for maintaining consistent design, colors, and layouts across all templates in the SHS System.

## Color Palette

We use a consistent color palette defined with CSS variables in the `partials/_styles.html` file:

### Primary Colors

- `--primary-color: #27ddf5` - Main highlight color
- `--primary-dark: #1fb8cc` - Darker shade for hover states
- `--primary-light: #7eeaf7` - Lighter shade for backgrounds
- `--primary-bg: #f0fbfd` - Very light background

### Secondary Colors

- `--secondary-color: #2c5d3f` - Complementary to primary
- `--secondary-dark: #1f4c2f` - Darker shade
- `--secondary-light: #4d7e62` - Lighter shade
- `--secondary-bg: #edf9e5` - Very light background

### Neutral Colors

- `--neutral-dark: #333333` - Text color
- `--neutral-medium: #666666` - Secondary text
- `--neutral-light: #999999` - Disabled text
- `--neutral-bg: #f4f4f4` - Page background

### Accent Colors

- `--accent-success: #28a745` - Success messages
- `--accent-danger: #dc3545` - Error messages
- `--accent-warning: #ffc107` - Warning messages
- `--accent-info: #17a2b8` - Information messages

## Typography

- Primary Font: `Source Sans 3` with system fallbacks
- Secondary Font: `Arial, sans-serif` (for specific components)
- Use the following font sizes for consistency:
  - Headings: `h1` (2rem), `h2` (1.75rem), `h3` (1.5rem), `h4` (1.25rem), `h5` (1rem)
  - Body text: 1rem (16px)
  - Small text: 0.875rem (14px)
  - Extra small text: 0.75rem (12px)

## Using the Style System

### Including Styles

Always include our centralized styles in each template:

```html
{% include 'partials/_styles.html' %}
```

### Using CSS Variables

Use CSS variables for consistent styling:

```css
.my-element {
  color: var(--primary-color);
  background-color: var(--primary-bg);
  border-radius: var(--border-radius-md);
  box-shadow: var(--box-shadow-sm);
}
```

### Components

#### Buttons

Use the following button classes:

- Primary buttons: `btn btn-primary`
- Secondary buttons: `btn btn-secondary`
- Success buttons: `btn btn-success`
- Danger buttons: `btn btn-danger`

#### Cards

Cards should use:

- `.card` for the container
- `.card-header` for the header
- `.card-body` for the content
- `.card-footer` for the footer

#### Tables

Tables should use:

- `.table` for basic tables
- `.table-striped` for alternating row colors
- `.table-hover` for hover effects
- `.table-bordered` for borders

## Template Structure

1. All templates should extend from `base.html` where possible
2. For standalone pages, include the centralized styles
3. Use consistent naming for blocks:
   - `{% block title %}{% endblock %}`
   - `{% block content %}{% endblock %}`
   - `{% block extra_css %}{% endblock %}`
   - `{% block extra_js %}{% endblock %}`

## Print Styles

When creating print-friendly pages:

1. Use `@media print` queries for print-specific styles
2. Add the `.no-print` class to elements that shouldn't be printed
3. Add the `.print-only` class to elements that should only appear in print

## Accessibility Guidelines

1. Use semantic HTML elements (`<header>`, `<main>`, `<footer>`, etc.)
2. Maintain good color contrast ratios
3. Include proper alt text for images
4. Ensure forms are properly labeled

## Responsive Design

All templates should be responsive, using:

1. Bootstrap's grid system with appropriate breakpoints
2. Fluid layouts that adjust to different screen sizes
3. Media queries for specific adjustments when needed

---

By following these guidelines, we ensure a consistent experience across all templates in the SHS System.
