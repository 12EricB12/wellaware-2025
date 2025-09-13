import { initializeApp } from 'firebase/app';  
import { getAuth } from 'firebase/auth';  

// Firebase configuration  
const firebaseConfig = {  
  apiKey: 'AIzaSyAMWFottH4wgZMFfDJfgAsdRlnI7ufkfYM',  
  authDomain: 'well-aware-app.firebaseapp.com',  
  projectId: 'well-aware-app',  
  storageBucket: 'well-aware-app.appspot.com',  
  messagingSenderId: '677534601692',  
  appId: '1:677534601692:web:4d53dbf394290528803f19',  
  measurementId: 'G-JVXPRXL9C5',  
};  

// Initialize Firebase  
const app = initializeApp(firebaseConfig);  

// Initialize Firebase Auth  
const auth = getAuth(app);  

export { app, auth };  