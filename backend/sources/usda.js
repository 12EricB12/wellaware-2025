// backend/sources/usda.js

const fetch = require('node-fetch');

/**
 * Fetches food data from the USDA FoodData Central API.
 * @param {string} query - The search query for food items.
 * @param {object} config - The API configuration containing the base URL and API key.
 * @returns {Promise<object>} A promise that resolves to the structured API response.
 */
const fetchFromUSDA = async (query, config) => {
  const url = `${config.USDA_BASE_URL}?api_key=${config.USDA_API_KEY}&query=${encodeURIComponent(query)}&pageSize=5`;
  
  console.log(`[USDA] Fetching data for: ${query}`);
  
  const response = await fetch(url);
  
  if (!response.ok) {
    console.error(`[USDA] API error: ${response.statusText}`);
    throw new Error('USDA API fetch failed');
  }
  
  const data = await response.json();
  
  return {
    source: "USDA FoodData Central",
    query: query,
    count: data.foods?.length || 0,
    data: data.foods || []
  };
};

module.exports = { fetchFromUSDA }; 