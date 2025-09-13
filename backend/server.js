// backend/server.js

const express = require("express");
const cors = require("cors");
const fetch = require("node-fetch"); // Ensure node-fetch is a dependency
const { exec } = require("child_process");
const path = require("path");
const fs = require("fs");
const multer = require("multer");
const { createWorker } = require("tesseract.js");
const { MongoClient } = require("mongodb");

// --- Import individual source fetchers ---
const { fetchFromUSDA } = require("./sources/usda");
const { fetchFromOpenFoodFacts } = require("./sources/openFoodFacts");
const { fetchFromMockAPI } = require("./sources/mockAPI");

const dotenv = require("dotenv");
const { textChangeRangeIsUnchanged } = require("typescript");
dotenv.config();

// =================================================================
// 1. CENTRALIZED CONFIGURATION
// =================================================================
const config = {
  server: {
    port: process.env.PORT || 3000,
  },
  api: {
    USDA_API_KEY: process.env.USDA_API_KEY || "DEMO_KEY",
    USDA_BASE_URL: "https://api.nal.usda.gov/fdc/v1/foods/search",
    OFF_BASE_URL: "https://world.openfoodfacts.org/cgi/search.pl",
  },
  scraper: {
    scriptPath: path.join(__dirname, "open_food_facts_scraper.py"),
    dataDir: path.join(__dirname, "data", "food"),
    logPath: path.join(__dirname, "scraper.log"),
  },
  mongodb: {
    uri: process.env.ATLAS_URI || process.env.ATLAS_URI,
    dbName: process.env.DB_NAME || "wellaware",
  },
};

// =================================================================
// 2. MONGODB CONNECTION
// =================================================================
let db;
let client;

async function connectToMongoDB() {
  try {
    client = new MongoClient(config.mongodb.uri);
    await client.connect();
    db = client.db(config.mongodb.dbName);
    console.log("✅ Connected to MongoDB successfully");

    // Test the connection
    await db.admin().ping();
    console.log("✅ MongoDB ping successful");

    return db;
  } catch (error) {
    console.error("❌ MongoDB connection failed:", error);
    throw error;
  }
}

// Initialize MongoDB connection
connectToMongoDB().catch(console.error);

// Graceful shutdown
process.on("SIGINT", async () => {
  if (client) {
    await client.close();
    console.log("MongoDB connection closed");
  }
  process.exit(0);
});

// =================================================================
// 3. MULTER CONFIGURATION FOR FILE UPLOADS
// =================================================================
const storage = multer.memoryStorage();
const upload = multer({
  storage: storage,
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB limit
  },
  fileFilter: (req, file, cb) => {
    // Accept only image files
    if (file.mimetype.startsWith("image/")) {
      cb(null, true);
    } else {
      cb(new Error("Only image files are allowed"), false);
    }
  },
});

// =================================================================
// 4. SOURCE REGISTRY PATTERN
// =================================================================
/**
 * A registry mapping source names to their respective data fetching functions.
 * This allows for easy addition of new sources without changing the main search logic.
 */
const sourceRegistry = {
  usda: (query) => fetchFromUSDA(query, config.api),
  openfoodfacts: (query) => fetchFromOpenFoodFacts(query, config.api),
  mock: (query) => fetchFromMockAPI(query, config.api), // mockAPI is self-contained
};

const app = express();
app.use(cors());
app.use(express.json());

// =================================================================
// 5. API ENDPOINTS & HELPER FUNCTIONS
// =================================================================

/**
 * Root endpoint providing an overview of the API.
 */
app.get("/", (req, res) => {
  res.json({
    message: "WellAware Food Data API - Refactored",
    description: "A unified API for searching multiple food data sources.",
    endpoints: {
      search: "/api/food/search?q={query}&sources={source1,source2}",
      scraperRun: "POST /api/scraper/run",
      scraperStatus: "/api/scraper/status",
      latestData: "/api/data/latest",
      dbStatus: "/api/db/status",
      dbFood: {
        create: "POST /api/db/food",
        read: "GET /api/db/food",
        readOne: "GET /api/db/food/:id",
        update: "PUT /api/db/food/:id",
        delete: "DELETE /api/db/food/:id",
        bulkImport: "POST /api/db/bulk-import",
      },
    },
    availableSources: Object.keys(sourceRegistry),
    database: "MongoDB",
  });
});

