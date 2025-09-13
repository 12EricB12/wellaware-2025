import React from 'react';  
import { View, StyleSheet, TouchableOpacity, Text } from 'react-native';  

const CloseButton = ({ onClose } : any) => {  
  return (  
    <View>  
      <TouchableOpacity style={styles.closeButton} onPress={onClose}>  
        <Text style={styles.closeButtonText}>✖</Text>  
      </TouchableOpacity>  
    </View>  
  );  
};  

const styles = StyleSheet.create({  
  closeButton: {  
    backgroundColor: 'white',  
    borderRadius: 50,  
    padding: 10,  
    elevation: 5, 
  },  
  closeButtonText: {  
    fontSize: 24,  
    color: 'black',  
  },  
});  

export default CloseButton;  