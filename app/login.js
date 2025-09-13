import React, { useState } from 'react';
import { View, TextInput, Button, StyleSheet, Text, TouchableOpacity } from 'react-native';
import { auth } from '../firebase';
import { signInWithEmailAndPassword } from 'firebase/auth';
import { useRouter } from 'expo-router'; 

const LoginScreen = ({ navigation }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);  // State for showing password temporarily
  const router = useRouter();
  
  const handleLogin = async () => {
    try {
      await signInWithEmailAndPassword(auth, email, password);
      alert('Login Successful');
      router.replace('/')
    } catch (err) {
      console.log('Firebase Auth Error:', err.message);  // Debugging line
      setError(err.message);  // Show actual error instead of static text
    }
  };

  const handleShowPassword = () => {
    setShowPassword(true);
    setTimeout(() => {
      setShowPassword(false);
    }, 2000);  // Hide the password after 2 seconds
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Login</Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <TextInput
        style={styles.input}
        placeholder="Email"
        value={email}
        onChangeText={setEmail}
      />
      <View style={styles.passwordContainer}>
        <TextInput
          style={styles.input}
          placeholder="Password"
          secureTextEntry={!showPassword}
          value={password}
          onChangeText={setPassword}
        />
        <TouchableOpacity onPress={handleShowPassword} style={styles.showButton}>
          <Text style={styles.toggleText}>Show</Text>
        </TouchableOpacity>
      </View>
      <Button title="Login" onPress={handleLogin} />
      
      {/* Updated sign-up button styling */}
      <TouchableOpacity
        style={styles.signupButton}
        onPress={() => router.replace('/signUp')}
      >
        <Text style={styles.signupButtonText}>Don't have an account? Sign up here.</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
  },
  title: {
    fontSize: 30,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 20,
  },
  input: {
    height: 40, // Consistent height for all input fields
    borderColor: '#ccc',
    borderWidth: 1,
    borderRadius: 5,
    marginBottom: 10,
    paddingLeft: 10,
    width: '100%', // Makes the input take up the full width
  },
  error: {
    color: 'red',
    marginBottom: 10,
    textAlign: 'center',
  },
  passwordContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
    width: '100%',  // Ensure the container takes full width
  },
  toggleText: {
    marginLeft: 10,
    color: '#007BFF',
  },
  showButton: {
    position: 'absolute',
    right: 10,  // Right-align the "Show" button
    padding: 5,
  },
  signupButton: {
    backgroundColor: '#28a745', // New green color for the sign-up button
    padding: 8,  // Smaller padding to make it more compact
    borderRadius: 5,
    marginTop: 15,
    alignItems: 'center',
  },
  signupButtonText: {
    color: 'white',
    fontSize: 14,  // Smaller text size
  },
});

export default LoginScreen;
