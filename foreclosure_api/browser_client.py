"""
Browser automation client for accessing the Connecticut foreclosure website.

This module uses Selenium to control a headless browser to bypass the website's
anti-bot protections and fetch foreclosure data.
"""
import os
import tempfile
import time
import uuid
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


class ForeclosureBrowserClient:
    """Browser automation client for Connecticut foreclosure website."""
    
    def __init__(self, headless: bool = True):
        """Initialize the browser client."""
        self.driver: Optional[webdriver.Chrome] = None
        self.headless = headless
        self.base_url = "https://sso.eservices.jud.ct.gov/foreclosures/Public/"
        self.temp_user_data_dir = None
        
    def start_browser(self) -> None:
        """Start the browser with optimal settings."""
        print("[BROWSER] Starting Chrome browser...")
        
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Essential Chrome options for government sites and isolation
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Complete isolation strategy - no user data persistence
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-client-side-phishing-detection")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-hang-monitor")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-prompt-on-repost")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-translate")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--metrics-recording-only")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--safebrowsing-disable-auto-update")
        chrome_options.add_argument("--enable-automation")
        chrome_options.add_argument("--password-store=basic")
        chrome_options.add_argument("--use-mock-keychain")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")
        
        # Create a unique temporary directory for this session only
        self.temp_user_data_dir = tempfile.mkdtemp(prefix="chrome_foreclosure_")
        chrome_options.add_argument(f"--user-data-dir={self.temp_user_data_dir}")
        print(f"[BROWSER] Using temp user data dir: {self.temp_user_data_dir}")
        
        # User agent to appear as a regular browser
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Set up the Chrome driver with auto-managed driver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute script to remove webdriver property
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("[BROWSER] Chrome browser started successfully")
        
    def stop_browser(self) -> None:
        """Stop the browser and clean up."""
        if self.driver:
            print("[BROWSER] Stopping Chrome browser...")
            self.driver.quit()
            self.driver = None
            
        # Clean up temporary user data directory
        if self.temp_user_data_dir and os.path.exists(self.temp_user_data_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_user_data_dir, ignore_errors=True)
                print(f"[BROWSER] Cleaned up temp directory: {self.temp_user_data_dir}")
            except Exception as e:
                print(f"[BROWSER] Warning: Could not clean up temp directory: {e}")
            self.temp_user_data_dir = None
            
    def get_page_source(self, url: str, wait_for_element: str = None, timeout: int = 30) -> str:
        """
        Get the page source for a given URL.
        
        Args:
            url: The URL to fetch
            wait_for_element: Optional element to wait for before returning source
            timeout: Maximum time to wait for page load
            
        Returns:
            The page source HTML
        """
        if not self.driver:
            self.start_browser()
            
        print(f"[BROWSER] Navigating to: {url}")
        self.driver.get(url)
        
        # Wait for page to load
        if wait_for_element:
            try:
                wait = WebDriverWait(self.driver, timeout)
                wait.until(EC.presence_of_element_located((By.ID, wait_for_element)))
                print(f"[BROWSER] Successfully waited for element: {wait_for_element}")
            except Exception as e:
                print(f"[BROWSER] Warning: Could not find element {wait_for_element}: {str(e)}")
        else:
            # Default wait for basic page load
            time.sleep(3)
            
        page_source = self.driver.page_source
        print(f"[BROWSER] Retrieved page source ({len(page_source)} characters)")
        
        return page_source
        
    def get_city_list_page(self) -> str:
        """Get the main city list page."""
        url = f"{self.base_url}PendPostbyTownList.aspx"
        # Wait for the main content to load (there should be city links)
        return self.get_page_source(url, timeout=30)
        
    def get_city_postings_page(self, city_name: str) -> str:
        """Get the posting list page for a specific city."""
        url = f"{self.base_url}PendPostbyTownDetails.aspx?town={city_name}"
        # Wait for the table to load
        return self.get_page_source(url, wait_for_element="ctl00_cphBody_GridView1", timeout=30)
        
    def get_auction_details_page(self, posting_id: str) -> str:
        """Get the auction details page for a specific posting ID."""
        url = f"{self.base_url}PendPostDetailPublic.aspx?PostingId={posting_id}"
        # Wait for the main content to load
        return self.get_page_source(url, timeout=30)
        
    def __enter__(self):
        """Context manager entry."""
        self.start_browser()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_browser()