// import React, { useRef, useState, useCallback, useEffect } from "react";
// import { View, StyleSheet, Text, TouchableOpacity, Image, Alert } from "react-native";
// import {
//   CameraType,
//   CameraView,
//   useCameraPermissions,
//   Camera,
//   FlashMode,
//   BarcodeScanningResult,
// } from "expo-camera";
// import { Button } from "react-native-paper";
// import CloseButton from "@/components/CloseButton";
// import { scale, verticalScale } from "react-native-size-matters";
// import { Dimensions, StatusBar, Platform } from "react-native";
// import * as ImagePicker from "expo-image-picker";
// import MaterialCommunityIcons from "@expo/vector-icons/MaterialCommunityIcons";
// import Feather from "@expo/vector-icons/Feather";
// import Ionicons from "@expo/vector-icons/Ionicons";
// import { BlurView } from "expo-blur";
// import { router } from "expo-router";

// const { width, height } = Dimensions.get("window");

// // Calculate sizes for the camera frame and masks
// const frameTop = height * 0.10; // Top spacing
// const frameBottom = height * 0.87; // Define the bottom position directly
// const frameHeight = frameBottom - frameTop; // Calculate height from top and bottom positions
// const bottomMaskHeight = height - frameBottom; // Bottom mask height based on frame bottom
// const frameLeftRight = width * 0.05; // 5% from each side

// interface CameraRefProps {
//   takePictureAsync: () => Promise<any>;
// }

// export default function CameraScreen() {
//   // All hooks must be at the top level - before any conditional returns
//   const [facing, setFacing] = useState<CameraType>("back");
//   const [permission, requestPermission] = useCameraPermissions();
//   const [activeButton, setActiveButton] = useState<"camera" | "barcode" | null>("camera");
//   const [image, setImage] = useState<string | null>(null);
//   const [flash, setFlash] = useState<FlashMode>("off");
//   const cameraRef = useRef<CameraView>(null);
//   const [isCameraReady, setIsCameraReady] = useState(false);
//   const [isCapturing, setIsCapturing] = useState(false);
//   const [scannedBarcode, setScannedBarcode] = useState<string | null>(null);
//   const [showPermissionUI, setShowPermissionUI] = useState(false);
//   const [isScanning, setIsScanning] = useState(false);
//   const lastScannedRef = useRef<string | null>(null);
//   const scanTimeoutRef = useRef<NodeJS.Timeout | null>(null);

//   // Define all callback functions using useCallback
//  const handleClose = useCallback(() => {
//     router.back(); // Navigate back to previous screen
//   }, []);

//   const toggleFlashMode = useCallback(() => {
//     // Cycle through flash modes: off -> on -> off
//     setFlash(flash === "off" ? "on" : "off");
//   }, [flash]);

//   const onCameraReady = useCallback(() => {
//     setIsCameraReady(true);
//   }, []);

//   const takePicture = useCallback(async () => {
//     if (cameraRef.current && isCameraReady && !isCapturing) {
//       try {
//         setIsCapturing(true);
//         const photo = await cameraRef.current.takePictureAsync({
//           quality: 0.8,
//           skipProcessing: false,
//         });

//         if (photo) {
//           console.log(photo.uri);
//           setImage(photo.uri);
//         }

//         // Add some delay before allowing another capture
//         setTimeout(() => {
//           setIsCapturing(false);
//         }, 1000);
//       } catch (error) {
//         console.error("Error taking picture:", error);
//         setIsCapturing(false);
//       }
//     }
//   }, [cameraRef, isCameraReady, isCapturing]);

//   const pickImage = useCallback(async () => {
//     try {
//       let result = await ImagePicker.launchImageLibraryAsync({
//         mediaTypes: ImagePicker.MediaTypeOptions.Images,
//         allowsEditing: true,
//         aspect: [4, 3],
//         quality: 1,
//       });

//       if (!result.canceled && result.assets && result.assets.length > 0) {
//         setImage(result.assets[0].uri);
//       }
//     } catch (error) {
//       console.error("Error picking image:", error);
//     }
//   }, []);

//   const handleBarCodeScanned = useCallback(({ type, data }: BarcodeScanningResult) => {
//     // Prevent multiple scans by checking if we're already in scanning mode
//     // or if this barcode was just scanned (within the last 3 seconds)
//     if (isScanning || lastScannedRef.current === data) {
//       return;
//     }

