import { View, StyleSheet, Button } from 'react-native';  
import React, { useState, useEffect } from 'react';  
import CameraButton from '@/components/CameraButton';  
import { useRouter } from 'expo-router';  
import { getAuth, signOut, onAuthStateChanged } from 'firebase/auth';  

export default function Index() {  
  const router = useRouter();  
  const auth = getAuth();  
  const [isAuthenticated, setIsAuthenticated] = useState(false);  

  // Track authentication state  
  useEffect(() => {  
    const unsubscribe = onAuthStateChanged(auth, (user: any) => {  
      setIsAuthenticated(!!user); // If user exists, set to true; otherwise, false  
    });  

    return () => unsubscribe(); 
  }, []);  

  const handleAuthAction = async () => {  
    if (isAuthenticated) {  
      // If logged in, log out the user  
      try {  
        await signOut(auth);  
        router.replace('/login'); 
      } catch (error) {  
        console.error('Logout error:', error);  
      }  
    } else {    
      router.replace('/login');  
    }  
  };  

  return (  
    <View style={styles.container}>  
      <View style={styles.row}>  
        <CameraButton />  
        <Button  
          title={isAuthenticated ? "Logout" : "Login"} // Change button text based on auth state  
          onPress={handleAuthAction}  
        />  
      </View>  
    </View>  
  );  
}  

const styles = StyleSheet.create({  
  container: {  
    flex: 1,  
    backgroundColor: '#25292e',  
    alignItems: 'center',  
    justifyContent: 'center',  
  },  
  row: {  
    flexDirection: 'row',  
    justifyContent: 'center',  
    flexWrap: 'wrap',  
    alignItems: 'center',  
    marginBottom: 20,  
    gap: 10,  
  },  
});  
