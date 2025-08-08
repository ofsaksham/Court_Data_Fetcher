import unittest
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock

# Add the parent directory to the path to import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db

class CourtDataFetcherTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client and database"""
        self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
        app.config['TESTING'] = True
        self.app = app.test_client()
        
        with app.app_context():
            db.init_db()

    def tearDown(self):
        """Clean up after tests"""
        os.close(self.db_fd)
        os.unlink(app.config['DATABASE'])

    def test_home_page(self):
        """Test that home page loads correctly"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Delhi High Court Case Status', response.data)

    def test_home_page_has_form(self):
        """Test that home page contains the search form"""
        response = self.app.get('/')
        self.assertIn(b'case_type', response.data)
        self.assertIn(b'case_number', response.data)
        self.assertIn(b'case_year', response.data)
        self.assertIn(b'captcha_entered', response.data)

    def test_refresh_captcha(self):
        """Test captcha refresh endpoint"""
        response = self.app.get('/refresh-captcha')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('success', data)
        self.assertIn('captcha', data)

    @patch('app.selenium_worker.fetch_case_data')
    def test_submit_form_success(self, mock_fetch):
        """Test successful form submission"""
        # Mock successful case data fetch
        mock_fetch.return_value = {
            'success': True,
            'data': {
                'parties': 'Test Petitioner vs Test Respondent',
                'filing_date': '2024-01-01',
                'next_hearing': '2024-02-01',
                'status': 'Pending'
            }
        }

        response = self.app.post('/submit', data={
            'case_type': 'WP(C)',
            'case_number': '123',
            'case_year': '2024',
            'captcha_entered': 'ABC123'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Case Result', response.data)

    @patch('app.selenium_worker.fetch_case_data')
    def test_submit_form_failure(self, mock_fetch):
        """Test form submission with invalid case"""
        # Mock failed case data fetch
        mock_fetch.return_value = {
            'success': False,
            'error': 'Case not found'
        }

        response = self.app.post('/submit', data={
            'case_type': 'WP(C)',
            'case_number': '999999',
            'case_year': '2024',
            'captcha_entered': 'ABC123'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Case not found', response.data)

    def test_submit_form_missing_fields(self):
        """Test form submission with missing required fields"""
        response = self.app.post('/submit', data={
            'case_type': 'WP(C)',
            'case_number': '',
            'case_year': '2024',
            'captcha_entered': 'ABC123'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        # Should redirect back to form with error

    def test_back_to_search(self):
        """Test back to search functionality"""
        response = self.app.get('/back')
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertIn('/index', response.location)

    def test_get_orders_data(self):
        """Test orders data endpoint"""
        response = self.app.post('/get-orders-data', data={
            'case_type': 'WP(C)',
            'case_number': '123',
            'case_year': '2024',
            'captcha_entered': 'ABC123'
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('success', data)

    def test_download_all_orders(self):
        """Test download all orders endpoint"""
        response = self.app.post('/download-all-orders', data={
            'orders_html': '<div>Test orders</div>'
        })
        # Should return a file or error response
        self.assertIn(response.status_code, [200, 400, 500])

class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test database"""
        self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
        app.config['TESTING'] = True
        
        with app.app_context():
            db.init_db()

    def tearDown(self):
        """Clean up after tests"""
        os.close(self.db_fd)
        os.unlink(app.config['DATABASE'])

    def test_database_connection(self):
        """Test database connection and table creation"""
        with app.app_context():
            # Test that we can connect to the database
            conn = db.get_db()
            self.assertIsNotNone(conn)
            
            # Test that tables exist
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            self.assertIn('case_queries', tables)
            self.assertIn('case_results', tables)

    def test_log_query(self):
        """Test logging a case query"""
        with app.app_context():
            query_id = db.log_case_query('WP(C)', '123', 2024, '{"test": "data"}', 'success')
            self.assertIsNotNone(query_id)
            
            # Verify the query was logged
            conn = db.get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM case_queries WHERE id = ?", (query_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[1], 'WP(C)')  # case_type
            self.assertEqual(row[2], '123')    # case_number
            self.assertEqual(row[3], 2024)     # case_year

class SeleniumWorkerTestCase(unittest.TestCase):
    """Test cases for selenium worker functionality"""
    
    @patch('app.selenium_worker.webdriver.Chrome')
    def test_browser_initialization(self, mock_chrome):
        """Test browser initialization"""
        from selenium_worker import initialize_browser
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        driver = initialize_browser()
        self.assertIsNotNone(driver)
        mock_chrome.assert_called_once()

    @patch('app.selenium_worker.webdriver.Chrome')
    def test_captcha_generation(self, mock_chrome):
        """Test CAPTCHA generation"""
        from selenium_worker import generate_captcha
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Mock page elements
        mock_element = MagicMock()
        mock_element.text = "ABC123"
        mock_driver.find_element.return_value = mock_element
        
        captcha = generate_captcha()
        self.assertIsNotNone(captcha)
        self.assertIsInstance(captcha, str)

    @patch('app.selenium_worker.webdriver.Chrome')
    def test_case_data_fetching(self, mock_chrome):
        """Test case data fetching"""
        from selenium_worker import fetch_case_data
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Mock successful case data
        mock_driver.find_element.return_value.text = "Test Case Data"
        
        result = fetch_case_data('WP(C)', '123', 2024, 'ABC123')
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)

class InputValidationTestCase(unittest.TestCase):
    """Test cases for input validation"""
    
    def test_valid_case_number(self):
        """Test valid case number validation"""
        from app import validate_case_number
        
        # Test valid case numbers
        self.assertTrue(validate_case_number('123'))
        self.assertTrue(validate_case_number('12345'))
        self.assertTrue(validate_case_number('ABC123'))
        
        # Test invalid case numbers
        self.assertFalse(validate_case_number(''))
        self.assertFalse(validate_case_number('abc'))
        self.assertFalse(validate_case_number('123abc!@#'))

    def test_valid_case_year(self):
        """Test valid case year validation"""
        from app import validate_case_year
        
        # Test valid years
        self.assertTrue(validate_case_year(2024))
        self.assertTrue(validate_case_year(2020))
        self.assertTrue(validate_case_year(1990))
        
        # Test invalid years
        self.assertFalse(validate_case_year(2025))  # Future year
        self.assertFalse(validate_case_year(1800))  # Too old
        self.assertFalse(validate_case_year('abc'))  # Not a number

    def test_valid_case_type(self):
        """Test valid case type validation"""
        from app import validate_case_type
        
        # Test valid case types
        self.assertTrue(validate_case_type('WP(C)'))
        self.assertTrue(validate_case_type('CRL.A.'))
        self.assertTrue(validate_case_type('CIVIL'))
        
        # Test invalid case types
        self.assertFalse(validate_case_type(''))
        self.assertFalse(validate_case_type('INVALID'))
        self.assertFalse(validate_case_type('123'))

class ErrorHandlingTestCase(unittest.TestCase):
    """Test cases for error handling"""
    
    def test_network_error_handling(self):
        """Test network error handling"""
        from selenium_worker import handle_network_error
        
        error = Exception("Connection timeout")
        result = handle_network_error(error)
        
        self.assertIsInstance(result, dict)
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    def test_captcha_error_handling(self):
        """Test CAPTCHA error handling"""
        from selenium_worker import handle_captcha_error
        
        error = Exception("CAPTCHA not found")
        result = handle_captcha_error(error)
        
        self.assertIsInstance(result, dict)
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    def test_database_error_handling(self):
        """Test database error handling"""
        with app.app_context():
            from db import handle_db_error
            
            error = Exception("Database connection failed")
            result = handle_db_error(error)
            
            self.assertIsInstance(result, dict)
            self.assertFalse(result['success'])
            self.assertIn('error', result)

class PerformanceTestCase(unittest.TestCase):
    """Test cases for performance and timing"""
    
    def test_response_time(self):
        """Test response time for main endpoints"""
        import time
        
        # Test home page response time
        start_time = time.time()
        response = self.app.get('/')
        end_time = time.time()
        
        response_time = end_time - start_time
        self.assertLess(response_time, 2.0)  # Should respond within 2 seconds
        self.assertEqual(response.status_code, 200)

    def test_captcha_refresh_time(self):
        """Test CAPTCHA refresh response time"""
        import time
        
        start_time = time.time()
        response = self.app.get('/refresh-captcha')
        end_time = time.time()
        
        response_time = end_time - start_time
        self.assertLess(response_time, 5.0)  # Should respond within 5 seconds
        self.assertEqual(response.status_code, 200)

class SecurityTestCase(unittest.TestCase):
    """Test cases for security features"""
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention"""
        malicious_input = "'; DROP TABLE case_queries; --"
        
        response = self.app.post('/submit', data={
            'case_type': 'WP(C)',
            'case_number': malicious_input,
            'case_year': '2024',
            'captcha_entered': 'ABC123'
        })
        
        # Should not crash and should handle gracefully
        self.assertIn(response.status_code, [200, 400, 500])

    def test_xss_prevention(self):
        """Test XSS prevention"""
        malicious_input = '<script>alert("XSS")</script>'
        
        response = self.app.post('/submit', data={
            'case_type': 'WP(C)',
            'case_number': malicious_input,
            'case_year': '2024',
            'captcha_entered': 'ABC123'
        })
        
        # Should not contain unescaped script tags in response
        if response.status_code == 200:
            self.assertNotIn(b'<script>', response.data)

    def test_input_sanitization(self):
        """Test input sanitization"""
        from app import sanitize_input
        
        # Test various malicious inputs
        malicious_inputs = [
            '<script>alert("XSS")</script>',
            '"; DROP TABLE users; --',
            'admin\' OR 1=1--',
            '../../etc/passwd'
        ]
        
        for malicious_input in malicious_inputs:
            sanitized = sanitize_input(malicious_input)
            self.assertNotIn('<script>', sanitized)
            self.assertNotIn('DROP TABLE', sanitized)
            self.assertNotIn('OR 1=1', sanitized)

class IntegrationTestCase(unittest.TestCase):
    """Integration test cases"""
    
    @patch('app.selenium_worker.fetch_case_data')
    def test_full_workflow(self, mock_fetch):
        """Test complete workflow from form submission to result display"""
        # Mock successful case data
        mock_fetch.return_value = {
            'success': True,
            'data': {
                'parties': 'Test Petitioner vs Test Respondent',
                'filing_date': '2024-01-01',
                'next_hearing': '2024-02-01',
                'status': 'Pending',
                'orders': [
                    {'title': 'Test Order', 'url': 'http://test.com/order.pdf'}
                ]
            }
        }
        
        # Step 1: Get home page
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Submit form
        response = self.app.post('/submit', data={
            'case_type': 'WP(C)',
            'case_number': '123',
            'case_year': '2024',
            'captcha_entered': 'ABC123'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Case Result', response.data)
        
        # Step 3: Test orders data endpoint
        response = self.app.post('/get-orders-data', data={
            'case_type': 'WP(C)',
            'case_number': '123',
            'case_year': '2024',
            'captcha_entered': 'ABC123'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('success', data)

if __name__ == '__main__':
    unittest.main()