// --- Unified Search Endpoint ---

/**
 * Parses and validates search request parameters.
 * @param {object} req - The Express request object.
 * @returns {{query: string, requestedSources: string[]}}
 * @throws {Error} if the query parameter is missing.
 */
function parseSearchParams(req) {
  const { q: query, sources } = req.query;
  console.log(sources);

  if (!query) {
    throw new Error("Query parameter 'q' is required.");
  }

  const allSources = Object.keys(sourceRegistry);
  const requestedSources = sources
    ? sources.split(",").filter((s) => {
        return allSources.includes(s);
      })
    : allSources;
  return { query, requestedSources };
}

/**
 * Fetches data from all requested sources in parallel.
 * @param {string} query - The search term.
 * @param {string[]} requestedSources - An array of source names to query.
 * @returns {Promise<object>} A promise that resolves to an aggregated results object.
 */
async function fetchAllSources(query, requestedSources) {
  console.log(`Executing search for "${query}" across sources: []`);

  const promises = requestedSources.map((sourceName) => {
    const fetcher = sourceRegistry[sourceName];
    return fetcher(query).catch((error) => ({
      source: sourceName,
      status: "error",
      reason: error.message,
    }));
  });

  const results = await Promise.allSettled(promises);

  const aggregatedResults = {
    query: query,
    sources: {},
  };

  results.forEach((result, index) => {
    const sourceName = requestedSources[index];
    if (result.status === "fulfilled") {
      // If the promise was fulfilled, it might still be a custom error object from our catch block
      if (result.value.status === "error") {
        aggregatedResults.sources[sourceName] = {
          status: "error",
          reason: result.value.reason,
        };
      } else {
        aggregatedResults.sources[sourceName] = {
          status: "success",
          ...result.value,
        };
      }
    } else {
      // The promise was rejected (e.g., network failure, code error)
      aggregatedResults.sources[sourceName] = {
        status: "error",
        reason: result.reason.message || "An unknown error occurred",
      };
    }
  });

  return aggregatedResults;
}

/**
 * @route GET /api/food/search
 * @description The main endpoint to search for food data across multiple sources.
 * It uses a "source registry" for scalability.
 * @param {string} q - The search query.
 * @param {string} [sources] - A comma-separated list of sources to query (e.g., "usda,openfoodfacts").
 * Defaults to all available sources if not provided.
 */
app.get("/api/food/search", async (req, res) => {
  try {
    const { query, requestedSources } = parseSearchParams(req);
    const results = await fetchAllSources(query, requestedSources);
    res.json(results);
  } catch (error) {
    res.status(400).json({ error: true, message: error.message });
  }
});

// --- Scraper Control Endpoints ---

/**
 * @route POST /api/scraper/run
 * @description Triggers the Python scraper to run as a background process.
 */
app.post("/api/scraper/run", (req, res) => {
  const { max_pages = 5 } = req.body;
  const command = `python "${config.scraper.scriptPath}" --max_pages ${max_pages}`;

  console.log(`Executing scraper with command: ${command}`);

  exec(command, { cwd: __dirname }, (error, stdout, stderr) => {
    if (error) {
      console.error(`Scraper execution error: ${error.message}`);
      return res.status(500).json({
        error: true,
        message: "Scraper execution failed",
        details: error.message,
      });
    }
    if (stderr) {
      console.warn(`Scraper stderr: ${stderr}`);
    }
    res.json({
      success: true,
      message: "Scraper executed successfully.",
      output: stdout,
    });
  });
});

/**
 * @route GET /api/scraper/status
 * @description Provides the status of the scraper, including recent logs and last scrape info.
 */
