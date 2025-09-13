import { CameraView } from 'expo-camera';
import React, { useState, useRef } from 'react';  
import {   
  StyleSheet,   
  View,   
  Text,   
  TouchableOpacity   
} from 'react-native';  
import {   
  Camera,   
  useCameraDevice,   
  useCameraPermission,  
  PhotoFile,  
  CameraRuntimeError  
} from 'react-native-vision-camera';  

type CameraComponentProps = {  
  onPhotoTaken?: (photo: PhotoFile) => void;  
};  

export default function CameraComponent({ onPhotoTaken }: CameraComponentProps) {  
  return(
    <View style={styles.container}>
      <CameraView style={styles.camera} facing={facing}>
        <View style={styles.buttonContainer}>
          <TouchableOpacity style={styles.button} onPress={toggleCameraFacing}>

            <Text style={styles.text}>Flip Camera</Text>
          </TouchableOpacity>
        </View>
      </CameraView>
    </View>
  )
   
}  

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
  },
  message: {
    textAlign: 'center',
    paddingBottom: 10,
  },
  camera: {
    flex: 1,
  },
  buttonContainer: {
    flex: 1,
    flexDirection: 'row',
    backgroundColor: 'transparent',
    margin: 64,
  },
  button: {
    flex: 1,
    alignSelf: 'flex-end',
    alignItems: 'center',
  },
  text: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
  },
});