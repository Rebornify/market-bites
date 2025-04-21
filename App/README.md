# is450-project: Market Bites

Market Bites is a full-stack text mining application that analyzes recent financial news and Reddit posts for key topics, named entities, and sentiment. Users can search for companies (e.g. Google, Tesla) and get bite-sized insights from real-time data.

## Recommended IDE Setup

[VSCode](https://code.visualstudio.com/) + [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```

### Start the frontend

```sh
npm run dev
```

### Compile and Minify for Production

```sh
npm run build
```

### Lint with [ESLint](https://eslint.org/)

```sh
npm run lint
```

### Start the backend
```sh
cd backend
python app.py
```

### Populate database hourly for latest news and reddit posts
```sh
cd backend
python scheduler.py
```