app.get("/api/scraper/status", (req, res) => {
  try {
    const status = {
      scraperScriptExists: fs.existsSync(config.scraper.scriptPath),
      lastScrapeInfo: null,
      recentLogs: [],
    };

    // Check for latest scraped file
    if (fs.existsSync(config.scraper.dataDir)) {
      const files = fs
        .readdirSync(config.scraper.dataDir)
        .filter(
          (file) =>
            file.startsWith("open_food_facts_products_") &&
            file.endsWith(".json")
        )
        .sort();

      if (files.length > 0) {
        const latestFile = files[files.length - 1];
        const fileContents = fs.readFileSync(
          path.join(config.scraper.dataDir, latestFile),
          "utf8"
        );
        const data = JSON.parse(fileContents);
        status.lastScrapeInfo = {
          filename: latestFile,
          scrapeDate: data.metadata?.scrape_date,
          totalProducts: data.metadata?.total_products,
        };
      }
    }

    // Read recent logs
    if (fs.existsSync(config.scraper.logPath)) {
      const logContent = fs.readFileSync(config.scraper.logPath, "utf8");
      status.recentLogs = logContent.split("\n").filter(Boolean).slice(-20);
    }

    res.json(status);
  } catch (error) {
    res.status(500).json({
      error: true,
      message: "Failed to get scraper status.",
      details: error.message,
    });
  }
});

// --- MongoDB Database Endpoints ---

/**
 * @route GET /api/db/status
 * @description Get MongoDB connection status and database info
 */
app.get("/api/db/status", async (req, res) => {
  try {
    if (!db) {
      return res.status(503).json({
        error: true,
        message: "Database not connected",
        status: "disconnected",
      });
    }

    const collections = await db.listCollections().toArray();
    const stats = await db.stats();

    res.json({
      status: "connected",
      database: config.mongodb.dbName,
      collections: collections.map((col) => col.name),
      stats: {
        collections: stats.collections,
        dataSize: stats.dataSize,
        storageSize: stats.storageSize,
        indexes: stats.indexes,
      },
    });
  } catch (error) {
    res.status(500).json({
      error: true,
      message: "Failed to get database status",
      details: error.message,
    });
  }
});

/**
 * @route POST /api/db/food
 * @description Save food data to MongoDB
 */
app.post("/api/db/food", async (req, res) => {
  try {
    if (!db) {
      return res.status(503).json({
        error: true,
        message: "Database not connected",
      });
    }

    const foodData = req.body;
    if (!foodData.name || !foodData.source) {
      return res.status(400).json({
        error: true,
        message: "Food name and source are required",
      });
    }

    // Add timestamp
    foodData.createdAt = new Date();
    foodData.updatedAt = new Date();

    const collection = db.collection("foods");
    const result = await collection.insertOne(foodData);

    res.json({
      success: true,
      message: "Food data saved successfully",
      id: result.insertedId,
    });
  } catch (error) {
    res.status(500).json({
      error: true,
      message: "Failed to save food data",
      details: error.message,
    });
  }
});

/**
 * @route GET /api/db/food
 * @description Get food data from MongoDB with optional filtering
 */
app.get("/api/db/food", async (req, res) => {
  try {
    if (!db) {
      return res.status(503).json({
        error: true,
        message: "Database not connected",
      });
    }

    const { query, source, limit = 50, skip = 0 } = req.query;
    const filter = {};

    if (query) {
      filter.$or = [
        { name: { $regex: query, $options: "i" } },
        { description: { $regex: query, $options: "i" } },
        { brand: { $regex: query, $options: "i" } },
      ];
    }

    if (source) {
      filter.source = source;
    }

    const collection = db.collection("foods");
    const foods = await collection
      .find(filter)
      .sort({ createdAt: -1 })
      .skip(parseInt(skip))
      .limit(parseInt(limit))
      .toArray();

    const total = await collection.countDocuments(filter);

    res.json({
      success: true,
      data: foods,
      pagination: {
        total,
        limit: parseInt(limit),
        skip: parseInt(skip),
        hasMore: total > parseInt(skip) + foods.length,
      },
    });
  } catch (error) {
    res.status(500).json({
      error: true,
      message: "Failed to retrieve food data",
      details: error.message,
    });
  }
});

function isNullOrEmpty(value) {
  return (
    value === null ||
    value === undefined ||
    (typeof value === "string" && value.trim() === "")
  );
}

/**
 * @route GET /api/db/food/:id
 * @description Get specific food item by ID
 */
