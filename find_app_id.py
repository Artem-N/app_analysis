import requests
import json
import sys
from typing import List, Dict, Optional

def validate_search_inputs(app_name: str, country: str) -> None:
    """
    Validate search input parameters
    """
    if not app_name or not isinstance(app_name, str) or len(app_name.strip()) == 0:
        raise ValueError("App name must be a non-empty string")
    
    if not country or not isinstance(country, str) or len(country) != 2:
        raise ValueError("Country must be a 2-letter country code")
    
    # List of valid country codes (can be expanded)
    valid_countries = ["us", "ua", "gb", "ca", "au", "de", "fr", "jp", "kr", "cn"]
    if country.lower() not in valid_countries:
        raise ValueError(f"Invalid country code: {country}. Valid codes: {valid_countries}")

def safe_extract_app_data(result: Dict) -> Optional[Dict]:
    """
    Safely extract app data from search result with error handling
    """
    try:
        return {
            "trackName": result.get('trackName', 'Unknown'),
            "artistName": result.get('artistName', 'Unknown'),
            "trackId": result.get('trackId', 'Unknown'),
            "primaryGenreName": result.get('primaryGenreName', 'Unknown'),
            "averageUserRating": result.get('averageUserRating', 'Unknown'),
            "userRatingCount": result.get('userRatingCount', 'Unknown'),
            "trackViewUrl": result.get('trackViewUrl', 'Unknown'),
            "bundleId": result.get('bundleId', 'Unknown'),
            "releaseDate": result.get('releaseDate', 'Unknown'),
            "version": result.get('version', 'Unknown')
        }
    except Exception as e:
        print(f"Warning: Error extracting app data: {e}")
        return None

def search_app_store(app_name: str, country: str = "us") -> List[Dict]:
    """
    Search for an app in the App Store by name with comprehensive error handling
    """
    try:
        # Validate inputs
        validate_search_inputs(app_name, country)
        
        search_url = "https://itunes.apple.com/search"
        params = {
            "term": app_name.strip(),
            "country": country.lower(),
            "entity": "software",
            "limit": 10
        }
        
        print(f"Searching for '{app_name}' in country {country.upper()}...")
        
        # Make request with timeout
        response = requests.get(search_url, params=params, timeout=30)
        response.raise_for_status()
        
        # Validate JSON response
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON response from App Store API: {e}")
            return []
        
        if not isinstance(data, dict):
            print("Error: Unexpected response format from App Store API")
            return []
        
        results = data.get("results", [])
        
        if not results:
            print(f"No results found for '{app_name}' in {country.upper()}")
            return []
        
        print(f"Search results for '{app_name}' in country {country}:")
        print("=" * 50)
        
        valid_results = []
        error_count = 0
        
        for i, result in enumerate(results, 1):
            app_data = safe_extract_app_data(result)
            
            if app_data:
                print(f"{i}. Name: {app_data['trackName']}")
                print(f"   Developer: {app_data['artistName']}")
                print(f"   ID: {app_data['trackId']}")
                print(f"   Category: {app_data['primaryGenreName']}")
                print(f"   Rating: {app_data['averageUserRating']}")
                print(f"   Number of ratings: {app_data['userRatingCount']}")
                print(f"   URL: {app_data['trackViewUrl']}")
                print("-" * 30)
                
                valid_results.append(app_data)
            else:
                error_count += 1
        
        if error_count > 0:
            print(f"Warning: {error_count} results had extraction errors")
        
        return valid_results
        
    except requests.exceptions.Timeout:
        print(f"Error: Request timeout while searching for '{app_name}' in {country}")
        return []
    except requests.exceptions.ConnectionError:
        print(f"Error: Connection error while searching for '{app_name}' in {country}")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"Error: HTTP error {e.response.status_code} while searching for '{app_name}' in {country}")
        return []
    except requests.RequestException as e:
        print(f"Error during search: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error during search: {e}")
        return []

def main():
    """
    Main function with error handling
    """
    try:
        # Search for Nebula in different countries
        countries = ["us"]
        app_name = "Nebula"
        
        total_results = 0
        
        for country in countries:
            print(f"\nSearching in country: {country.upper()}")
            
            try:
                results = search_app_store(app_name, country)
                
                if results:
                    print(f"Found {len(results)} results")
                    total_results += len(results)
                else:
                    print("No results found")
                    
            except Exception as e:
                print(f"Error searching in {country}: {e}")
                continue
        
        print(f"\nTotal results across all countries: {total_results}")
        
        if total_results == 0:
            print("No results found in any country. Consider:")
            print("- Checking the app name spelling")
            print("- Trying different country codes")
            print("- Verifying internet connection")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\nSearch interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 