from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
import time

driver = None

def start_browser():
    global driver
    if driver is None:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--mute-audio")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        driver.get("https://delhihighcourt.nic.in/app/get-case-type-status")
        time.sleep(3)
    return driver

def get_captcha():
    driver = start_browser()
    return driver.find_element(By.ID, "captcha-code").text

def refresh_captcha():
    """Refresh captcha without reloading the entire page"""
    global driver
    if driver is None:
        return get_captcha()
    
    try:
        # First, make sure we're on the main search page
        current_url = driver.current_url
        if "get-case-type-status" not in current_url:
            # If we're not on the main page, navigate back to it
            driver.get("https://delhihighcourt.nic.in/app/get-case-type-status")
            time.sleep(3)
        
        # Try to refresh the captcha by clicking a refresh button or reloading just the captcha area
        # First, try to find a refresh button for captcha
        try:
            refresh_button = driver.find_element(By.ID, "refresh-captcha")
            refresh_button.click()
            time.sleep(1)
        except:
            # If no refresh button, try to reload the page but keep the driver instance
            driver.refresh()
            time.sleep(3)
        
        # Wait for the captcha element to be present
        wait = WebDriverWait(driver, 10)
        captcha_element = wait.until(EC.presence_of_element_located((By.ID, "captcha-code")))
        return captcha_element.text
    except Exception as e:
        print(f"Error refreshing captcha: {e}")
        # Fallback to getting a fresh captcha by restarting the browser
        if driver:
            try:
                driver.quit()
            except:
                pass
        driver = None
        return get_captcha()

def get_available_case_types():
    """Get all available case types from the dropdown"""
    driver = start_browser()
    try:
        # Make sure we're on the main search page
        current_url = driver.current_url
        if "get-case-type-status" not in current_url:
            # If we're not on the main page, navigate back to it
            driver.get("https://delhihighcourt.nic.in/app/get-case-type-status")
            time.sleep(3)
        
        # Wait for the case type select to be present
        wait = WebDriverWait(driver, 10)
        case_type_select = wait.until(EC.presence_of_element_located((By.ID, "case_type")))
        select = Select(case_type_select)
        options = select.options
        case_types = []
        for option in options:
            if option.get_attribute("value") and option.get_attribute("value").strip():
                case_types.append({
                    'value': option.get_attribute("value"),
                    'text': option.text
                })
        return case_types
    except Exception as e:
        print(f"Error getting case types: {e}")
        return []

def submit_form(case_type, case_number, case_year, captcha_input):
    driver = start_browser()
    
    try:
        # Wait for elements to be present
        wait = WebDriverWait(driver, 10)
        
        # Select case type with error handling
        case_type_select = wait.until(EC.presence_of_element_located((By.ID, "case_type")))
        select = Select(case_type_select)
        
        # Check if the case type exists
        available_options = [option.get_attribute("value") for option in select.options]
        if case_type not in available_options:
            error_msg = f"Case type '{case_type}' not found. Available options: {', '.join(available_options[:10])}..."
            return f"<div style='color: red; padding: 20px; border: 1px solid red;'><h3>Error</h3><p>{error_msg}</p></div>", ""
        
        select.select_by_value(case_type)
        
        # Fill other fields
        case_number_input = wait.until(EC.presence_of_element_located((By.ID, "case_number")))
        case_number_input.clear()
        case_number_input.send_keys(case_number)
        
        year_select = wait.until(EC.presence_of_element_located((By.ID, "case_year")))
        year_select_element = Select(year_select)
        year_select_element.select_by_value(case_year)
        
        captcha_input_element = wait.until(EC.presence_of_element_located((By.ID, "captchaInput")))
        captcha_input_element.clear()
        captcha_input_element.send_keys(captcha_input)
        
        # Submit form
        search_button = wait.until(EC.element_to_be_clickable((By.ID, "search")))
        search_button.click()
        time.sleep(5)

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        result_div = soup.find("div", class_="table-responsive") or soup
        result_html = str(result_div)

        # Extract Orders link and fetch that page
        orders_html = ""
        try:
            orders_link_tag = soup.find("a", string="Orders")
            if orders_link_tag and orders_link_tag.get("href"):
                orders_url = orders_link_tag["href"]
                driver.get(orders_url)
                time.sleep(3)
                orders_soup = BeautifulSoup(driver.page_source, "html.parser")
                orders_table = orders_soup.find("table", id="caseTable")
                if orders_table:
                    orders_html = str(orders_table)
                else:
                    orders_html = "<p style='color:red;'>Orders table not found on the page.</p>"
        except Exception as e:
            orders_html = f"<p style='color:red;'>Could not fetch Orders content: {str(e)}</p>"

        return result_html, orders_html
        
    except NoSuchElementException as e:
        error_msg = f"Element not found: {str(e)}"
        return f"<div style='color: red; padding: 20px; border: 1px solid red;'><h3>Error</h3><p>{error_msg}</p></div>", ""
    except TimeoutException as e:
        error_msg = f"Timeout waiting for element: {str(e)}"
        return f"<div style='color: red; padding: 20px; border: 1px solid red;'><h3>Error</h3><p>{error_msg}</p></div>", ""
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        return f"<div style='color: red; padding: 20px; border: 1px solid red;'><h3>Error</h3><p>{error_msg}</p></div>", ""