// Searches the MongoDB database, returning the number of specified most promising fuzzy search matches.
const searchDB = async (text, numResults, processingType = "basic") => {
  try {
    // Basic processing only searches by line.
    // Complete search is a "last resort" search, uses all available information to search the brand and the product name instead of just the product name
    basicProcessingName = "basic";
    completeProcessingName = "complete";

    if (!db) {
      return null;
    }

    const collection = db.collection("products");
    // Start with searching through the brand field, then the product field
    let splitText = text.split("\n");

    for (i = 0; i < splitText.length; i++) {
      splitText[i] = splitText[i].replace(/[^a-zA-Z0-9/" "-]/g, "");
      splitText[i] = splitText[i].replace(/\s+/g, " ");
    }

    let res = [];

    // Fuzzy search products by name only, only keeping the two most promising results
    for (i = 0; i < splitText.length; i++) {
      if (isNullOrEmpty(splitText[i])) {
        continue;
      }
      const results = await db
        .collection("products")
        .aggregate([
          {
            $search: {
              index: "productSearch",
              text: {
                query: splitText[i],
                path: "productName",
                fuzzy: { maxEdits: 2 },
              },
            },
          },
          {
            $addFields: { score: { $meta: "searchScore" } },
          },
          { $sort: { score: -1 } },
          { $limit: 2 },
        ])
        .toArray();

      if (results.length > 0) {
        res = [...res, ...results];
        res.sort((a, b) => b.score - a.score);
      }
    }

    if (processingType === completeProcessingName && res.length == 0) {
      let all_candidates = [];
      for (i = 0; i < splitText.length; i++) {
        for (j = 0; j < splitText.length; j++) {
          if (
            splitText[i] != splitText[j] &&
            !isNullOrEmpty(splitText[i]) &&
            !isNullOrEmpty(splitText[j])
          ) {
            all_candidates.push([splitText[i], splitText[j]]);
          }
        }
      }

      // Fuzzy search all brands with their respective products, only keeping the two most promising results
      for (i = 0; i < all_candidates.length; i++) {
        const results = await db
          .collection("products")
          .aggregate([
            {
              $search: {
                index: "productSearch",
                compound: {
                  should: [
                    {
                      text: {
                        query: all_candidates[i][0],
                        path: "brand",
                        fuzzy: { maxEdits: 2 },
                      },
                    },
                    {
                      text: {
                        query: all_candidates[i][1],
                        path: "productName",
                        fuzzy: { maxEdits: 2 },
                      },
                    },
                  ],
                },
              },
            },
            {
              $addFields: { score: { $meta: "searchScore" } },
            },
            { $sort: { score: -1 } },
            { $limit: 2 },
          ])
          .toArray();

        if (results.length > 0) {
          res = [...res, ...results];
          res.sort((a, b) => b.score - a.score);
        }
      }
    }

    res = res.slice(0, numResults);
    return res;
  } catch (error) {
    console.error("SearchDB error:", error);
    return null;
  }
  // --------------------FASTEST ALGORITHM------------------------
  // Simply searches line by line and checks for a match in the database without fuzzy search.
  // If extra processing is desired, each line is also checked for a brand match to narrow down results.
  // This algorithm isn't very accurate, so I'm leaving it here just in case we need a faster approach.
  // IF USED: Put this search algorithm before all the fuzzy searching in the try statement, and only use fuzzy search if no results are returned.
  // -------------------------------------------------------------
  // Perform 2 searches using two algorithms to maximize the chances of getting a result
  // First search: Search by line, finding items that contain the word
  // for (i = 0; i < splitText.length; i++) {
  //   let query = splitText[i];
  //   // Whitespace check
  //   if (query.toLowerCase() == "") {
  //     continue;
  //   }
  //   const food = await collection
  //     .find({
  //       productName: {
  //         $regex: `(^|\\s)${query.toLowerCase()}(\\s|$)`,
  //       },
  //     })
  //     .limit(5)
  //     .toArray();

  //   // If the product name isn't a significant part of the query, discard it (it is probably gibberish)
  //   const foodFiltered = food
  //     .filter(
  //       (f) =>
  //         f.productName.toLowerCase().includes(query.toLowerCase()) &&
  //         query.length / f.productName.length > 0.1
  //     )
  //     .sort((a, b) => {
  //       const ratioA = query.length / a.productName.length;
  //       const ratioB = query.length / b.productName.length;
  //       return ratioB - ratioA; // Descending order (highest to lowest)
  //     });
  //   if (foodFiltered.length > 0) {
  //     res = [...res, ...foodFiltered];
  //   }
  // }

  // // Further refine results if processing is complete
  // if (processingType === completeProcessingName) {
  //   resBrands = [];
  //   // Get brand overlap if we can find it
  //   for (i = 0; i < res.length; i++) {
  //     for (j = 0; j < splitText.length; j++) {
  //       extractedBrand = splitText[j].toLowerCase();
  //       resBrand = res[i].brand;

  //       if (resBrand == null || resBrand == undefined) {
  //         continue;
  //       }

  //       if (extractedBrand.equals === resBrand) {
  //         resBrands.push(res[i]);
  //       }
  //     }
  //   }
  //   // Preffered results from brand overlap come first
  //   if (resBrands.length > 0) {
  //     res = [...resBrands, ...res];
  //   }
  // }
};

