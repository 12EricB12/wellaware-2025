// backend/mockAPI.js

// This is a mock data source to demonstrate scalability.
// It mimics a real API but just returns hardcoded data.

const fetchFromMockAPI = async (query) => {
  console.log(`[MockAPI] Searching for: ${query}`);
  
  // Simulate a network delay of 50ms
  await new Promise(resolve => setTimeout(resolve, 50));

  return {
    source: "Mock Retailer API",
    query: query,
    data: [
      {
        product_name: `Mock Product for '${query}'`,
        brand: "MockBrand",
        price: "12.99",
        in_stock: true
      }
    ]
  };
};

module.exports = { fetchFromMockAPI }; 