//     setIsScanning(true);
//     lastScannedRef.current = data;
//     setScannedBarcode(data);

//     Alert.alert(
//       "Barcode Scanned",
//       `Type: ${type}\nData: ${data}`,
//       [
//         {
//           text: "Scan Again",
//           onPress: () => {
//             setScannedBarcode(null);

//             // Add a small cooldown period before allowing new scans
//             setTimeout(() => {
//               setIsScanning(false);
//               lastScannedRef.current = null;
//             }, 100); // Reduced cooldown to 500ms
//           },
//         },
//         {
//           text: "OK",
//           onPress: () => {
//             // Reset scan state immediately instead of after a delay
//             setScannedBarcode(null);
//             setIsScanning(false);
//             lastScannedRef.current = null;

//             // If we need a cooldown to prevent immediate rescans, use a short one
//             if (scanTimeoutRef.current) {
//               clearTimeout(scanTimeoutRef.current);
//             }
//           }
//         }
//       ]
//     );
//   }, [isScanning]);

//   // Clean up timeout on unmount
//   useEffect(() => {
//     return () => {
//       if (scanTimeoutRef.current) {
//         clearTimeout(scanTimeoutRef.current);
//       }
//     };
//   }, []);

//   // Reset scanning state when switching modes
//   useEffect(() => {
//     setIsScanning(false);
//     lastScannedRef.current = null;
//     if (scanTimeoutRef.current) {
//       clearTimeout(scanTimeoutRef.current);
//       scanTimeoutRef.current = null;
//     }
//   }, [activeButton]);

//   // Handle permissions with useEffect
//   useEffect(() => {
//     if (permission) {
//       setShowPermissionUI(!permission.granted);
//     }
//   }, [permission]);

//   // Return permission UI if needed
//   if (!permission) {
//     return <View />;
//   }

//   if (showPermissionUI) {
//     return (
//       <View style={styles.mainContainer}>
//         <Text style={styles.permissionMessage}>
//           We need your permission to show the camera
//         </Text>
//         <TouchableOpacity onPress={requestPermission} style={styles.permissionButton}>
//           <Text style={styles.permissionButtonText}>Grant Permission</Text>
//         </TouchableOpacity>
//       </View>
//     );
//   }

//   return (
//     <View style={styles.mainContainer}>
//       <StatusBar barStyle="light-content" />

//       {/* Camera view that fills the entire screen */}
//       {!image && (
//         <CameraView
//           style={StyleSheet.absoluteFillObject}
//           facing={facing}
//           onCameraReady={onCameraReady}
//           flash={flash}
//           ref={cameraRef}
//           {...(activeButton === "barcode" ? {
//             barcodeScannerSettings: {
//               barcodeTypes: [
//                 "qr",
//                 "ean13",
//                 "ean8",
//                 "code39",
//                 "code128",
//                 "upc_e",
//                 "pdf417",
//                 "aztec",
//                 "datamatrix"
//               ],
//             },
//             onBarcodeScanned: scannedBarcode ? undefined : handleBarCodeScanned
//           } : {})}
//         />
//       )}

//       {/* UI Container with masked areas defining a cutout */}
//       <View style={styles.uiContainer}>
//         {/* Top masked area with blur */}
//         <BlurView intensity={25} tint="dark" style={styles.topMask} />

//         {/* Left masked area with blur */}
//         <BlurView intensity={25} tint="dark" style={styles.leftMask} />

//         {/* Right masked area with blur */}
//         <BlurView intensity={25} tint="dark" style={styles.rightMask} />

//         {/* Bottom masked area with blur */}
//         <BlurView intensity={25} tint="dark" style={styles.bottomMask} />

//         {/* White frame around camera view */}
//         <View style={styles.cameraFrame} />

//         {/* Image preview replaces camera when image is taken */}
//         {image && (
//           <View style={styles.previewContainer}>
//             <Image source={{ uri: image }} style={styles.previewImage} />
//             <BlurView intensity={50} tint="dark" style={styles.blurRetakeButton}>
//               <TouchableOpacity
//                 style={styles.retakeButtonContainer}
//                 onPress={() => setImage(null)}>
//                 <Ionicons name="refresh" size={24} color="white" style={{marginRight: 8}} />
//                 <Text style={styles.retakeText}>Retake</Text>
//               </TouchableOpacity>
//             </BlurView>
//           </View>
//         )}