/**
 * @route PUT /api/db/food/:id
 * @description Update food data in MongoDB
 */
app.put("/api/db/food/:id", async (req, res) => {
  try {
    if (!db) {
      return res.status(503).json({
        error: true,
        message: "Database not connected",
      });
    }

    const { ObjectId } = require("mongodb");
    const id = req.params.id;
    const updateData = req.body;

    if (!ObjectId.isValid(id)) {
      return res.status(400).json({
        error: true,
        message: "Invalid ID format",
      });
    }

    // Add update timestamp
    updateData.updatedAt = new Date();

    const collection = db.collection("foods");
    const result = await collection.updateOne(
      { _id: new ObjectId(id) },
      { $set: updateData }
    );

    if (result.matchedCount === 0) {
      return res.status(404).json({
        error: true,
        message: "Food item not found",
      });
    }

    res.json({
      success: true,
      message: "Food data updated successfully",
      modifiedCount: result.modifiedCount,
    });
  } catch (error) {
    res.status(500).json({
      error: true,
      message: "Failed to update food data",
      details: error.message,
    });
  }
});

// --- OCR Image Processing Endpoints ---

/**
 * @route GET /api/ocr/config
 * @description Get information about available OCR configuration options
 */
app.get("/api/ocr/config", (req, res) => {
  res.json({
    message: "OCR Configuration Options",
    description:
      "Available settings to adjust OCR sensitivity, accuracy, and processing behavior",
    settings: {
      lang: {
        description: "Language for OCR processing",
        default: "eng",
        options: [
          "eng",
          "fra",
          "deu",
          "spa",
          "ita",
          "por",
          "rus",
          "chi_sim",
          "jpn",
          "kor",
        ],
        effect: "Better accuracy for the specified language",
      },
      oem: {
        description: "OCR Engine Mode",
        default: 3,
        options: [
          {
            value: 0,
            name: "Legacy engine only",
            effect: "Fastest, but less accurate",
          },
          {
            value: 1,
            name: "Neural nets LSTM engine only",
            effect: "Most accurate, slower",
          },
          {
            value: 2,
            name: "Legacy + LSTM engines",
            effect: "Balanced approach",
          },
          {
            value: 3,
            name: "Default",
            effect: "Automatically selects best available",
          },
        ],
      },
      psm: {
        description: "Page Segmentation Mode",
        default: 3,
        options: [
          {
            value: 0,
            name: "OSD only",
            effect: "Orientation and script detection",
          },
          {
            value: 1,
            name: "Automatic with OSD",
            effect: "Full page analysis with orientation detection",
          },
          {
            value: 3,
            name: "Fully automatic",
            effect: "Default - good for most documents",
          },
          {
            value: 6,
            name: "Uniform block",
            effect: "Good for single text blocks",
          },
          {
            value: 7,
            name: "Single line",
            effect: "Good for single lines of text",
          },
          {
            value: 8,
            name: "Single word",
            effect: "Good for individual words",
          },
          {
            value: 9,
            name: "Single word in a circle",
            effect: "Good for individual words",
          },
          {
            value: 10,
            name: "Single character",
            effect: "Good for individual characters",
          },
          {
            value: 11,
            name: "Sparse text with OSD",
            effect: "Good for sparse text layouts",
          },
          {
            value: 12,
            name: "Sparse text uniform",
            effect: "Good for sparse text in uniform blocks",
          },
          {
            value: 13,
            name: "Raw line",
            effect: "Raw text line with any orientation",
          },
        ],
      },
      confidence: {
        description: "Confidence threshold (0-100)",
        default: 0,
        effect:
          "Only return text with confidence above this value. Higher values = more accurate but fewer results",
      },
      preserveSpaces: {
        description: "Preserve interword spaces",
        default: false,
        effect: "Maintain spacing between words for better readability",
      },
      dpi: {
        description: "DPI (dots per inch)",
        default: 300,
        options: [72, 150, 200, 300, 400, 600],
        effect:
          "Higher DPI = better accuracy but slower processing. 300 is usually optimal",
      },
      timeout: {
        description: "Processing timeout in seconds",
        default: 30,
        effect: "Maximum time allowed for OCR processing",
      },
      processingType: {
        description:
          "Select whether greater product selection range/refinement is desired. Two options: 'basic' or 'complete'",
        default: "basic",
        effect:
          "Complete allows for a greater range of products to be selected from only if no products are found at first, but is usually slower",
      },
      responseNumber: {
        description: "Max number of products returned from the search",
        default: 10,
      },
    },
    usage: {
      example: "/api/ocr/process?confidence=70&psm=6&dpi=400",
      description: "Add query parameters to customize OCR behavior",
    },
    recommendations: {
      high_accuracy: {
        description: "For maximum accuracy",
        settings: "oem=1&psm=1&confidence=60&dpi=400",
      },
      fast_processing: {
        description: "For speed over accuracy",
        settings: "oem=0&psm=3&confidence=0&dpi=200",
      },
      product_labels: {
        description: "For product labels and UPC codes",
        settings: "oem=1&psm=8&confidence=50&dpi=300",
      },
      document_text: {
        description: "For document text extraction",
        settings: "oem=1&psm=1&confidence=40&dpi=300",
      },
    },
  });
});

