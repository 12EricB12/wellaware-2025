import React, { useState, useRef } from "react";
import {
  View,
  StyleSheet,
  Text,
  TouchableOpacity,
  Image,
  Dimensions,
  Alert,
  ActivityIndicator,
  ScrollView,
  Linking,
  Platform,
} from "react-native";
import Checkbox from "expo-checkbox";
import { CameraView, useCameraPermissions, FlashMode } from "expo-camera";
import { BlurView } from "expo-blur";
import Ionicons from "@expo/vector-icons/Ionicons";
import * as ImagePicker from "expo-image-picker";
import { router } from "expo-router";
import {
  Button,
  Dialog,
  Portal,
  Provider,
  TextInput,
} from "react-native-paper";
import { SafeAreaView } from "react-native-safe-area-context";

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get("window");
const frameWidth = 334;
const frameHeight = 391;

// OCR Configuration interface
interface OcrConfig {
  confidence: number;
  psm: number;
  dpi: number;
  timeout: number;
  preserveSpaces: boolean;
  oem: number;
  tessedit_char_whitelist: string;
  processing_type: string;
  response_number: number;
}

export default function CameraScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [flash, setFlash] = useState<FlashMode>("off");
  const [activeButton, setActiveButton] = useState<"photo" | "barcode">(
    "photo"
  );
  const [facing, setFacing] = useState<"back" | "front">("back");
  const [image, setImage] = useState<string | null>(null);
  const [isCameraReady, setIsCameraReady] = useState(false);
  const [visible, setVisible] = useState(false);
  const [scannedBarcode, setScannedBarcode] = useState<{
    type: string;
    data: string;
  } | null>(null);
  const [ocrResult, setOcrResult] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const cameraRef = useRef<CameraView | null>(null);
  const [currentProduct, setCurrentProduct] = useState(0);
  const [completeModeChecked, setCompleteModeChecked] = useState(false);
  const [ipAddress, setIpAddress] = useState("");

  // OCR Configuration state
  const [ocrConfig, setOcrConfig] = useState<OcrConfig>({
    confidence: 0,
    psm: 3,
    dpi: 300,
    timeout: 90,
    preserveSpaces: false,
    oem: 3,
    tessedit_char_whitelist: "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    processing_type: completeModeChecked ? "complete" : "basic",
    response_number: 5,
  });

  const onCameraReady = () => {
    setIsCameraReady(true);
    console.log("Camera is ready");
  };

  const showDialog = (type: string, data: string) => {
    setScannedBarcode({ type, data });
    setVisible(true);
  };

  const hideDialog = () => {
    setVisible(false);
    setScannedBarcode(null);
  };

  const handleBarCodeScanned = ({ type, data }: { type: any; data: any }) => {
    showDialog(type, data);
  };

  const getOcrFromImage = async (photo: any) => {
    try {
      // Handle different image object types
      let imageUri = photo.uri;

      // Log the photo object to debug
      console.log("Photo object:", photo);
      console.log("Processing photo URI:", imageUri);

      if (!imageUri) {
        throw new Error("No URI found in photo object");
      }

      // For picked images, we might need to handle the URI differently
      // Some URIs might be file:// URLs that need special handling
      if (imageUri.startsWith("file://")) {
        console.log("Detected file:// URI, this is a picked image");
      }

      // Create FormData differently for native vs web
      const formData = new FormData();

      if (Platform.OS === "web") {
        // On web, append a Blob
        const res = await fetch(imageUri);
        if (!res.ok) {
          throw new Error(`Failed to fetch image: ${res.status}`);
        }
        const blob = await res.blob();
        const fileExtFromMime = blob.type?.split("/")[1] || "jpg";
        const webFilename = `image.${fileExtFromMime}`;
        formData.append("image", blob, webFilename);
        console.log(
          "FormData (web) created with filename:",
          webFilename,
          "type:",
          blob.type
        );
      } else {
        // On native, append a file object
        const defaultMime = "image/jpeg";
        const inferredExt = imageUri.split(".").pop()?.toLowerCase();
        const filename = inferredExt ? `image.${inferredExt}` : "image.jpg";
        const mimeType =
          inferredExt === "png"
            ? "image/png"
            : inferredExt === "webp"
            ? "image/webp"
            : defaultMime;
        formData.append("image", {
          uri: imageUri,
          name: filename,
          type: mimeType,
        } as any);
        console.log(
          "FormData (native) created with filename:",
          filename,
          "type:",
          mimeType
        );
      }

      // Build query string with OCR configuration
      const queryParams = new URLSearchParams({
        confidence: ocrConfig.confidence.toString(),
        psm: ocrConfig.psm.toString(),
        dpi: ocrConfig.dpi.toString(),
        timeout: ocrConfig.timeout.toString(),
        preserveSpaces: ocrConfig.preserveSpaces.toString(),
        oem: ocrConfig.oem.toString(),
        processingType: completeModeChecked ? "complete" : "basic",
        responseNumber: ocrConfig.response_number.toString(),
      });

      console.log("Sending to backend with config:", queryParams.toString());

      console.log(
        `http://${ipAddress}:3000/api/ocr/process?${queryParams.toString()}`
      );
      // Send to backend OCR endpoint with configuration using fetch
      const url =
        ipAddress == ""
          ? `http://localhost:3000/api/ocr/process?${queryParams.toString()}`
          : `http://${ipAddress}:3000/api/ocr/process?${queryParams.toString()}`;

      const controller = new AbortController();
      const timeoutId = setTimeout(
        () => controller.abort(),
        ocrConfig.timeout * 1000
      );

      const fetchResponse = await fetch(url, {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!fetchResponse.ok) {
        throw new Error(`Request failed with status ${fetchResponse.status}`);
      }

      const ocrResponseData = await fetchResponse.json();

      console.log("Backend response received");

      if (ocrResponseData.success) {
        setOcrResult(ocrResponseData.data);
        console.log("OCR Result:", ocrResponseData.data);

        // Show success alert with extracted text
        Alert.alert("OCR Completed successfully!");
      } else {
        Alert.alert("OCR Error", "Failed to process image");
      }
    } catch (error: any) {
      console.error("Error in getOcrFromImage:", error);

      // More specific error messages
      if (
        error?.name === "AbortError" ||
        (error?.message && error.message.toLowerCase().includes("timeout"))
      ) {
        Alert.alert(
          "Timeout Error",
          "The request took too long. Please try again."
        );
      } else if (
        error?.message &&
        error.message.includes("Network request failed")
      ) {
        Alert.alert(
          "Network Error",
          "Could not connect to the server. Please check if the backend is running."
        );
      } else {
        Alert.alert(
          "Error",
          `Failed to process image: ${error.message || "Unknown error"}`
        );
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const takePicture = async () => {
    if (cameraRef.current && isCameraReady) {
      try {
        // Set processing state immediately when button is clicked
        setIsProcessing(true);

        // Small delay to show the loading state
        await new Promise((resolve) => setTimeout(resolve, 100));

        const photo = await cameraRef.current.takePictureAsync();

        if (!photo) {
          Alert.alert("Error", "Failed to capture photo");
          return;
        }

        setImage(photo.uri);
        getOcrFromImage(photo);
      } catch (error) {
        console.error("Error processing image:", error);
        Alert.alert("Error", "Failed to process image. Please try again.");
      }
    }
  };

  const retakePicture = () => {
    setImage(null);
    setOcrResult(null);
  };

  const toggleFlash = () => {
    setFlash((prev) => (prev === "off" ? "on" : "off"));
  };

  const handleClose = () => {
    router.back();
  };

  const handlePickImage = async () => {
    try {
      // Set processing state immediately when button is clicked
      setIsProcessing(true);

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 1,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        const pickedImage = result.assets[0];
        setImage(pickedImage.uri);

        try {
          // Use the existing getOcrFromImage function
          getOcrFromImage(pickedImage);
        } catch (error) {
          console.error("Error processing picked image:", error);
          Alert.alert(
            "Error",
            "Failed to process picked image. Please try again."
          );
        }
      } else {
        // If user cancels, stop the loading state
        setIsProcessing(false);
      }
    } catch (error) {
      console.error("Error picking image:", error);
      Alert.alert("Error", "Failed to pick image from gallery");
      setIsProcessing(false);
    }
  };

  function OcrResultsScreen({ data }: { data: any }) {
    console.log(data);
    // If there are no items
    if (data.length == 0) {
      return (
        <View>
          <Text style={{ textAlign: "center", fontSize: 96 }}>
            No items were found!
          </Text>
          <Text style={{ textAlign: "center", fontSize: 48 }}>
            Try turning on more advanced processing options...
          </Text>
        </View>
      );
    }

    let item = data[currentProduct];
    let nutrition = {};
    if (item.details != undefined) {
      nutrition = item.details.nutritionFacts;
    }
    console.log(nutrition);

    return (
      <View>
        <View
          style={{
            flexDirection: "row",
            alignItems: "flex-start",
            marginBottom: 20,
          }}
        >
          <Image
            style={{
              width: 200,
              height: 200,
              padding: 10,
            }}
            source={{ uri: item?.imageUrl }}
          />
          <View
            style={{ flex: 1, marginLeft: 15, justifyContent: "flex-start" }}
          >
            <Text
              style={{
                color: "white",
                fontSize: 12,
                marginBottom: 8,
              }}
            >
              Current product number: {currentProduct + 1}
              {"\n"}
              All available products: {data.length}
            </Text>
            <TouchableOpacity
              onPress={() => {
                Linking.openURL(item.productUrl);
              }}
            >
              <Text
                style={{
                  color: "#ADD8E6",
                  fontSize: 16,
                  fontWeight: "bold",
                  textDecorationLine: "underline",
                }}
              >
                {item?.productName}
              </Text>
            </TouchableOpacity>
            <Text style={{ color: "white", marginBottom: 8 }}>
              (From {item?.source})
            </Text>
          </View>
        </View>
        <View>
          <Text style={styles.subcategoryTitle}>Category:</Text>
          <Text style={{ color: "white", fontSize: 14, lineHeight: 20 }}>
            {item?.category != undefined && item.category.length > 0 ? (
              item?.category.slice(-3).join(", ")
            ) : (
              <Text>No category provided</Text>
            )}
          </Text>
        </View>
        <View>
          <Text style={styles.subcategoryTitle}>
            {"\n"}
            Ingredients:
          </Text>
          <Text style={{ color: "white", fontSize: 14, lineHeight: 20 }}>
            {item?.details != undefined &&
            item.details.ingredients != undefined &&
            item.details.ingredients.length > 0 ? (
              item?.details.ingredients.join(", ")
            ) : (
              <Text>No Ingredients Provided</Text>
            )}
          </Text>
        </View>
        <View>
          <Text style={styles.subcategoryTitle}>{"\n"}Nutrition Facts:</Text>
          <Text style={{ color: "white", fontSize: 14, lineHeight: 20 }}>
            {nutrition != null && Object.entries(nutrition).length > 0 ? (
              Object.entries(nutrition).map(([key, value]) => (
                <Text
                  key={key}
                  style={{ color: "white", fontSize: 14, lineHeight: 20 }}
                >
                  {typeof key !== "object" ? key + ": " : ""}
                  {typeof value === "object" && value !== null
                    ? Object.entries(value).map(([k, v]) => (
                        <Text
                          key={`${key}-${k}`}
                          style={{ color: "white", fontSize: 12 }}
                        >
                          {"- "}
                          {String(k)}:{" "}
                          {String(
                            typeof v === "object"
                              ? "\n" +
                                  "\t" +
                                  "- " +
                                  JSON.stringify(v)
                                    .replace(/[{}""]/g, "")
                                    .replace(/,(?=[A-Za-z])/g, "  |  ")
                                    .replace(/[:]/g, ": ")
                              : v
                          )}
                          {"\n"}
                        </Text>
                      ))
                    : String(value !== "" ? value : "Not provided")}
                  {"\n"}
                </Text>
              ))
            ) : (
              <Text>No nutrition facts provided</Text>
            )}
          </Text>
        </View>
        <View style={{ flexDirection: "row", alignItems: "flex-start" }}>
          <TouchableOpacity
            onPress={() => {
              currentProduct > 0
                ? setCurrentProduct(currentProduct - 1)
                : setCurrentProduct(currentProduct);
            }}
          >
            <Ionicons name="arrow-back" size={48} color="white" />
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => {
              currentProduct + 1 < data.length
                ? setCurrentProduct(currentProduct + 1)
                : setCurrentProduct(currentProduct);
            }}
            style={{ marginLeft: "auto" }}
          >
            <Ionicons name="arrow-forward" size={48} color="white" />
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  if (!permission?.granted) {
    return (
      <View style={styles.permissionContainer}>
        <Text style={styles.permissionText}>Camera permission is required</Text>
        <TouchableOpacity
          style={styles.permissionButton}
          onPress={requestPermission}
        >
          <Text style={styles.permissionButtonText}>Grant Permission</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <Provider>
      <SafeAreaView style={{ flex: 1 }}>
        {/* OCR Results Display */}
        {ocrResult ? (
          <SafeAreaView style={{ flex: 1 }}>
            <ScrollView
              style={{ flex: 1 }}
              contentContainerStyle={{ paddingBottom: 24 }}
            >
              <Text style={styles.ocrResultsTitle}>OCR Results:</Text>
              <View style={styles.ocrResultsContainer}>
                <Text style={styles.ocrResultsText} numberOfLines={2}>
                  {ocrResult.text}
                </Text>
                <OcrResultsScreen data={ocrResult} />
              </View>
            </ScrollView>
          </SafeAreaView>
        ) : (
          <View style={styles.container}>
            {/* Darkened Background */}
            <View style={styles.backgroundOverlay} />
            {/* Blurred Mask */}
            <BlurView
              style={[
                styles.blurredMask,
                {
                  height:
                    activeButton === "barcode" ? 226 + 4 : frameHeight + 4,
                },
              ]}
              intensity={80}
              tint="dark"
            />
            <TouchableOpacity
              style={styles.closeButtonOutside}
              onPress={handleClose}
            >
              <Ionicons name="close" size={24} color="#FFF" />
            </TouchableOpacity>

            {/* Camera Frame */}
            {/* Loading Indicator */}
            <View>
              {isProcessing && image && (
                <View style={styles.loadingContainer}>
                  <ActivityIndicator size="large" color="#14AE5C" />
                  <Text style={styles.loadingText}>
                    Processing image... (This may take a bit!)
                  </Text>
                </View>
              )}
            </View>
            <View
              style={[
                styles.cameraFrame,
                { backgroundColor: "transparent" },
                activeButton === "barcode" && {
                  height: 226,
                },
              ]}
            >
              {!image && (
                <CameraView
                  style={StyleSheet.absoluteFillObject}
                  onCameraReady={onCameraReady}
                  flash={flash}
                  ref={(ref) => (cameraRef.current = ref)}
                  {...(activeButton === "barcode"
                    ? {
                        barcodeScannerSettings: {
                          barcodeTypes: [
                            "qr",
                            "ean13",
                            "ean8",
                            "code39",
                            "code128",
                            "upc_e",
                            "pdf417",
                            "aztec",
                            "datamatrix",
                          ],
                        },
                        onBarcodeScanned: handleBarCodeScanned,
                      }
                    : {})}
                />
              )}

              {image && (
                <View style={styles.imageContainer}>
                  <Image
                    source={{ uri: image }}
                    style={StyleSheet.absoluteFillObject}
                    resizeMode="cover"
                  />

                  <TouchableOpacity
                    style={styles.retakeButtonInFrame}
                    onPress={retakePicture}
                  >
                    <Text style={styles.retakeButtonInFrameText}>Retake</Text>
                  </TouchableOpacity>
                </View>
              )}

              {/* Bottom Controls */}
              {activeButton === "photo" && (
                <View style={styles.bottomControls}>
                  {/* Pick Image Button */}
                  <TouchableOpacity
                    style={styles.controlButton}
                    onPress={handlePickImage}
                  >
                    <Ionicons name="image-outline" size={24} color="#1E1E1E" />
                  </TouchableOpacity>

                  {/* Capture/Scan Button */}
                  <TouchableOpacity
                    style={[
                      styles.captureButton,
                      isProcessing && styles.captureButtonDisabled,
                    ]}
                    onPress={activeButton === "photo" ? takePicture : undefined}
                    disabled={isProcessing}
                  >
                    {isProcessing ? (
                      <ActivityIndicator size="small" color="#FFF" />
                    ) : (
                      <Ionicons
                        name={"camera-outline"}
                        size={24}
                        color="#FFF"
                      />
                    )}
                  </TouchableOpacity>

                  {/* Flashlight Button */}
                  <TouchableOpacity
                    style={styles.controlButton}
                    onPress={toggleFlash}
                  >
                    <Ionicons
                      name={flash === "on" ? "flash" : "flash-off"}
                      size={24}
                      color="#1E1E1E"
                    />
                  </TouchableOpacity>
                </View>
              )}
            </View>
            {/* Mode Selection */}
            <View style={styles.modeSelection}>
              <TouchableOpacity
                style={[
                  styles.modeButton,
                  activeButton === "photo"
                    ? styles.activePhotoMode
                    : styles.inactiveMode,
                ]}
                onPress={() => setActiveButton("photo")}
              >
                <Ionicons name="camera" size={20} color="#FFF" />
                <Text style={styles.modeButtonText}>Photo</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[
                  styles.modeButton,
                  activeButton === "barcode"
                    ? styles.activeScanMode
                    : styles.inactiveMode,
                ]}
                onPress={() => setActiveButton("barcode")}
              >
                <Ionicons name="barcode-outline" size={20} color="#FFF" />
                <Text style={styles.modeButtonText}>Scan</Text>
              </TouchableOpacity>
            </View>
            <View
              style={{
                flexDirection: "row",
                paddingTop: 10,
                paddingBottom: 10,
              }}
            >
              {!isProcessing ? (
                <View>
                  <Checkbox
                    value={completeModeChecked}
                    onValueChange={setCompleteModeChecked}
                    aria-label="a"
                  />
                  <Text style={{ color: "white" }}>
                    {" "}
                    Activate complete analysis (may be slow)
                  </Text>
                </View>
              ) : (
                <View />
              )}
            </View>
            {!isProcessing ? (
              <TextInput
                style={{ width: 400 }}
                onChangeText={setIpAddress}
                value={ipAddress}
                placeholder="Type IPv4 Address here if testing from a phone..."
              />
            ) : (
              <View />
            )}
            {/* Barcode Dialog */}
            <Portal>
              <Dialog visible={visible} onDismiss={hideDialog}>
                <Dialog.Title>Barcode Scanned</Dialog.Title>
                <Dialog.Content>
                  {scannedBarcode && (
                    <>
                      <Text>Type: {scannedBarcode.type}</Text>
                      <Text>Data: {scannedBarcode.data}</Text>
                    </>
                  )}
                </Dialog.Content>
                <Dialog.Actions>
                  <Button onPress={hideDialog}>Done</Button>
                </Dialog.Actions>
              </Dialog>
            </Portal>
          </View>
        )}
      </SafeAreaView>
    </Provider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "transparent",
    justifyContent: "center",
    alignItems: "center",
  },
  backgroundOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0, 0, 0, 0.6)", // Semi-transparent black
  },
  blurredMask: {
    position: "absolute",
    borderRadius: 7,
    // These are calculated dynamically based on cameraFrame size and position
  },
  closeButtonOutside: {
    position: "absolute",
    top: 2,
    left: 20,
    width: 31,
    height: 31,
    borderRadius: 20,
    backgroundColor: "rgba(0, 0, 0, 0.6)",
    justifyContent: "center",
    alignItems: "center",
  },
  cameraFrame: {
    width: frameWidth,
    height: frameHeight,
    borderRadius: 5,
    borderWidth: 2,
    borderColor: "#FFF",
    overflow: "hidden",
  },
  imageContainer: {
    width: "100%",
    height: "100%",
  },
  retakeButtonInFrame: {
    position: "absolute",
    top: 10,
    right: 10,
    backgroundColor: "rgba(0,0,0,0.5)",
    paddingVertical: 8,
    paddingHorizontal: 15,
    borderRadius: 20,
  },
  retakeButtonInFrameText: {
    color: "#FFF",
    fontSize: 14,
  },
  bottomControls: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 10,
    top: "76%",
  },
  controlButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#D9D9D9",
    justifyContent: "center",
    alignItems: "center",
  },
  captureButton: {
    width: 61,
    height: 61,
    borderRadius: 35,
    backgroundColor: "#2C2C2C",
    borderWidth: 5,
    borderColor: "#D9D9D9",
    alignItems: "center",
    justifyContent: "center",
  },
  captureButtonDisabled: {
    opacity: 0.7,
  },
  modeSelection: {
    flexDirection: "row",
    width: 318,
    height: 49,
    backgroundColor: "#000",
    justifyContent: "space-between",
    borderRadius: 32,
    alignItems: "center",
    marginTop: 20,
  },
  modeButton: {
    flex: 1,
    height: 45,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    borderRadius: 32,
    marginHorizontal: 5,
  },
  activePhotoMode: {
    backgroundColor: "#14AE5C",
  },
  activeScanMode: {
    backgroundColor: "#0F8C49",
  },
  inactiveMode: {
    backgroundColor: "rgba(66, 66, 66, 0.5)",
  },
  modeButtonText: {
    color: "#FFF",
    fontSize: 14,
    marginLeft: 6,
  },
  permissionContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
    backgroundColor: "#000",
  },
  permissionText: {
    color: "#FFF",
    fontSize: 16,
    marginBottom: 10,
    textAlign: "center",
  },
  permissionButton: {
    backgroundColor: "#14AE5C",
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
  },
  permissionButtonText: {
    color: "#FFF",
    fontSize: 16,
    textAlign: "center",
  },
  ocrResultsContainer: {
    backgroundColor: "rgba(0,0,0,0.7)",
    padding: 10,
    borderRadius: 8,
    justifyContent: "center",
    alignItems: "stretch",
    width: "100%",
    marginTop: 12,
  },
  ocrResultsTitle: {
    color: "#333",
    fontSize: 32,
    fontWeight: "bold",
    marginBottom: 5,
    textAlign: "center",
  },
  ocrResultsText: {
    color: "#FFF",
    fontSize: 14,
  },
  ocrUpcText: {
    color: "#FFF",
    fontSize: 14,
    marginTop: 5,
  },
  loadingContainer: {
    position: "relative",
    backgroundColor: "rgba(0,0,0,0.7)",
    padding: 20,
    borderRadius: 10,
    alignItems: "center",
  },
  loadingText: {
    color: "#FFF",
    fontSize: 16,
    marginTop: 10,
  },
  subcategoryTitle: {
    color: "white",
    textDecorationLine: "underline",
  },
});
