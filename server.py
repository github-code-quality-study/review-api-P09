import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, urlparse
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass

    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """
        FILTER_LOCATIONS = set([
        "Albuquerque, New Mexico", "Carlsbad, California", "Chula Vista, California", "Colorado Springs, Colorado",
        "Denver, Colorado", "El Cajon, California", "El Paso, Texas", "Escondido, California", "Fresno, California",
        "La Mesa, California", "Las Vegas, Nevada", "Los Angeles, California", "Oceanside, California",
        "Phoenix, Arizona", "Sacramento, California", "Salt Lake City, Utah", "San Diego, California", "Tucson, Arizona"
        ])
        if environ["REQUEST_METHOD"] == "GET":
            # Create the response body from the reviews and convert to a JSON byte string
            response_body = json.dumps(reviews, indent=2).encode("utf-8")
             # Write your code here
            query_params = parse_qs(environ.get('QUERY_STRING', ''))
            location = query_params.get('location', [None])[0]
            start_date = query_params.get('start_date', [None])[0]
            end_date = query_params.get('end_date', [None])[0]
        
            # Filter reviews based on location
            filter_review = reviews
            if location:
                filter_review = [review for review in filter_review if review['Location'] == location]
            #Filter reviews based on start_date and end_date
            if start_date or end_date:
                    # Convert string dates to datetime objects for comparison
                if start_date:
                    start_date = datetime.strptime(start_date, "%Y-%m-%d")
                if end_date:
                    end_date = datetime.strptime(end_date, "%Y-%m-%d")
                
                filter_review = [
                    review for review in filter_review
                    if (
                        (not start_date or datetime.strptime(review.get('Timestamp', ''), "%Y-%m-%d %H:%M:%S") >= start_date) and
                        (not end_date or datetime.strptime(review.get('Timestamp', ''), "%Y-%m-%d %H:%M:%S") <= end_date)
                    )
                ]
            # Sort reviews by sentiment
            response_data = []
            for review in filter_review:
                sentiment = self.analyze_sentiment(review['ReviewBody'])
                response_data.append({
                    "ReviewId": review['ReviewId'],
                    "ReviewBody": review['ReviewBody'],
                    "Location": review['Location'],
                    "Timestamp": review['Timestamp'],
                    "sentiment": sentiment
                })

            response_body = json.dumps(response_data, indent=2).encode("utf-8")
            # Set the appropriate response headers
            start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body)))
             ])
            
            return [response_body]


        if environ["REQUEST_METHOD"] == "POST":
            # Write your code here
            try:
                request_body_size = int(environ.get('CONTENT_LENGTH', 0))
                request_body = environ['wsgi.input'].read(request_body_size)
                data = parse_qs(request_body.decode('utf-8'))

                location = data.get('Location', [None])[0]
                review_body = data.get('ReviewBody', [None])[0]
                #Location check
                if location is None:
                    error_response = json.dumps({"error": "missing location"}).encode("utf-8")
                    start_response("400 Bad Request", [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(error_response)))
                ])
                    return [error_response]
                elif location.strip() not in FILTER_LOCATIONS:
                    error_response = json.dumps({"error": "invalid location"}).encode("utf-8")
                    start_response("400 Bad Request", [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(error_response)))
                ])
                    return [error_response]

                # ReviewBody check
                if review_body is None:
                    error_response = json.dumps({"error": "missing review body"}).encode("utf-8")
                    start_response("400 Bad Request", [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(error_response)))
                ])
                    return [error_response]

                # Create ReviewId and timestamp
                existing_ids = {review.get('review_id') for review in reviews}
                review_id = str(uuid.uuid4())
                while review_id in existing_ids:
                    review_id = str(uuid.uuid4())
            
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                response_data = {
                "ReviewId": review_id,
                "ReviewBody": review_body,
                "Location": location,
                "Timestamp": timestamp
                }

                response_body = json.dumps(response_data).encode("utf-8")

                start_response("201 Created", [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response_body)))
                ])

                return [response_body]
            except Exception as e:
                error_response = json.dumps({"error": str(e)}).encode("utf-8")
                start_response("500 Internal Server Error", [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(error_response)))
                ])
                return [error_response]

if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()