/**
 * @route POST /api/ocr/process
 * @description Upload an image and process it with Tesseract OCR
 */
app.post("/api/ocr/process", upload.single("image"), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        error: true,
        message: "No image file provided",
      });
    }

    // Get OCR configuration from query parameters or use defaults
    const ocrConfig = {
      // Language settings
      lang: req.query.lang || "eng",

      // OCR Engine Mode (0-3)
      // 0: Legacy engine only
      // 1: Neural nets LSTM engine only
      // 2: Legacy + LSTM engines
      // 3: Default, based on what is available
      oem: parseInt(req.query.oem) || 3,

      // Page Segmentation Mode (0-13)
      // 0: Orientation and script detection (OSD) only
      // 1: Automatic page segmentation with OSD
      // 3: Fully automatic page segmentation, but no OSD (default)
      // 6: Uniform block of text
      // 7: Single text line
      // 8: Single word
      // 9: Single word in a circle
      // 10: Single character
      // 11: Sparse text with OSD
      // 12: Sparse text with uniform block
      // 13: Raw line with any orientation
      psm: parseInt(req.query.psm) || 3,

      // Confidence threshold (0-100)
      // Only return text with confidence above this value
      confidence: parseInt(req.query.confidence) || 0,

      // Preserve interword spaces
      preserveInterwordSpaces: req.query.preserveSpaces === "true",

      // DPI (dots per inch) - affects image scaling
      dpi: parseInt(req.query.dpi) || 300,

      // Timeout for OCR processing (in seconds)
      timeout: parseInt(req.query.timeout) || 30,

      // Processing type
      processingType: req.query.processingType,

      // Number of responses
      responseNumber: parseInt(req.query.responseNumber),
    };

    console.log(
      `Processing image: ${req.file.originalname} (${req.file.size} bytes)`
    );
    console.log(`MIME type: ${req.file.mimetype}`);
    console.log(`Field name: ${req.file.fieldname}`);
    console.log(`OCR Config:`, ocrConfig);

    // Validate file size
    if (req.file.size > 10 * 1024 * 1024) {
      // 10MB limit
      return res.status(400).json({
        error: true,
        message: "File too large. Maximum size is 10MB.",
      });
    }

    // Validate MIME type more strictly
    const allowedMimeTypes = [
      "image/jpeg",
      "image/jpg",
      "image/png",
      "image/gif",
      "image/bmp",
      "image/webp",
    ];

    if (!allowedMimeTypes.includes(req.file.mimetype)) {
      return res.status(400).json({
        error: true,
        message: `Unsupported image format: ${req.file.mimetype}. Supported formats: JPEG, PNG, GIF, BMP, WebP`,
      });
    }

    // Validate that we have buffer data
    if (!req.file.buffer || req.file.buffer.length === 0) {
      return res.status(400).json({
        error: true,
        message: "Invalid image data received",
      });
    }

    console.log(`Image buffer size: ${req.file.buffer.length} bytes`);

    // Log the first few bytes to help debug format issues
    const firstBytes = req.file.buffer.slice(0, 16);
    console.log(
      `First 16 bytes: ${Array.from(firstBytes)
        .map((b) => b.toString(16).padStart(2, "0"))
        .join(" ")}`
    );

    // Check if buffer contains valid image data
    if (
      req.file.mimetype === "image/png" &&
      !req.file.buffer
        .slice(0, 8)
        .equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))
    ) {
      console.warn("Warning: PNG header signature not found in buffer");
    } else if (
      req.file.mimetype === "image/jpeg" &&
      !(req.file.buffer[0] === 0xff && req.file.buffer[1] === 0xd8)
    ) {
      console.warn("Warning: JPEG header signature not found in buffer");
    }

    // Create Tesseract worker with error handling and custom configuration
    let worker;
    try {
      worker = await createWorker(ocrConfig.lang, ocrConfig.oem, {
        logger: (m) => console.log(m),
        // Set worker options
        workerOptions: {
          // Set page segmentation mode
          tessedit_pageseg_mode: ocrConfig.psm,
          // Set OCR engine mode
          tessedit_ocr_engine_mode: ocrConfig.oem,
          // Set DPI
          tessedit_pix_x: ocrConfig.dpi,
          tessedit_pix_y: ocrConfig.dpi,
          // Preserve interword spaces
          preserve_interword_spaces: ocrConfig.preserveInterwordSpaces
            ? "1"
            : "0",
          // Set confidence threshold
          tessedit_min_confidence: ocrConfig.confidence.toString(),
          // Additional accuracy settings
          tessedit_char_whitelist: "", // Allow all characters
          tessedit_char_blacklist: "", // No blacklisted characters
          // Text layout analysis
          textord_heavy_nr: "1", // Heavy noise removal
          textord_min_linesize: "2.0", // Minimum line size
          // Language model settings
          language_model_penalty_non_dict_word: "0.15", // Penalty for non-dictionary words
          language_model_penalty_non_freq_dict_word: "0.1", // Penalty for non-frequent dictionary words
        },
      });
    } catch (workerError) {
      console.error("Failed to create Tesseract worker:", workerError);
      return res.status(500).json({
        error: true,
        message: "Failed to initialize OCR engine",
        details: workerError.message,
      });
    }

    try {
      // Process the image with OCR and timeout
      const ocrPromise = worker.recognize(req.file.buffer);
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(
          () => reject(new Error("OCR processing timeout")),
          ocrConfig.timeout * 1000
        )
      );

      const {
        data: { text, confidence, words },
      } = await Promise.race([ocrPromise, timeoutPromise]);

      // Extract potential UPC codes or product identifiers
      const extractedText = text.trim();
      console.log(`EXTRACTED TEXT: ${extractedText}`);
      // Start by searching the database for candidate results for both the brand and the product
      const mongoDBRes = await searchDB(
        extractedText,
        ocrConfig.responseNumber,
        ocrConfig.processingType
      );
      if (mongoDBRes != null) {
        console.log("DONE SEARCHING: Products found!");
      } else {
        console.log("DONE SEARCHING: No products found");
      }

      const wordsList = extractedText.split(/\s+/);

      // Filter words based on confidence threshold if specified
      let potentialUpcs = [];
      if (ocrConfig.confidence > 0) {
        // Filter words by confidence level
        const confidentWords = words.filter(
          (word) => word.confidence >= ocrConfig.confidence
        );
        potentialUpcs = confidentWords
          .map((word) => word.text)
          .filter((word) => word.length >= 8 && /^\d+$/.test(word));
      } else {
        // Use all words for UPC detection
        potentialUpcs = wordsList.filter(
          (word) => word.length >= 8 && /^\d+$/.test(word)
        );
      }

      // Get additional OCR data
      const ocrData = {
        text: extractedText,
        confidence: confidence,
        wordCount: wordsList.length,
        potentialUpcs: potentialUpcs,
        filename: req.file.originalname,
        fileSize: req.file.size,
        mimeType: req.file.mimetype,
        // Include the configuration used
        config: ocrConfig,
        // Include detailed word information if confidence filtering was used
        words:
          ocrConfig.confidence > 0
            ? words.map((w) => ({
                text: w.text,
                confidence: w.confidence,
                bbox: w.bbox,
              }))
            : undefined,
      };

      console.log(
        `OCR completed successfully. Extracted ${
          wordsList.length
        } words with confidence ${confidence.toFixed(2)}%.`
      );

      res.json({
        success: true,
        data: mongoDBRes,
      });
    } catch (ocrError) {
      console.error("OCR processing error:", ocrError);

      // Provide more specific error messages
      let errorMessage = "OCR processing failed";
      const errorMsg = ocrError.message || String(ocrError);

      if (errorMsg.includes("Unknown format")) {
        errorMessage =
          "Image format not recognized. Please try a different image.";
      } else if (errorMsg.includes("no pix returned")) {
        errorMessage =
          "Image could not be processed. Please try a clearer image.";
      } else if (errorMsg.includes("timeout")) {
        errorMessage =
          "OCR processing took too long. Try a smaller image or increase timeout.";
      }

      res.status(500).json({
        error: true,
        message: errorMessage,
        details: errorMsg,
      });
    } finally {
      // Always terminate the worker
      try {
        if (worker) {
          await worker.terminate();
          console.log("Worker terminated successfully");
        }
      } catch (terminateError) {
        console.error("Error terminating worker:", terminateError);
      }
    }
  } catch (error) {
    console.error("Unexpected error in OCR endpoint:", error);
    res.status(500).json({
      error: true,
      message: "Unexpected server error",
      details: error.message,
    });
  }
});

