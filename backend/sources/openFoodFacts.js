// backend/sources/openFoodFacts.js

const fetch = require('node-fetch');

/**
 * Fetches food data from the Open Food Facts API.
 * @param {string} query - The search query for food items.
 * @param {object} config - The API configuration containing the base URL.
 * @returns {Promise<object>} A promise that resolves to the structured API response.
 */
const fetchFromOpenFoodFacts = async (query, config) => {
  const url = `${config.OFF_BASE_URL}?search_terms=${encodeURIComponent(query)}&json=1&page_size=5`;
  
  console.log(`[OpenFoodFacts] Fetching data for: ${query}`);
  
  const response = await fetch(url);

  if (!response.ok) {
    console.error(`[OpenFoodFacts] API error: ${response.statusText}`);
    throw new Error('Open Food Facts API fetch failed');
  }

  const data = await response.json();

  return {
    source: "Open Food Facts",
    query: query,
    count: data.products?.length || 0,
    data: data.products || []
  };
};

module.exports = { fetchFromOpenFoodFacts }; 