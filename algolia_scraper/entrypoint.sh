#!/bin/sh
# This script runs the full data pipeline.
# It first runs the scrapers for the default stores,
# then runs the data processor, passing along any command-line
# arguments provided to the container. This allows for dynamic
# keyword filtering.

set -e

# Run the scrapers
echo "--- Running Sobeys scraper ---"
python algolia_scraper.py sobeys

echo "--- Running Safeway scraper ---"
python algolia_scraper.py safeway

# Run the data processor with all arguments passed to the container
echo "--- Running data processor ---"
python process_data.py "$@"