/**
 * @route POST /api/ocr/process-with-data
 * @description Upload an image with additional form data and process with OCR
 */
app.post(
  "/api/ocr/process-with-data",
  upload.single("image"),
  async (req, res) => {
    try {
      if (!req.file) {
        return res.status(400).json({
          error: true,
          message: "No image file provided",
        });
      }

      const additionalData = req.body.additionalData || null;
      console.log(
        `Processing image with additional data: ${req.file.originalname}`
      );

      // Create Tesseract worker
      const worker = await createWorker("eng", 1, {
        logger: (m) => console.log(m),
      });

      try {
        // Process the image with OCR
        const {
          data: { text, confidence, words },
        } = await worker.recognize(req.file.buffer);

        // Extract potential UPC codes or product identifiers
        const extractedText = text.trim();
        const wordsList = extractedText.split(/\s+/);
        const potentialUpcs = wordsList.filter(
          (word) => word.length >= 8 && /^\d+$/.test(word)
        );

        // Get additional OCR data
        const ocrData = {
          text: extractedText,
          confidence: confidence,
          wordCount: wordsList.length,
          potentialUpcs: potentialUpcs,
          additionalData: additionalData,
          filename: req.file.originalname,
          fileSize: req.file.size,
          mimeType: req.file.mimetype,
        };

        console.log(
          `OCR completed successfully. Extracted ${wordsList.length} words.`
        );

        res.json({
          success: true,
          data: ocrData,
        });
      } finally {
        // Always terminate the worker
        await worker.terminate();
      }
    } catch (error) {
      console.error("OCR processing error:", error);
      res.status(500).json({
        error: true,
        message: "OCR processing failed",
        details: error.message,
      });
    }
  }
);

// --- Server Initialization ---

// Global error handlers to prevent crashes
process.on("uncaughtException", (error) => {
  console.error("Uncaught Exception:", error);
  // Don't exit the process, just log the error
});

process.on("unhandledRejection", (reason, promise) => {
  console.error("Unhandled Rejection at:", promise, "reason:", reason);
  // Don't exit the process, just log the error
});

app.listen(config.server.port, "0.0.0.0", () => {
  console.log(
    `🚀 WellAware API server listening on http://localhost:${config.server.port} and http://${process.env.LAN_IP_ADDRESS}:${config.server.port}`
  );
  console.log(
    `✅ Available sources: ${Object.keys(sourceRegistry).join(", ")}`
  );
});
