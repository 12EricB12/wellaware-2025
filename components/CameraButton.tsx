import { Camera, CameraType, CameraView, useCameraPermissions } from "expo-camera";  
import { Link } from "expo-router";
import React, { useState } from "react";  
import {   
  View,   
  Pressable,   
  StyleSheet,   
  Text,   
  Button,   
  Modal,   
  TouchableOpacity   
} from "react-native";  

export default function CameraButton() {  


  return (  
    <View style={styles.container}>  
    <Link href="/camera" style={styles.buttonContainer}>  
      <Text style={styles.buttonLabel}>Open Camera</Text>  
    </Link>  
  </View>  
  );  
}  

const styles = StyleSheet.create({  
  buttonContainer: {  
    margin: 10,  
    backgroundColor: "white",  
    borderColor: "black",  
    borderWidth: 1,  
    borderRadius: 10,  
    width: 138,  
    height: 138,  
  },  
  button: {  
    borderRadius: 10,  
    width: "100%",  
    height: "100%",  
    alignItems: "center",  
    justifyContent: "center",  
    flexDirection: "row",  
  },  
  buttonLabel: {  
    fontSize: 16,  
    color: "black",  
  },  
  container: {  
    flex: 1,  
    padding:20,
    justifyContent:'center',
    alignContent:'center'
  },  
  camera: {   
    width: '80%',  
    height:'60%',  
    borderWidth: 1,  
    borderColor: 'black',  
    borderRadius: 10,  
    overflow: 'hidden', 
  },  
//   flipButton: {  
//     position: 'absolute',  
//     top: 50,  
//     left: 20,  
//     backgroundColor: 'rgba(0,0,0,0.5)',  
//     padding: 10,  
//     borderRadius: 5,  
//   },  
  closeButton: {  
    position: 'absolute',  
    top: 50,  
    right: 20,  
    backgroundColor: 'rgba(0,0,0,0.5)',  
    padding: 10,  
    borderRadius: 5,  
  },  
  text: {  
    color: 'white',  
  },  
});  