//         {/* Header controls */}
//         <View style={styles.headerControls}>
//           <BlurView intensity={50} tint="dark" style={styles.blurCircleButton}>
//             <TouchableOpacity style={styles.circleButton} onPress={handleClose}>
//               <Ionicons name="close" size={20} color="white" />
//             </TouchableOpacity>
//           </BlurView>

//           <BlurView intensity={50} tint="dark" style={styles.blurCircleButton}>
//             <TouchableOpacity style={styles.circleButton} onPress={toggleFlashMode}>
//               <Ionicons
//                 name={flash === "on" ? "flash" : "flash-off"}
//                 size={20}
//                 color="white"
//               />
//             </TouchableOpacity>
//           </BlurView>
//         </View>

//         {/* Bottom camera controls */}
//         {!image && (
//           <View style={styles.bottomControls}>
//             <View style={styles.cameraControls}>
//               {activeButton === "camera" && (
//                 <>
//                   <BlurView intensity={50} tint="dark" style={styles.galleryButton}>
//                     <TouchableOpacity style={styles.galleryButtonInner} onPress={pickImage}>
//                       <MaterialCommunityIcons name="image" size={24} color="white" />
//                     </TouchableOpacity>
//                   </BlurView>

//                   <TouchableOpacity
//                     style={[
//                       styles.captureButton,
//                       isCapturing && styles.disabledButton
//                     ]}
//                     onPress={takePicture}
//                     disabled={isCapturing}
//                   >
//                     <View style={styles.captureButtonInner} />
//                   </TouchableOpacity>
//                 </>
//               )}
//             </View>
//           </View>
//         )}

//         {/* Bottom tab buttons with frosted glass effect - only show when no image */}
//         {!image && (
//           <View style={styles.tabBarContainer}>
//             <BlurView intensity={50} tint="dark" style={styles.tabBar}>
//               <TouchableOpacity
//                 style={[
//                   styles.tabButton,
//                   activeButton === "camera" && styles.activeTabButton
//                 ]}
//                 onPress={() => {
//                   setActiveButton("camera");
//                   setImage(null);
//                   setScannedBarcode(null);
//                   setIsScanning(false);
//                   lastScannedRef.current = null;
//                 }}
//               >
//                 <Ionicons name="camera" size={20} color="white" />
//                 <Text style={styles.tabButtonText}>Photo</Text>
//               </TouchableOpacity>

//               <TouchableOpacity
//                 style={[
//                   styles.tabButton,
//                   activeButton === "barcode" && styles.activeTabButton
//                 ]}
//                 onPress={() => {
//                   setActiveButton("barcode");
//                   setImage(null);
//                   setScannedBarcode(null);
//                   setIsScanning(false);
//                   lastScannedRef.current = null;
//                 }}
//               >
//                 <Ionicons name="barcode-outline" size={20} color="white" />
//                 <Text style={styles.tabButtonText}>Barcode</Text>
//               </TouchableOpacity>
//             </BlurView>
//           </View>
//         )}
//       </View>
//     </View>
//   );
// }

// const styles = StyleSheet.create({
//   mainContainer: {
//     flex: 1,
//     backgroundColor: '#000',
//   },

//   uiContainer: {
//     ...StyleSheet.absoluteFillObject,
//   },

//   // Masked areas with blur (all areas outside the camera frame)
//   topMask: {
//     position: 'absolute',
//     top: 0,
//     left: 0,
//     right: 0,
//     height: frameTop,
//     zIndex: 5,
//   },

//   leftMask: {
//     position: 'absolute',
//     top: frameTop,
//     left: 0,
//     width: frameLeftRight,
//     height: frameHeight,
//     zIndex: 5,
//   },

//   rightMask: {
//     position: 'absolute',
//     top: frameTop,
//     right: 0,
//     width: frameLeftRight,
//     height: frameHeight,
//     zIndex: 5,
//   },

//   bottomMask: {
//     position: 'absolute',
//     bottom: 0,
//     left: 0,
//     right: 0,
//     height: bottomMaskHeight,
//     zIndex: 5,
//   },

//   headerControls: {
//     flexDirection: "row",
//     justifyContent: "space-between",
//     position: "absolute",
//     top: 15,
//     width: "85%",
//     alignSelf: 'center',
//     zIndex: 20,
//   },

//   bottomControls: {
//     position: 'absolute',
//     bottom: 100,
//     width: '100%',
//     alignItems: 'center',
//     zIndex: 20,
//   },

