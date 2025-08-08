from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import db
import sqlite3
from selenium_worker import get_captcha, submit_form, get_available_case_types, refresh_captcha
import requests
import zipfile
import os
import tempfile
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

app = Flask(__name__)
db.init_db()

@app.route('/')
def index():
    captcha = get_captcha()
    case_types = get_available_case_types()
    return render_template('index.html', captcha=captcha, case_types=case_types)

@app.route('/back')
def back_to_search():
    """Go back to search form with fresh captcha without reloading driver"""
    captcha = refresh_captcha()
    case_types = get_available_case_types()
    return render_template('index.html', captcha=captcha, case_types=case_types)

@app.route('/refresh-captcha')
def refresh_captcha_ajax():
    """AJAX endpoint to refresh captcha"""
    try:
        captcha = refresh_captcha()
        return jsonify({'success': True, 'captcha': captcha})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get-orders-data', methods=['POST'])
def get_orders_data():
    """Get orders data for a specific case without redirecting to Delhi High Court"""
    try:
        case_type = request.form['case_type']
        case_number = request.form['case_number']
        case_year = request.form['case_year']
        captcha_entered = request.form['captcha_entered']
        
        # Get the orders data using selenium worker
        result_html, orders_html = submit_form(case_type, case_number, case_year, captcha_entered)
        
        # Parse the orders HTML to extract order details
        soup = BeautifulSoup(orders_html, 'html.parser')
        
        # Find all order links and their details
        orders_data = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href')
            if href and ('pdf' in href.lower() or 'order' in href.lower()):
                # Make sure it's a full URL
                if not href.startswith('http'):
                    base_url = "https://delhihighcourt.nic.in"
                    href = urljoin(base_url, href)
                
                # Get the text content (order title/description)
                order_title = link.get_text(strip=True) or f"Order {len(orders_data) + 1}"
                
                orders_data.append({
                    'title': order_title,
                    'url': href,
                    'filename': os.path.basename(urlparse(href).path) or f"order_{len(orders_data) + 1}.pdf"
                })
        
        return jsonify({
            'success': True,
            'orders_data': orders_data,
            'orders_html': orders_html
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download-all-orders', methods=['POST'])
def download_all_orders():
    """Download all orders as a zip file"""
    try:
        # Get the orders HTML from the request
        orders_html = request.form.get('orders_html', '')
        
        if not orders_html:
            return jsonify({'success': False, 'error': 'No orders data found'})
        
        # Parse the HTML to extract order links
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(orders_html, 'html.parser')
        
        # Find all links in the orders table
        order_links = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href')
            if href and ('pdf' in href.lower() or 'order' in href.lower()):
                # Make sure it's a full URL
                if href.startswith('http'):
                    order_links.append(href)
                else:
                    # Convert relative URL to absolute
                    base_url = "https://delhihighcourt.nic.in"
                    full_url = urljoin(base_url, href)
                    order_links.append(full_url)
        
        if not order_links:
            return jsonify({'success': False, 'error': 'No downloadable orders found'})
        
        # Create a temporary directory for downloads
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, 'all_orders.zip')
        
        # Download all PDFs and create zip file
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for i, link in enumerate(order_links, 1):
                try:
                    # Download the PDF
                    response = requests.get(link, timeout=30)
                    if response.status_code == 200:
                        # Get filename from URL or create one
                        filename = f"order_{i}.pdf"
                        if 'pdf' in link.lower():
                            parsed_url = urlparse(link)
                            path = parsed_url.path
                            if path.endswith('.pdf'):
                                filename = os.path.basename(path)
                        
                        # Add to zip
                        zipf.writestr(filename, response.content)
                except Exception as e:
                    print(f"Error downloading {link}: {e}")
                    continue
        
        # Return the zip file
        return send_file(
            zip_path,
            as_attachment=True,
            download_name='all_orders.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/submit', methods=['POST'])
def submit():
    case_type = request.form['case_type']
    case_number = request.form['case_number']
    case_year = request.form['case_year']
    captcha_entered = request.form['captcha_entered']

    conn = sqlite3.connect('case_data.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO requests (case_type, case_number, case_year, captcha_entered) VALUES (?, ?, ?, ?)',
                (case_type, case_number, case_year, captcha_entered))
    request_id = cur.lastrowid
    conn.commit()

    result_html, orders_html = submit_form(case_type, case_number, case_year, captcha_entered)

    cur.execute('INSERT INTO results (request_id, result_html) VALUES (?, ?)',
                (request_id, result_html))
    conn.commit()
    conn.close()

    return render_template('result.html', 
                         result_html=result_html, 
                         orders_html=orders_html,
                         case_type=case_type,
                         case_number=case_number,
                         case_year=case_year,
                         captcha_entered=captcha_entered)

if __name__ == '__main__':
    app.run(debug=True)
