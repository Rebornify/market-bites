# Market Bites Application

Market Bites is a full-stack text mining application that analyzes recent financial news and Reddit posts for key topics, named entities, and sentiment. Users can search for companies (e.g. Google, Tesla) and get bite-sized insights from real-time data.

## How to Run the Application

To run the application, you need to start both the frontend and backend servers. Follow the steps below.

### 1. Start the Backend Server

The backend is a Python Flask server that serves data to the frontend.

**Open a new terminal** and run the following commands:

```sh
# Navigate to the backend directory
cd backend

# Install the required Python packages
pip install -r requirements.txt

# Start the server
python app.py
```
The backend will be running at `http://127.0.0.1:5000`.

### 2. Start the Frontend Application

The frontend is a Vue.js application.

**Open a second terminal** and run the following commands:

```sh
# Navigate to the frontend directory
cd frontend

# Install the required npm packages
npm install

# Start the development server
npm run dev
```
You can now access the web application at the local URL provided by Vite (usually `http://localhost:5173`).

---

## Optional: Hourly Data Population

The project includes a scheduler to fetch the latest news and Reddit posts every hour. This is **not required** to run the main application.

To run the scheduler, **open a third terminal**:

```sh
# Navigate to the backend directory
cd backend

# Run the scheduler
python scheduler.py
```

## Other Frontend Scripts

### Lint with [ESLint](https://eslint.org/)
This command helps maintain code quality.
```sh
cd frontend
npm run lint
```

### Compile and Minify for Production
This command prepares the frontend code for deployment.
```sh
cd frontend
npm run build
```

## Recommended IDE Setup

[VSCode](https://code.visualstudio.com/) + [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).
