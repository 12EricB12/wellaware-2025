const express = require("express");
const cors = require("cors");
const app = express();
const port = 3000;

const USDA_API_KEY = "DEMO_KEY";
const BASE_URL = "https://api.nal.usda.gov/fdc/v1/foods/search";

app.use(cors());

app.get("/", (req, res) => {
  res.send("USDA Testing Server");
});

app.get("/api/food", async (req, res) => {
  const query = req.query.q;

  if (!query) {
    return res.status(400).json({ error: "Missing query" });
  }

  const url = `${BASE_URL}?api_key=${USDA_API_KEY}&query=${query}&pageSize=5`;

  try {
    const response = await fetch(url);
    if (!response.ok)
      return res.status(400).json({ error: "USDA API fetch failed" });

    const data = await response.json();
    data["foods"];
    res.json(data);
  } catch (err) {
    console.error("Error fetching from USDA:", err.message);
    res.status(500).json({ error: "Error fetching food data" });
  }
});

app.listen(port, () => {
  console.log(`Express app listening at http://localhost:${port}`);
});