//   cameraControls: {
//     flexDirection: 'row',
//     alignItems: 'center',
//     justifyContent: 'center',
//     width: '80%',
//   },

//   message: {
//     marginBottom: 20,
//     textAlign: "center",
//     color: "white",
//   },

//   blurCircleButton: {
//     width: 40,
//     height: 40,
//     borderRadius: 20,
//     justifyContent: "center",
//     alignItems: "center",
//     overflow: 'hidden',
//   },

//   circleButton: {
//     width: "100%",
//     height: "100%",
//     justifyContent: "center",
//     alignItems: "center",
//   },

//   galleryButton: {
//     width: 44,
//     height: 44,
//     borderRadius: 22,
//     overflow: 'hidden',
//     marginRight: 50,
//   },

//   galleryButtonInner: {
//     width: "100%",
//     height: "100%",
//     justifyContent: "center",
//     alignItems: "center",
//   },

//   captureButton: {
//     width: 68,
//     height: 68,
//     borderRadius: 34,
//     backgroundColor: 'rgba(255,255,255,0.3)',
//     justifyContent: 'center',
//     alignItems: 'center',
//     borderWidth: 3,
//     borderColor: 'white',
//   },

//   captureButtonInner: {
//     width: 54,
//     height: 54,
//     borderRadius: 27,
//     backgroundColor: "white",
//   },

//   tabBarContainer: {
//     position: 'absolute',
//     bottom: 30,
//     width: '100%',
//     alignItems: 'center',
//     zIndex: 20,
//   },

//   tabBar: {
//     flexDirection: "row",
//     borderRadius: 30,
//     width: "70%",
//     height: 50,
//     overflow: "hidden",
//     justifyContent: 'space-between',
//   },

//   tabButton: {
//     flex: 1,
//     flexDirection: 'row',
//     height: 50,
//     justifyContent: "center",
//     alignItems: "center",
//     borderRadius: 25,
//   },

//   tabButtonText: {
//     color: 'white',
//     marginLeft: 5,
//     fontWeight: '600',
//   },

//   activeTabButton: {
//     backgroundColor: "#14AE5C",
//   },

//   disabledButton: {
//     opacity: 0.5,
//   },

//   previewContainer: {
//     position: 'absolute',
//     top: frameTop,
//     left: frameLeftRight,
//     width: width - (frameLeftRight * 2),
//     height: frameHeight,
//     overflow: 'hidden',
//     zIndex: 15,
//   },

//   previewImage: {
//     width: "100%",
//     height: "100%",
//   },

//   blurRetakeButton: {
//     position: "absolute",
//     bottom: 40,
//     left: 0,
//     right: 0,
//     padding: 15,
//     backgroundColor: 'rgba(0,0,0,0.5)',
//     zIndex: 25,
//     alignItems: 'center',
//   },

//   retakeText: {
//     color: "white",
//     fontWeight: "bold",
//     fontSize: 16,
//   },

//   scanOverlay: {
//     position: 'absolute',
//     top: 0,
//     left: 0,
//     right: 0,
//     bottom: 0,
//     justifyContent: 'center',
//     alignItems: 'center',
//     backgroundColor: 'rgba(0, 0, 0, 0.5)',
//     zIndex: 30,
//   },

//   scanText: {
//     color: 'white',
//     fontSize: 18,
//     fontWeight: 'bold',
//     marginBottom: 20,
//   },

//   rescanButton: {
//     backgroundColor: '#14AE5C',
//     padding: 12,
//     borderRadius: 20,
//   },

//   rescanText: {
//     color: 'white',
//     fontWeight: 'bold',
//   },

//   permissionButton: {
//     backgroundColor: '#14AE5C',
//     padding: 12,
//     borderRadius: 8,
//   },

//   permissionButtonText: {
//     color: 'white',
//     fontWeight: 'bold',
//   },

//   permissionMessage: {
//     marginBottom: 20,
//     textAlign: "center",
//     color: "white",
//   },

//   // Updated camera frame style - positioned to exactly match blur masks
//   cameraFrame: {
//     position: 'absolute',
//     top: frameTop,
//     left: frameLeftRight,
//     width: width - (frameLeftRight * 2),
//     height: frameHeight - frameTop -14,
//     borderWidth: 2,
//     borderColor: 'white',
//     zIndex: 10,
//   },

//   retakeButtonContainer: {
//     flexDirection: 'row',
//     alignItems: 'center',
//     justifyContent: 'center',
//   },
// });
