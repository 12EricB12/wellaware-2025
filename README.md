Project Setup Instructions
Follow the steps below to set up the project repository, install all dependencies, configure Firebase, and run the app.

1. Clone the Repository
First, clone the repository from GitHub. Run the command below:

bash
git clone <repository-url>  
Replace <repository-url> with the link to the repository.

2. Install Project Dependencies
Once the repository is cloned, navigate to the respective directory (frontend or backend) and install the necessary npm dependencies:

bash
cd <frontend-or-backend-directory>  
npm install  
This will install all required npm packages listed in the package.json file.

3. Install Firebase Services
After installing the main dependencies, install the Firebase SDK by running:

bash
npm install firebase  
This ensures all Firebase-related services are available for the project.

4. Start the Application
Run the app on a simulator, physical device, or in a web browser by following these steps:

Set up a Simulator (Optional):

Use an Android Emulator or iOS Simulator.
If no simulator is installed, you can run the app in your web browser.
Start the Expo Development Server:

Run the following command to start the Expo server:

bash
npx expo start  
Choose Target Platform:
In the terminal or web interface, select one of the following options:

Press a to run the app on an Android Emulator.
Press i to run the app on an iOS Simulator.
Press w to run the app in a Web Browser.
5. Additional Notes
If you're using a physical device, download the Expo Go app on your device. Then, scan the QR code that appears when the Expo server starts.
To clear cached data and restart the server, use:
bash
expo start --clear  
Quick Workflow Summary:
bash
# Step 1: Clone the repo  
git clone <repository-url>  

# Step 2: Navigate to the project folder  
cd <frontend-or-backend-directory>  

# Step 3: Install npm dependencies  
npm install  

# Step 4: Install Firebase  
npm install firebase  

# Step 5: Start the Expo server  
npx expo start  
Troubleshooting
If the app doesn’t start correctly:
Ensure you have Node.js and npm properly installed.
Make sure Firebase was installed using npm install firebase.
Clear the Expo server cache using expo start --clear.

---
# New as of July 2025
To run the database test, you will need to boot up two servers.

# Step 1: Install Express.js
npm install express

# Step 2: Run the backend
cd backend
node usda.js

# Step 3: Run the frontend
npx expo start

# Step 4: Navigate to the test, named query_test
Input whatever product you want to get information on. The website will provide you with the top 5 results.

# Troubleshooting
- Make sure all your devices are connected to the same wifi network (especially for phone + computer)
- Ensure your IPv4 address is correct (if you have a VPN active, this may change) if you are trying to test on mobile

---
# Camera Function Viewing
- Run the app (npx expo start)
- Navigate to the camera. Input your IPv4 address in the IP field if testing from a phone (found using ipconfig in the terminal)
- Take a photo or upload an image (recommended) to test the function. The program will take you to a separate layout with the OCR results.

All test images can be found in the /app directory, then looking inside the /test_images directory. Be sure to download the images beforehand.
