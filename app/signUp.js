import React, { useState } from 'react';
import { View, TextInput, Button, StyleSheet, Text, TouchableOpacity } from 'react-native';
import { auth } from '../firebase';
import { createUserWithEmailAndPassword } from 'firebase/auth';
import { useRouter } from 'expo-router';  

const SignUpScreen = ({ navigation }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);  // State for showing password temporarily
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);  // State for confirm password
  const router = useRouter();
  
  const handleSignUp = async () => {
    
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    try {
      await createUserWithEmailAndPassword(auth, email, password);
      alert('Sign Up Successful');
      router.replace('/');
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

  const handleShowConfirmPassword = () => {
    setShowConfirmPassword(true);
    setTimeout(() => {
      setShowConfirmPassword(false);
    }, 2000);  // Hide the confirm password after 2 seconds
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Sign Up</Text>
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
      <View style={styles.passwordContainer}>
        <TextInput
          style={styles.input}
          placeholder="Confirm Password"
          secureTextEntry={!showConfirmPassword}
          value={confirmPassword}
          onChangeText={setConfirmPassword}
        />
        <TouchableOpacity onPress={handleShowConfirmPassword} style={styles.showButton}>
          <Text style={styles.toggleText}>Show</Text>
        </TouchableOpacity>
      </View>
      <Button title="Sign Up" onPress={handleSignUp} />

      {/* "Back to Login" button */}
      <TouchableOpacity
        style={styles.backButton}
        onPress={() => router.replace('/login')}
      >
        <Text style={styles.backButtonText}>Back to Login</Text>
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
    height: 50, // Consistent height for all input fields
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
  // New styles for the "Back to Login" button
  backButton: {
    backgroundColor: '#00BBFF',
    padding: 10,
    borderRadius: 5,
    marginTop: 15,
    alignItems: 'center',
  },
  backButtonText: {
    color: 'white',
    fontSize: 16,
  },
});

export default SignUpScreen;
