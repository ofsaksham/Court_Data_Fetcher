# API Documentation

## Overview

The Court Data Fetcher application provides a RESTful API for programmatically accessing court case information. This document describes the available endpoints, request/response formats, and usage examples.

## Base URL

```
http://localhost:5000
```

## Authentication

Currently, the API does not require authentication. However, rate limiting is implemented to prevent abuse.

## Endpoints

### 1. Get Home Page

**GET** `/`

Returns the main search page with the case search form.

**Response:**
- Content-Type: `text/html`
- Status: `200 OK`

### 2. Refresh CAPTCHA

**GET** `/refresh-captcha`

Generates a new CAPTCHA for the search form.

**Response:**
```json
{
  "success": true,
  "captcha": "ABC123"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Failed to generate CAPTCHA"
}
```

### 3. Submit Case Search

**POST** `/submit`

Submits a case search request.

**Request Body:**
```json
{
  "case_type": "WP(C)",
  "case_number": "123",
  "case_year": "2024",
  "captcha_entered": "ABC123"
}
```

**Form Data:**
- `case_type` (string, required): Type of case (e.g., "WP(C)", "CRL.A.")
- `case_number` (string, required): Case number
- `case_year` (integer, required): Year the case was filed
- `captcha_entered` (string, required): CAPTCHA text entered by user

**Response:**
- Content-Type: `text/html`
- Status: `200 OK` (with case results page)
- Status: `302 Found` (redirect to error page on failure)

### 4. Get Orders Data

**POST** `/get-orders-data`

Retrieves detailed orders data for a specific case.

**Request Body:**
```json
{
  "case_type": "WP(C)",
  "case_number": "123",
  "case_year": "2024",
  "captcha_entered": "ABC123"
}
```

**Response:**
```json
{
  "success": true,
  "orders_data": [
    {
      "title": "Order dated 2024-01-15",
      "url": "https://delhihighcourt.nic.in/orders/123.pdf",
      "filename": "order_123_20240115.pdf"
    }
  ]
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Failed to fetch orders data"
}
```

### 5. Download All Orders

**POST** `/download-all-orders`

Downloads all orders for a case as a ZIP file.

**Request Body:**
```json
{
  "orders_html": "<div>Orders HTML content</div>"
}
```

**Response:**
- Content-Type: `application/zip`
- Status: `200 OK`
- Headers: `Content-Disposition: attachment; filename="all_orders.zip"`

### 6. Back to Search

**GET** `/back`

Redirects back to the main search page.

**Response:**
- Status: `302 Found`
- Location: `/index`

## Data Models

### Case Query

```json
{
  "id": 1,
  "case_type": "WP(C)",
  "case_number": "123",
  "case_year": 2024,
  "query_timestamp": "2024-01-15T10:30:00Z",
  "response_data": "{\"parties\": \"...\", \"filing_date\": \"...\"}",
  "status": "success",
  "error_message": null
}
```

### Case Result

```json
{
  "id": 1,
  "query_id": 1,
  "parties": "Petitioner vs Respondent",
  "filing_date": "2024-01-01",
  "next_hearing": "2024-02-01",
  "case_status": "Pending",
  "orders_data": "[{\"title\": \"...\", \"url\": \"...\"}]"
}
```

### Order

```json
{
  "title": "Order dated 2024-01-15",
  "url": "https://delhihighcourt.nic.in/orders/123.pdf",
  "filename": "order_123_20240115.pdf"
}
```

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 302 | Redirect |
| 400 | Bad Request - Invalid input data |
| 404 | Not Found - Case not found |
| 500 | Internal Server Error - Server error |

## Rate Limiting

The API implements rate limiting to prevent abuse:
- Maximum 10 requests per minute per IP address
- CAPTCHA refresh limited to 5 requests per minute

## Usage Examples

### Python Example

```python
import requests

# Refresh CAPTCHA
response = requests.get('http://localhost:5000/refresh-captcha')
captcha_data = response.json()
captcha = captcha_data['captcha']

# Submit case search
search_data = {
    'case_type': 'WP(C)',
    'case_number': '123',
    'case_year': '2024',
    'captcha_entered': captcha
}

response = requests.post('http://localhost:5000/submit', data=search_data)
print(response.status_code)
```

### JavaScript Example

```javascript
// Refresh CAPTCHA
fetch('/refresh-captcha')
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      document.getElementById('captcha-display').textContent = data.captcha;
    }
  });

// Submit form
const formData = new FormData();
formData.append('case_type', 'WP(C)');
formData.append('case_number', '123');
formData.append('case_year', '2024');
formData.append('captcha_entered', 'ABC123');

fetch('/submit', {
  method: 'POST',
  body: formData
})
.then(response => {
  if (response.redirected) {
    window.location.href = response.url;
  }
});
```

### cURL Example

```bash
# Refresh CAPTCHA
curl -X GET http://localhost:5000/refresh-captcha

# Submit case search
curl -X POST http://localhost:5000/submit \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "case_type=WP(C)&case_number=123&case_year=2024&captcha_entered=ABC123"
```

## Notes

1. **CAPTCHA Handling**: All requests that interact with the court website require a valid CAPTCHA
2. **Session Management**: The application maintains browser sessions to reduce CAPTCHA frequency
3. **Error Handling**: All endpoints return appropriate error messages for debugging
4. **Data Logging**: All queries and responses are logged in the SQLite database
5. **Security**: Input validation and sanitization are implemented for all endpoints

## Future Enhancements

- JWT-based authentication
- API key management
- Webhook support for real-time updates
- GraphQL endpoint
- Bulk case search functionality
- Caching layer with Redis
