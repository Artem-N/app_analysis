from app_store_web_scraper import AppStoreEntry, AppNotFound
import json
from datetime import datetime
import sys
import os

def validate_inputs(app_id, countries):
    """
    Validate input parameters
    """
    if not app_id or not isinstance(app_id, int) or app_id <= 0:
        raise ValueError("App ID must be a positive integer")
    
    if not countries or not isinstance(countries, list):
        raise ValueError("Countries must be a non-empty list")
    
    valid_countries = ["us", "ua", "gb", "ca", "au", "de", "fr", "jp", "kr", "cn"]
    for country in countries:
        if not isinstance(country, str) or country.lower() not in valid_countries:
            raise ValueError(f"Invalid country code: {country}. Valid codes: {valid_countries}")

def safe_get_review_data(review):
    """
    Safely extract review data with error handling
    """
    try:
        return {
            "id": getattr(review, 'id', None),
            "date": review.date.isoformat() if hasattr(review, 'date') and review.date else None,
            "user_name": getattr(review, 'user_name', 'Anonymous'),
            "title": getattr(review, 'title', ''),
            "content": getattr(review, 'content', ''),
            "rating": getattr(review, 'rating', 0),
            "app_version": getattr(review, 'app_version', 'Unknown')
        }
    except Exception as e:
        print(f"Warning: Error extracting review data: {e}")
        return None

def calculate_statistics(reviews):
    """
    Calculate review statistics with error handling
    """
    if not reviews:
        return {
            "average_rating": 0,
            "rating_distribution": {},
            "total_reviews": 0
        }
    
    try:
        # Filter out reviews with invalid ratings
        valid_reviews = [r for r in reviews if r and isinstance(r.get("rating"), (int, float)) and 1 <= r["rating"] <= 5]
        
        if not valid_reviews:
            print("Warning: No valid reviews with ratings found")
            return {
                "average_rating": 0,
                "rating_distribution": {},
                "total_reviews": 0
            }
        
        ratings = [review["rating"] for review in valid_reviews]
        avg_rating = sum(ratings) / len(ratings)
        
        rating_distribution = {}
        for rating in ratings:
            rating_distribution[rating] = rating_distribution.get(rating, 0) + 1
        
        return {
            "average_rating": avg_rating,
            "rating_distribution": rating_distribution,
            "total_reviews": len(valid_reviews)
        }
        
    except Exception as e:
        print(f"Error calculating statistics: {e}")
        return {
            "average_rating": 0,
            "rating_distribution": {},
            "total_reviews": 0
        }

# ---------- SAVE REVIEWS GENERIC ----------

def save_reviews_to_file(reviews, app_id, country, statistics):
    """
    Save reviews to JSON file with error handling
    """
    try:
        # Prepare output directory: data/raw/<country>/
        dir_path = os.path.join("data", "raw", country)
        os.makedirs(dir_path, exist_ok=True)

        filename = os.path.join(dir_path, f"app_{app_id}_reviews_{country}.json")
        
        # Check if file already exists and create backup
        if os.path.exists(filename):
            backup_filename = os.path.join(
                dir_path,
                f"app_{app_id}_reviews_{country}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            )
            os.rename(filename, backup_filename)
            print(f"Backup created: {backup_filename}")
        
        data = {
            "app_id": app_id,
            "country": country,
            "analysis_date": datetime.now().isoformat(),
            "total_reviews": statistics["total_reviews"],
            "average_rating": statistics["average_rating"],
            "rating_distribution": statistics["rating_distribution"],
            "reviews": reviews
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Reviews saved to: {filename}")
        return filename
        
    except PermissionError:
        print(f"Error: Permission denied when trying to save {filename}")
        return None
    except Exception as e:
        print(f"Error saving reviews to file: {e}")
        return None

def analyze_app(app_id: int, countries=None):
    """Analyze given App ID in specified countries with comprehensive error handling."""
    if countries is None:
        countries = ["us"]

    print("=== App Analysis ===")
    print(f"App ID: {app_id}")
    print(f"Analysis started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Countries already provided
    
    total_analysis_results = {}
    
    for country in countries:
        print(f"\n--- Analyzing in {country.upper()} ---")
        
        try:
            # Create AppStoreEntry for Nebula
            app = AppStoreEntry(app_id=app_id, country=country)
            
            # Collect reviews
            reviews = []
            review_count = 0
            error_count = 0
            
            print("Collecting reviews...")
            
            try:
                for review in app.reviews(limit=100):  # Limit to 100 reviews for analysis
                    review_data = safe_get_review_data(review)
                    
                    if review_data:
                        reviews.append(review_data)
                        review_count += 1
                        
                        if review_count % 10 == 0:
                            print(f"Collected {review_count} reviews...")
                    else:
                        error_count += 1
                        
            except Exception as e:
                print(f"Error during review collection: {e}")
                # Continue with collected reviews
            
            print(f"Total reviews collected: {review_count}")
            if error_count > 0:
                print(f"Reviews with errors: {error_count}")
            
            # Calculate statistics
            statistics = calculate_statistics(reviews)
            
            if statistics["total_reviews"] > 0:
                print(f"Average rating: {statistics['average_rating']:.2f}")
                print("Rating distribution:")
                for rating in sorted(statistics["rating_distribution"].keys()):
                    count = statistics["rating_distribution"][rating]
                    percentage = (count / statistics["total_reviews"]) * 100
                    print(f"  {rating} stars: {count} reviews ({percentage:.1f}%)")
                
                # Save reviews to file
                saved_file = save_reviews_to_file(reviews, app_id, country, statistics)
                
                total_analysis_results[country] = {
                    "success": True,
                    "reviews_collected": review_count,
                    "errors": error_count,
                    "statistics": statistics,
                    "file_saved": saved_file is not None
                }
            else:
                print("No valid reviews found for analysis")
                total_analysis_results[country] = {
                    "success": False,
                    "error": "No valid reviews found"
                }
            
        except AppNotFound:
            print(f"Error: App with ID {app_id} not found in {country}")
            total_analysis_results[country] = {
                "success": False,
                "error": "App not found"
            }
        except Exception as e:
            print(f"Unexpected error analyzing app in {country}: {e}")
            total_analysis_results[country] = {
                "success": False,
                "error": str(e)
            }
    
    # Print summary
    print("\n=== Analysis Summary ===")
    successful_analyses = sum(1 for result in total_analysis_results.values() if result.get("success", False))
    total_countries = len(countries)
    
    print(f"Successfully analyzed: {successful_analyses}/{total_countries} countries")
    
    for country, result in total_analysis_results.items():
        if result.get("success"):
            print(f"  {country.upper()}: {result['reviews_collected']} reviews collected")
        else:
            print(f"  {country.upper()}: Failed - {result.get('error', 'Unknown error')}")
    
    print("\n=== Analysis Complete ===")
    return total_analysis_results

# Backward compatibility wrapper

def analyze_nebula_app():
    return analyze_app(1447033725, ["us"])

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze App Store reviews for given app ID.")
    parser.add_argument("app_id", type=int, help="App Store ID")
    parser.add_argument("--countries", nargs="*", default=["us"], help="Country codes")
    args = parser.parse_args()

    try:
        results = analyze_app(args.app_id, args.countries)
        # Exit with appropriate code
        if any(result.get("success", False) for result in results.values()):
            sys.exit(0)  # Success
        else:
            sys.exit(1)  # All analyses failed
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1) 