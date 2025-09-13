const Tesseract = require("tesseract.js");
const fs = require("fs");
const path = require("path");

/**
 * Extract text from a base64 URI string using Tesseract.js
 * @param {string} base64Uri - The base64 URI string (e.g., "data:image/png;base64,iVBORw0KGgo...")
 * @param {Object} options - OCR options
 * @returns {Promise<string>} - Extracted text
 */
async function extractTextFromBase64(base64Uri, options = {}) {
  try {
    // Validate base64 URI format
    if (!base64Uri || typeof base64Uri !== "string") {
      throw new Error("Invalid base64 URI provided");
    }

    // Check if it's a valid data URI
    if (!base64Uri.startsWith("data:")) {
      throw new Error('Invalid data URI format. Must start with "data:"');
    }

    // Extract the base64 data part (remove the data:image/...;base64, prefix)
    const base64Data = base64Uri.split(",")[1];
    if (!base64Data) {
      throw new Error("Invalid base64 data in URI");
    }

    // Default OCR options
    const defaultOptions = {
      lang: "eng", // Language for OCR
      oem: 1, // OCR Engine Mode: 1 = Neural nets LSTM engine
      psm: 3, // Page segmentation mode: 3 = Fully automatic page segmentation
      ...options,
    };

    console.log("Starting OCR processing...");
    console.log(`Language: ${defaultOptions.lang}`);
    console.log(`Engine Mode: ${defaultOptions.oem}`);
    console.log(`Page Segmentation: ${defaultOptions.psm}`);

    // Process the image with Tesseract
    const result = await Tesseract.recognize(base64Uri, defaultOptions.lang, {
      logger: (m) => {
        if (m.status === "recognizing text") {
          console.log(`Progress: ${Math.round(m.progress * 100)}%`);
        }
      },
    });

    console.log("OCR processing completed successfully!");
    return result.data.text.trim();
  } catch (error) {
    console.error("Error during OCR processing:", error.message);
    throw error;
  }
}

/**
 * Extract text from a base64 URI string with confidence scores
 * @param {string} base64Uri - The base64 URI string
 * @param {Object} options - OCR options
 * @returns {Promise<Object>} - Object containing text and confidence information
 */
async function extractTextWithConfidence(base64Uri, options = {}) {
  try {
    const defaultOptions = {
      lang: "eng",
      oem: 1,
      psm: 3,
      ...options,
    };

    console.log("Starting OCR processing with confidence analysis...");

    const result = await Tesseract.recognize(base64Uri, defaultOptions.lang, {
      logger: (m) => {
        if (m.status === "recognizing text") {
          console.log(`Progress: ${Math.round(m.progress * 100)}%`);
        }
      },
    });

    // Extract confidence information
    const confidence = result.data.confidence;
    const words = result.data.words || [];
    const lines = result.data.lines || [];

    console.log("OCR processing completed with confidence analysis!");

    return {
      text: result.data.text.trim(),
      confidence: confidence,
      wordCount: words.length,
      lineCount: lines.length,
      words: words.map((word) => ({
        text: word.text,
        confidence: word.confidence,
        bbox: word.bbox,
      })),
      lines: lines.map((line) => ({
        text: line.text,
        confidence: line.confidence,
        bbox: line.bbox,
      })),
    };
  } catch (error) {
    console.error(
      "Error during OCR processing with confidence:",
      error.message
    );
    throw error;
  }
}

/**
 * Save base64 URI to a temporary file and process it
 * @param {string} base64Uri - The base64 URI string
 * @param {string} outputPath - Output file path
 * @param {Object} options - OCR options
 * @returns {Promise<string>} - Extracted text
 */
async function extractTextFromBase64File(base64Uri, outputPath, options = {}) {
  try {
    // Extract the base64 data part
    const base64Data = base64Uri.split(",")[1];
    if (!base64Data) {
      throw new Error("Invalid base64 data in URI");
    }

    // Convert base64 to buffer
    const imageBuffer = Buffer.from(base64Data, "base64");

    // Ensure output directory exists
    const outputDir = path.dirname(outputPath);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    // Write buffer to file
    fs.writeFileSync(outputPath, imageBuffer);
    console.log(`Image saved to: ${outputPath}`);

    // Process the saved file
    const result = await Tesseract.recognize(
      outputPath,
      options.lang || "eng",
      {
        logger: (m) => {
          if (m.status === "recognizing text") {
            console.log(`Progress: ${Math.round(m.progress * 100)}%`);
          }
        },
      }
    );

    // Clean up temporary file
    fs.unlinkSync(outputPath);
    console.log("Temporary file cleaned up");

    return result.data.text.trim();
  } catch (error) {
    console.error("Error processing base64 file:", error.message);
    throw error;
  }
}

/**
 * Example usage and testing function
 */
async function testOCR() {
  try {
    // Example base64 URI (you would replace this with your actual base64 string)
    const filePath = "serum.jpeg";

    if (!fs.existsSync(filePath)) {
      console.log(
        `⚠️  Test image "${filePath}" not found. Please add an image file to test with.`
      );
      return;
    }

    const imageBlob = fs.readFileSync(filePath);
    const mimeType = "image/jpeg";
    console.log(`File size: ${imageBlob.length} bytes`);
    console.log(`MIME type: ${mimeType}`);

    // Check if image data is valid
    if (imageBlob.length === 0) {
      console.log("❌ Image file is empty");
      return;
    }

    // Test if the image can be read as a buffer
    console.log("Testing image buffer...");
    try {
      const testBuffer = Buffer.from(imageBlob);
      console.log("✅ Buffer created successfully");
      console.log("Buffer length:", testBuffer.length);
    } catch (bufferError) {
      console.log("❌ Buffer creation failed:", bufferError.message);
      return;
    }

    const base64ImageUri = `data:${mimeType};base64,${Buffer.from(
      imageBlob
    ).toString("base64")}`;

    console.log("=== Testing Basic OCR with file path ===");
    const basicText = await Tesseract.recognize(filePath, "eng");
    console.log("Extracted text:", basicText.data.text);

    console.log("\n=== Testing OCR with Confidence ===");
    const detailedResult = await Tesseract.recognize(filePath, "eng");
    console.log("Confidence:", detailedResult.data.confidence);
    console.log("Word count:", detailedResult.data.words?.length || 0);
    console.log("Line count:", detailedResult.data.lines?.length || 0);
  } catch (error) {
    console.error("Test failed:", error.message);
  }
}

// Export functions for use in other modules
module.exports = {
  extractTextFromBase64,
  extractTextWithConfidence,
  extractTextFromBase64File,
  testOCR,
};

// Run test if this file is executed directly
if (require.main === module) {
  testOCR();
}
