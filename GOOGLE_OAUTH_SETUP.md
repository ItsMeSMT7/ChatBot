# Google OAuth Setup Guide

## Steps to Enable Google Authentication

### 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Set Application type to "Web application"
6. Add authorized origins:
   - `http://localhost:3000`
   - `http://localhost:3001`
7. Copy the Client ID

### 2. Configure Frontend

1. Open `frontend/.env`
2. Replace `your-google-client-id-here` with your actual Google Client ID:
   ```
   REACT_APP_GOOGLE_CLIENT_ID=your-actual-client-id-here.apps.googleusercontent.com
   ```

### 3. Test the Setup

1. Start the application:
   ```bash
   start_application.bat
   ```
2. Click "Continue with Google" button
3. Complete the Google OAuth flow

## Features Implemented

✅ **Separate Login/Signup Forms**
- Click "Sign In" to open login form
- Click "Sign Up" to open signup form
- Easy switching between forms

✅ **Google OAuth Integration**
- "Continue with Google" button works on both forms
- Automatic user creation for new Google users
- Secure token-based authentication

✅ **Backend Support**
- Google authentication API endpoint
- User creation from Google profile data
- Token generation for authenticated users

## Usage

1. **Manual Registration**: Use email/username and password
2. **Google Sign-in**: One-click authentication with Google account
3. **Form Switching**: Toggle between login and signup easily

The system automatically handles:
- User creation for new Google users
- Username generation from email
- Profile picture from Google account
- Secure authentication tokens