import { Slot } from "expo-router";  
import { onAuthStateChanged } from 'firebase/auth';  
import { auth } from '../firebase';  
import { useState, useEffect } from 'react';  

export default function RootLayout() {  
  const [isAuthenticated, setIsAuthenticated] = useState(false);  

  useEffect(() => {  
    const unsubscribe = onAuthStateChanged(auth, (user: any) => {  
      setIsAuthenticated(!!user);  
    });  

    return () => unsubscribe();  
  }, []);  

  return <Slot />;  
}  
