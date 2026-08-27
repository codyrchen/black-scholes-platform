# Quick Start Guide

## Starting the Application

You need **TWO terminal windows** running simultaneously:

### Terminal 1: Backend (Flask Server)

```bash
cd /Users/codychen/black-scholes-platform
python3 app.py
```

**OR use the startup script:**
```bash
cd /Users/codychen/black-scholes-platform
./start_backend.sh
```

You should see:
```
==================================================
Starting Black-Scholes Backend Server
==================================================
Server URL: http://localhost:5000
Health check: http://localhost:5000/api/health
==================================================
Press Ctrl+C to stop the server
==================================================

 * Running on http://0.0.0.0:5000
```

**Keep this terminal open!** The server must stay running.

### Terminal 2: Frontend (React App)

```bash
cd /Users/codychen/black-scholes-platform/frontend
npm start
```

The React app will open in your browser at `http://localhost:3000`

## Testing the Backend

To verify the backend is running, in a new terminal:

```bash
cd /Users/codychen/black-scholes-platform
python3 test_backend.py
```

Or manually test:
```bash
curl http://localhost:5000/api/health
```

## Troubleshooting

### "Backend Status: ✗ Not Connected"

1. **Check if Flask is running:**
   - Look at Terminal 1 - you should see the Flask server output
   - If not, start it with `python3 app.py`

2. **Test the connection:**
   ```bash
   python3 test_backend.py
   ```

3. **Check for port conflicts:**
   ```bash
   lsof -ti:5000
   ```
   If something is using port 5000, kill it:
   ```bash
   lsof -ti:5000 | xargs kill
   ```

4. **Verify dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

### "Failed to fetch" Error

- Make sure Flask server is running (Terminal 1)
- Check that both servers are running:
  - Flask on port 5000
  - React on port 3000
- Try refreshing the browser
- Check browser console (F12) for detailed errors

## Important Notes

- **Both servers must run at the same time**
- Flask server must be started **before** using the React app
- Keep both terminal windows open while using the app
- The frontend will automatically detect when the backend comes online
