"""
Views for the foreclosure API endpoints.

This module provides endpoints to fetch foreclosure data from the Connecticut
state website, including city lists, posting IDs, and auction details.
"""
import json
import re
import ssl
import traceback

import requests
import urllib3
from bs4 import BeautifulSoup
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .browser_client import ForeclosureBrowserClient

# Base URL for Connecticut foreclosure website
BASE_URL = "https://sso.eservices.jud.ct.gov/foreclosures/Public/"

# Headers to mimic browser requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}

# SSL configuration for requests
# Create a custom SSL context
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Disable SSL warnings since we're bypassing verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create a persistent session with retry strategy
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def create_session():
    """Create a requests session with retry strategy and browser-like behavior"""
    session = requests.Session()
    
    # Retry strategy
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        method_whitelist=["HEAD", "GET", "OPTIONS"],
        backoff_factor=1
    )
    
    # Mount adapter with retry strategy
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set default headers for the session
    session.headers.update(HEADERS)
    
    return session


@csrf_exempt
@require_http_methods(["GET"])
def test_view(request):
    """Simple test endpoint to verify the app is working"""
    return JsonResponse(
        {"success": True, "message": "Foreclosure API is working!", "test": True}
    )


@csrf_exempt
@require_http_methods(["GET"])
def test_external_request(request):
    """Test what happens when we make a request to the external site"""
    print(f"[TEST] Starting comprehensive external request test...")
    
    # Test different approaches
    test_results = []
    
    # Approach 1: Simple requests with verify=False
    try:
        print(f"[TEST] Approach 1: Basic requests with SSL disabled")
        url = f"{BASE_URL}PendPostbyTownList.aspx"
        
        simple_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=simple_headers, timeout=15, verify=False)
        print(f"[TEST] Approach 1 - Status: {response.status_code}")
        
        test_results.append({
            "approach": "Basic SSL disabled",
            "success": True,
            "status_code": response.status_code,
            "content_length": len(response.text)
        })
        
        if response.status_code == 200:
            return JsonResponse({
                "success": True,
                "message": "Basic approach worked!",
                "status_code": response.status_code,
                "content_length": len(response.text),
                "approach": "basic_ssl_disabled"
            })
            
    except Exception as e:
        print(f"[TEST] Approach 1 failed: {str(e)}")
        test_results.append({
            "approach": "Basic SSL disabled",
            "success": False,
            "error": str(e)
        })
    
    # Approach 2: Try HTTP instead of HTTPS
    try:
        print(f"[TEST] Approach 2: Try HTTP instead of HTTPS")
        http_url = BASE_URL.replace('https://', 'http://')
        url = f"{http_url}PendPostbyTownList.aspx"
        
        response = requests.get(url, timeout=15)
        print(f"[TEST] Approach 2 - Status: {response.status_code}")
        
        test_results.append({
            "approach": "HTTP instead of HTTPS",
            "success": True,
            "status_code": response.status_code,
            "content_length": len(response.text)
        })
        
        if response.status_code == 200:
            return JsonResponse({
                "success": True,
                "message": "HTTP approach worked!",
                "status_code": response.status_code,
                "content_length": len(response.text),
                "approach": "http_instead_of_https"
            })
            
    except Exception as e:
        print(f"[TEST] Approach 2 failed: {str(e)}")
        test_results.append({
            "approach": "HTTP instead of HTTPS",
            "success": False,
            "error": str(e)
        })
    
    # Return summary of all failed attempts
    return JsonResponse({
        "success": False,
        "message": "All approaches failed",
        "test_results": test_results,
        "note": "The government website appears to be blocking server requests"
    }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def test_browser_automation(request):
    """Test the browser automation approach."""
    try:
        print("[BROWSER TEST] Starting browser automation test...")
        
        with ForeclosureBrowserClient(headless=True) as browser:
            print("[BROWSER TEST] Browser started, fetching city list page...")
            
            # Get the city list page
            page_source = browser.get_city_list_page()
            
            print(f"[BROWSER TEST] Retrieved page source ({len(page_source)} chars)")
            
            # Parse the page source
            cities = extract_city_info(page_source)
            print(f"[BROWSER TEST] Extracted {len(cities)} cities")
            
            # Test with a specific city if we found any
            if cities:
                test_city = cities[0]['name']
                print(f"[BROWSER TEST] Testing posting IDs for city: {test_city}")
                
                city_page_source = browser.get_city_postings_page(test_city)
                posting_ids = extract_posting_ids(city_page_source)
                
                print(f"[BROWSER TEST] Found {len(posting_ids)} posting IDs for {test_city}")
                
                return JsonResponse({
                    "success": True,
                    "message": "Browser automation successful!",
                    "cities_found": len(cities),
                    "test_city": test_city,
                    "posting_ids_found": len(posting_ids),
                    "sample_cities": cities[:3] if cities else [],
                    "sample_posting_ids": posting_ids[:3] if posting_ids else []
                })
            else:
                return JsonResponse({
                    "success": False,
                    "message": "Page loaded but no cities found",
                    "page_length": len(page_source),
                    "page_preview": page_source[:500]
                })
                
    except Exception as e:
        print(f"[BROWSER TEST] Error: {str(e)}")
        traceback.print_exc()
        return JsonResponse({
            "success": False,
            "error": str(e),
            "message": "Browser automation test failed"
        }, status=500)


def parse_html_to_text(html_content):
    """Convert HTML to plain text while preserving structure"""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text()


def extract_city_info(html_content):
    """Extract city names and counts from the main page"""
    soup = BeautifulSoup(html_content, "html.parser")

    # Select all anchor elements with href containing "PendPostbyTownDetails.aspx?town="
    city_links = soup.find_all(
        "a", href=re.compile(r"PendPostbyTownDetails\.aspx\?town=")
    )

    cities = []

    for link in city_links:
        name = link.text.strip()

        # The expected structure is:
        # <a>City Name</a> <span> (</span> <span>Number</span> <span>)</span> <br>...
        count = 0
        first_span = link.find_next_sibling("span")
        if first_span:
            count_span = first_span.find_next_sibling("span")
            if count_span:
                try:
                    count = int(count_span.text.strip())
                except ValueError:
                    count = 0

        cities.append({"name": name, "count": count})

    return cities


def extract_posting_ids(html_content):
    """Extract posting IDs from city pages"""
    soup = BeautifulSoup(html_content, "html.parser")

    # Get the table that holds the foreclosure sales records
    sales_table = soup.find("table", id="ctl00_cphBody_GridView1")
    if not sales_table:
        return []

    # Get all the rows in the table
    rows = sales_table.find_all("tr")
    posting_ids = []

    # Iterate over each row. Skip the header row (which contains <th> elements).
    for row in rows:
        if row.find("th"):
            continue  # Skip header row

        cells = row.find_all("td")
        if len(cells) < 5:
            continue

        # Extract the "View Full Notice" URL from the fifth cell
        view_notice_link = cells[4].find("a")
        if view_notice_link:
            view_full_notice_url = view_notice_link.get("href", "")

            # Extract the posting_id from the URL query parameter
            if "?" in view_full_notice_url:
                query_part = view_full_notice_url.split("?")[1]
                params = dict(
                    param.split("=") for param in query_part.split("&") if "=" in param
                )
                posting_id = params.get("PostingId", "")

                if posting_id:
                    posting_ids.append(posting_id)

    return posting_ids


def parse_public_auction_notice(html_content):
    """Parse auction notice details from HTML"""
    soup = BeautifulSoup(html_content, "html.parser")

    def get_text(element_id):
        element = soup.find(id=element_id)
        return element.text.strip() if element else ""

    # Extract address
    address = ""
    heading_element = soup.find(id="ctl00_cphBody_lblHeading")
    if heading_element:
        heading_html = str(heading_element)
        # Look for "ADDRESS:" followed by optional <br> tags and capture the text
        address_regex = r"ADDRESS:\s*(?:<br\s*/?>\s*)*([^<]+)"
        match = re.search(address_regex, heading_html, re.IGNORECASE)
        if match:
            address = match.group(1).strip()
            # Check if a second line exists to append
            after_match = heading_html.split(match.group(0))[1]
            second_line_match = re.search(
                r"<br\s*/?>\s*([^<]+)", after_match, re.IGNORECASE
            )
            if second_line_match and second_line_match.group(1).strip():
                address += ", " + second_line_match.group(1).strip()
    
    # Fallback address extraction if not found above
    if not address:
        address_regex2 = r"ADDRESS:\s*(?:<br\s*/?>\s*)*([^<]+)"
        full_match = re.search(address_regex2, html_content, re.IGNORECASE)
        if full_match:
            address = full_match.group(1).strip()

    # Extract dollar amount
    dollar_amount_match = re.search(r"\$[0-9,]+(\.[0-9]{2})?", html_content)
    dollar_amount_string = dollar_amount_match.group(0) if dollar_amount_match else ""
    dollar_amount_number = 0
    if dollar_amount_string:
        try:
            dollar_amount_number = float(
                dollar_amount_string.replace("$", "").replace(",", "")
            )
        except ValueError:
            pass

    # Extract committee information - matching frontend parsing exactly
    committee_element = soup.find(id="ctl00_cphBody_lblCommittee")
    committee_original = committee_element.text.strip() if committee_element else ""

    committee_name = ""
    committee_phone = ""
    committee_email = ""

    if committee_element:
        # Replace <br> tags with newline characters then split into lines
        committee_html = str(committee_element)
        committee_lines = re.sub(r"<br\s*/?>", "\n", committee_html, flags=re.IGNORECASE)
        committee_lines = [
            line.strip() for line in committee_lines.split("\n") if line.strip()
        ]

        # First line is the committee name (matching frontend logic)
        if committee_lines:
            committee_name = committee_lines[0]
            # Remove any span tags from the committee name
            committee_name = re.sub(r"<[^>]+>", "", committee_name).strip()

            # Look for phone and email in all lines
            for line in committee_lines:
                if "PHONE:" in line.upper():
                    committee_phone = (
                        line.split(":", 1)[1].strip() if ":" in line else ""
                    )
                elif "EMAIL:" in line.upper():
                    committee_email = (
                        line.split(":", 1)[1].strip() if ":" in line else ""
                    )

    return {
        "caseCaption": get_text("ctl00_cphBody_uEfileCaseInfo1_lblCaseCap"),
        "fileDate": get_text("ctl00_cphBody_uEfileCaseInfo1_lblFileDate"),
        "docketNumber": get_text("ctl00_cphBody_uEfileCaseInfo1_hlnkDocketNo"),
        "returnDate": get_text("ctl00_cphBody_uEfileCaseInfo1_lblRetDate"),
        "town": get_text("ctl00_cphBody_hlnktown1"),
        "saleDate": get_text("ctl00_cphBody_lblSaleDate"),
        "saleTime": get_text("ctl00_cphBody_lblSaleTime"),
        "inspectionCommencingAt": get_text("ctl00_cphBody_lblInsp"),
        "noticeFrom": get_text("ctl00_cphBody_lblNoticeFrom"),
        "noticeThru": get_text("ctl00_cphBody_lblNoticeThru"),
        "heading": get_text("ctl00_cphBody_lblHeading"),
        "body": get_text("ctl00_cphBody_lblBody"),
        "committee": committee_original,
        "status": get_text("ctl00_cphBody_lblStatus"),
        "address": address,
        "dollarAmountString": dollar_amount_string,
        "dollarAmountNumber": dollar_amount_number,
        "committeeName": committee_name,
        "committeePhone": committee_phone,
        "committeeEmail": committee_email,
    }


@csrf_exempt
@require_http_methods(["GET"])
def get_city_list(request):
    """Fetch the list of cities with foreclosure data using browser automation"""
    try:
        print(f"[FORECLOSURE API] Fetching city list using browser automation...")
        
        with ForeclosureBrowserClient(headless=True) as browser:
            # Get the city list page
            page_source = browser.get_city_list_page()
            
            print(f"[FORECLOSURE API] Retrieved page source ({len(page_source)} characters)")
            
            # Parse the cities
            cities = extract_city_info(page_source)
            print(f"[FORECLOSURE API] Extracted {len(cities)} cities")
            
            if cities:
                print(f"[FORECLOSURE API] First 3 cities: {cities[:3]}")
            
            return JsonResponse({
                "success": True,
                "cities": cities,
                "timestamp": "",  # Browser doesn't provide response headers
                "count": len(cities),
            })
            
    except Exception as e:
        print(f"[FORECLOSURE API] Browser automation error: {str(e)}")
        traceback.print_exc()
        return JsonResponse(
            {
                "success": False,
                "error": f"Failed to fetch city list: {str(e)}",
                "error_type": "browser_automation_error",
            },
            status=500,
        )


@csrf_exempt
@require_http_methods(["GET"])
def get_posting_ids(request):
    """Fetch posting IDs for a specific city using browser automation"""
    city_name = request.GET.get("city")
    if not city_name:
        return JsonResponse(
            {"success": False, "error": "City parameter is required"}, status=400
        )

    try:
        print(f"[FORECLOSURE API] Fetching posting IDs for city: {city_name}")
        
        with ForeclosureBrowserClient(headless=True) as browser:
            # Get the city postings page
            page_source = browser.get_city_postings_page(city_name)
            
            # Extract posting IDs
            posting_ids = extract_posting_ids(page_source)
            print(f"[FORECLOSURE API] Found {len(posting_ids)} posting IDs for {city_name}")

            return JsonResponse({
                "success": True,
                "city": city_name,
                "postingIds": posting_ids,
                "count": len(posting_ids),
            })
            
    except Exception as e:
        print(f"[FORECLOSURE API] Error fetching posting IDs for {city_name}: {str(e)}")
        traceback.print_exc()
        return JsonResponse(
            {"success": False, "error": f"Failed to fetch posting IDs: {str(e)}"},
            status=500,
        )


@csrf_exempt
@require_http_methods(["GET"])
def get_auction_details(request):
    """Fetch auction details for a specific posting ID using browser automation"""
    posting_id = request.GET.get("postingId")
    if not posting_id:
        return JsonResponse(
            {"success": False, "error": "postingId parameter is required"}, status=400
        )

    try:
        print(f"[FORECLOSURE API] Fetching auction details for posting ID: {posting_id}")
        
        with ForeclosureBrowserClient(headless=True) as browser:
            # Get the auction details page
            page_source = browser.get_auction_details_page(posting_id)
            
            # Check if the page indicates "No data found"
            if "No data found" in page_source:
                print(f"[FORECLOSURE API] No data found for posting ID: {posting_id}")
                return JsonResponse({
                    "success": True, 
                    "dataFound": False, 
                    "postingId": posting_id
                })

            # Parse auction notice details
            auction_notice = parse_public_auction_notice(page_source)
            print(f"[FORECLOSURE API] Successfully parsed auction details for posting ID: {posting_id}")

            return JsonResponse({
                "success": True,
                "dataFound": True,
                "postingId": posting_id,
                "auctionNotice": auction_notice,
            })
            
    except Exception as e:
        print(f"[FORECLOSURE API] Error fetching auction details for {posting_id}: {str(e)}")
        traceback.print_exc()
        return JsonResponse(
            {"success": False, "error": f"Failed to fetch auction details: {str(e)}"},
            status=500,
        )


@csrf_exempt
@require_http_methods(["POST"])
def get_batch_auction_details(request):
    """Fetch auction details for multiple posting IDs"""
    try:
        data = json.loads(request.body)
        posting_ids = data.get("postingIds", [])

        if not posting_ids:
            return JsonResponse(
                {"success": False, "error": "postingIds array is required"}, status=400
            )

        results = []
        errors = []

        for posting_id in posting_ids:
            try:
                url = f"{BASE_URL}PendPostDetailPublic.aspx?PostingId={posting_id}"
                response = requests.get(url, headers=HEADERS, timeout=30, verify=False)
                response.raise_for_status()

                if "No data found" in response.text:
                    results.append({"postingId": posting_id, "dataFound": False})
                else:
                    auction_notice = parse_public_auction_notice(response.text)
                    results.append(
                        {
                            "postingId": posting_id,
                            "dataFound": True,
                            "auctionNotice": auction_notice,
                        }
                    )
            except Exception as e:
                errors.append({"postingId": posting_id, "error": str(e)})

        return JsonResponse(
            {
                "success": True,
                "results": results,
                "errors": errors,
                "totalProcessed": len(results),
                "totalErrors": len(errors),
            }
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON in request body"}, status=400
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Failed to process batch request: {str(e)}"},
            status=500,
        )
