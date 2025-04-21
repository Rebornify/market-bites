<template>
  <div class="news-search">
    <div class="search-container">
      <input
        type="text"
        v-model="searchQuery"
        placeholder="Enter company name"
        @keyup.enter="handleSearch"
      />
      <button @click="handleSearch" :disabled="loading">
        {{ loading ? 'Searching...' : 'Search' }}
      </button>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <!-- Item List -->
    <div v-else-if="items.length > 0" class="articles-container">
      <div
        v-for="item in visibleItems"
        :key="item.id"
        :class="['article-card', { processing: item.isProcessing }]"
      >
        <div class="article-content">
          <h3>{{ item.title }}</h3>

          <!-- Topics Section -->
          <div class="topics-container" v-if="item.topics.length">
            <div class="topic-pills">
              <span :class="['topic-pill', getTopicClass(item.topics[0].topic)]" :title="item.topics[0].score ? `Distribution: ${(item.topics[0].score).toFixed(3)}` : ''">
                {{ item.topics[0].topic }}
              </span>
            </div>
          </div>
          <div v-else-if="item.isProcessing" class="topics-container">
            <div class="processing-message">Analyzing topics...</div>
          </div>

          <!-- Summary Section -->
          <div class="summary-container">
             <!-- Using computed property for highlighted summary -->
            <p class="post-content" v-html="highlightedSummary(item)"></p>
          </div>

          <div class="article-meta">
            <span class="source">{{ item.source }}</span>
            <span class="date">{{ formatDate(item.publishDate) }}</span>
            <span
              :class="['sentiment', getSentimentClass(item.sentiment)]"
              :title="item.confidence ? `Confidence: ${(item.confidence * 100).toFixed(1)}%` : ''"
            >
              {{ item.sentiment }}
              <span v-if="item.confidence && !item.isProcessing">
                ({{ (item.confidence * 100).toFixed(1) }}%)
              </span>
            </span>
          </div>
          <a :href="item.link" target="_blank" rel="noopener noreferrer" class="read-more">
            Read More
          </a>
        </div>
      </div>
      <!-- Loading More Spinner -->
      <div v-if="loadingMore" class="loading-spinner">
        <div class="spinner"></div>
      </div>
    </div>

    <!-- No results -->
    <div v-else-if="!loading && searchPerformed" class="no-results">
      <h3>No articles found</h3>
      <p>Try searching for a different company or keyword.</p>
    </div>

    <!-- Placeholder -->
    <div v-else-if="!loading" class="news-placeholder">
       <h3>Welcome to Market Bites</h3>
       <p>Enter a company name above to analyze the sentiment of recent financial news.</p>
       <p>Example: <i>Tesla, Microsoft, Amazon, JPMorgan ...</i></p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';

// --- State ---
const searchQuery = ref('');
const items = ref([]); // Renamed from articles for potential generalization
const loading = ref(false);
const error = ref(null);
const searchPerformed = ref(false);

// --- Infinite Scroll State ---
// Extracted logic related to infinite scroll
const itemsToShow = ref(5);
const loadingMore = ref(false);
const visibleItems = computed(() => items.value.slice(0, itemsToShow.value));

// --- API Fetching ---
// Ideally, this would be in a `useApiSearch` composable
async function handleSearch() {
  if (!searchQuery.value.trim()) return;

  loading.value = true;
  error.value = null;
  items.value = [];
  itemsToShow.value = 5; // Reset visible items count
  searchPerformed.value = true;

  try {
    const baseUrl = import.meta.env.VITE_API_BASE_URL;
    const apiUrl = `${baseUrl}/api/news/search?query=${encodeURIComponent(searchQuery.value)}`;
    const response = await fetch(apiUrl);
    if (!response.ok) throw new Error('Request failed');

    const results = await response.json();

    items.value = results.map(article => ({
      ...article,
      // id: article.id, // Assuming API provides a unique ID
      // title: article.title,
      // link: article.link,
      // source: article.source,
      // publishDate: article.publishDate,
      sentiment: article.sentiment?.label || 'Unknown',
      confidence: typeof article.sentiment?.confidence === 'number' ? article.sentiment.confidence : null,
      topics: article.topics || [],
      generatedSummary: article.summary || '',
      // content: article.content, // Used for fallback summary
      ner_results: article.ner_results || [] // Used for highlighting
      // isProcessing: article.isProcessing // Optional: if API indicates processing status
    }));
  } catch (err) {
    error.value = 'Failed to fetch news. Please try again later.';
    console.error('Search error:', err);
  } finally {
    loading.value = false;
  }
}

// --- Infinite Scroll Logic ---
// Ideally, this would be in a `useInfiniteScroll` composable
function loadMoreItems() {
  if (visibleItems.value.length >= items.value.length || loadingMore.value) return;

  loadingMore.value = true;
  // Simulating network delay; adjust as needed
  setTimeout(() => {
    itemsToShow.value += 5; // Increase the number of items to show
    loadingMore.value = false;
  }, 500); // Reduced delay a bit
}

let scrollHandler = null;

onMounted(() => {
  scrollHandler = () => {
    const scrollY = window.scrollY;
    const viewportHeight = window.innerHeight;
    const fullHeight = document.documentElement.scrollHeight;

    // Trigger load more when near the bottom
    if (scrollY + viewportHeight >= fullHeight - 150) { // Slightly larger threshold
      loadMoreItems();
    }
  };
  window.addEventListener('scroll', scrollHandler);
});

onBeforeUnmount(() => {
  if (scrollHandler) {
    window.removeEventListener('scroll', scrollHandler);
  }
});

// --- Formatting Utilities ---
// Ideally, these would be in a `useFormatting` composable or `utils.js`
function formatDate(dateString) {
  if (!dateString) return 'N/A';
  const options = {
    year: 'numeric', month: 'long', day: 'numeric',
    hour: 'numeric', minute: '2-digit', hour12: true,
  };
  try {
    let formatted = new Date(dateString).toLocaleString('en-US', options);
    return formatted.replace('AM', 'am').replace('PM', 'pm');
  } catch (e) {
    console.error("Error formatting date:", dateString, e);
    return "Invalid Date";
  }
}

function getSentimentClass(sentiment) {
    if (!sentiment) return 'unknown';
    return String(sentiment).toLowerCase().replace(/\s+/g, '-'); // Handle potential multiple spaces
}

// --- Highlighting Logic ---
// Ideally, this would be in a `useHighlighting` composable
function escapeRegex(text) {
  if (!text) return '';
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function highlightedSummary(item) {
  // Determine base text (adjust fallback based on component if needed)
  const isReddit = !!item.selftext; // Simple check if it's likely a Reddit item
  const baseText = item.generatedSummary || (isReddit ? (item.selftext || '') : (item.content || '')).slice(0, 200) + (((isReddit ? item.selftext : item.content)?.length ?? 0) > 200 ? '...' : '');

  const ner = item.ner_results || [];
  let highlighted = baseText;

  // 1. Get unique entity texts
  const uniqueEntityTexts = [...new Set(ner.map(e => e.text).filter(Boolean))];

  // 2. Sort unique texts by length descending
  const sortedUniqueEntities = uniqueEntityTexts.sort((a, b) => b.length - a.length);

  // 3. Iterate through unique sorted texts
  sortedUniqueEntities.forEach(entity => {
    const safeEntity = escapeRegex(entity);
    const hasSpecialChar = /[^a-zA-Z0-9\s]/.test(entity);
    const pattern = hasSpecialChar ? `(${safeEntity})` : `\\b(${safeEntity})\\b`;

    try {
      const regex = new RegExp(pattern, 'gi');
      // Replace only on the current state of 'highlighted'
      highlighted = highlighted.replace(regex, (match, p1) => `<strong class="highlight">${p1}</strong>`);
    } catch (e) {
      console.error("Regex error for entity:", entity, e);
    }
  });

  return highlighted;
}


// --- Topic Styling ---
// Ideally, this would be in a `useTopicStyling` composable
const topicClassMap = {
  "Tesla & Electric Vehicles": "topic-tesla",
  "Earnings Estimates & Surprises": "topic-earnings",
  "Elon Musk & Twitter": "topic-elon",
  "Quarterly Financial Results": "topic-earnings", // Duplicate, maps to same class
  "Banks, Interest Rates & Inflation": "topic-finance",
  "Stock Market Movements": "topic-market",
  "Corporate Announcements": "topic-corporate",
  "Yahoo Finance & Earnings Coverage": "topic-yahoo",
  "Big Tech & AI": "topic-tech",
  "Healthcare & Pharmaceuticals": "topic-health",
  "Market Indices & Economic Data": "topic-market", // Duplicate
  "Earnings Calls & Executive Commentary": "topic-earnings", // Duplicate
  "Retail & Consumer Spending": "topic-retail",
  "Analyst Insights & Investment Ideas": "topic-analyst",
  "Media & Streaming": "topic-media",
  "Auto Industry & Labor Strikes": "topic-tesla", // Duplicate
  "Costco & Wholesale Retail": "topic-retail", // Duplicate
  "Insider Trading & Share Activity": "topic-insider",
  "Aerospace & Aviation": "topic-aerospace",
  "E-commerce & Amazon": "topic-ecommerce",
  "Social Media & Advertising": "topic-media", // Duplicate
  "Dividends & Energy Stocks": "topic-energy",
  "Industrial Tech & Conglomerates": "topic-industrial",
  "ETFs & Asset Management": "topic-etf",
  "AI & Semiconductors": "topic-tech" // Duplicate
};

function getTopicClass(topicName) {
  return topicClassMap[topicName] || "topic-default";
}

</script>

<style>
/* ... existing styles ... */
/* Ensure styles for .article-card, .topics-container, .summary-container, .article-meta, .sentiment, .topic-pill, .loading-spinner etc. are defined */
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap');

* {
  font-family: "Inter", Arial;
}

h3 {
  font-weight: 650
}

.news-search {
  width: 100%;
  padding: 20px 0;
}

.search-container {
  display: flex;
  gap: 10px;
  margin-bottom: 30px;
  justify-content: center;
}

.search-container input {
  padding: 10px 16px;
  font-size: 16px;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 100%;
  max-width: 400px;
}

.search-container button {
  padding: 10px 20px;
  font-size: 16px;
  background-color: #eca406;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
  font-weight: 700;
}

.search-container button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.search-container button:hover:not(:disabled) {
  background-color: #666; /* Consider a different hover color e.g. #d49005 */
}

.error-message {
  color: #c90a0a;
  text-align: center;
  padding: 20px;
  background-color: #fff5f5;
  border-radius: 4px;
  margin: 20px 0;
}

.articles-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.article-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 5px 8px rgba(98, 65, 0, 0.3);
  border: 1px solid #eee;
  /* Added for processing overlay */
  position: relative;
  overflow: hidden; /* Contain pseudo-elements */
}

.article-content h3 {
  margin: 0 0 10px 0;
  color: #333;
}

.summary-container {
  margin: 15px 0;
  padding: 15px;
  background-color: #f2f6f7;
  border-radius: 8px;
  border-left: 4px solid #241f6e; /* Specific color for news summaries */
}

.post-content { /* Generic class for summary text */
  color: #333; /* Darker text for better readability */
  line-height: 1.6; /* Improved line spacing */
}


strong.highlight {
  font-weight: 668; /* Slightly bolder */
  background-color: #ffebae; /* Adjusted highlight color */
  padding: 1px 3px; /* Slightly more padding */
  border-radius: 4px;
  box-shadow: 0 0 0 1px #ffe08a; /* Subtle border */
}

.article-meta {
  display: flex;
  gap: 15px;
  font-size: 0.9em;
  color: #666;
  margin: 10px 0;
  flex-wrap: wrap;
  align-items: center; /* Vertically align items if they wrap */
}

.article-meta .source,
.article-meta .date {
  margin-right: 10px; /* Ensure spacing */
}


.sentiment {
  padding: 3px 10px; /* Adjusted padding */
  border-radius: 12px;
  font-size: 0.85em; /* Slightly smaller */
  font-weight: 500; /* Medium weight */
  margin-left: auto; /* Pushes sentiment to the right */
  /* Removed margin-right: 10px; - rely on gap */
  text-transform: capitalize; /* Capitalize sentiment */
}

.sentiment.unknown { /* Style for unknown sentiment */
    background-color: #e9ecef;
    color: #6c757d;
}

.sentiment.very-positive { background-color: #a4e1b3; color: #064414; }
.sentiment.positive { background-color: #e6f4ea; color: #1e7e34; }
.sentiment.neutral { background-color: #d7dfe2; color: #6c757d; }
.sentiment.negative { background-color: #fff3cd; color: #856404; }
.sentiment.very-negative { background-color: #f8d7da; color: #721c24; }


.read-more {
  display: inline-block;
  color: #0079d3;
  text-decoration: none;
  margin-top: 10px;
  font-weight: 500; /* Make it slightly bolder */
}

.read-more:hover {
  text-decoration: underline;
  color: #005a9c; /* Darker blue on hover */
}

.news-placeholder {
  text-align: center;
  padding: 40px;
  background: rgb(255, 250, 244); /* Original desired background */
  border-radius: 12px;
  box-shadow: 2px 5px 8px 2px rgba(98, 65, 0, 0.2);
  color: #555;
}

.news-placeholder h3 {
  color: #333;
  margin-bottom: 15px;
  font-weight: 600;
}

.news-placeholder p {
  margin: 10px 0;
  line-height: 1.5;
  font-weight: 400;
  color: #444;
}

/* --- Topic Pills Styling --- */
.topics-container {
  margin: 10px 0 15px 0; /* Adjusted margin */
}

.topic-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  /* Removed margin-bottom */
}

.topic-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 0.85em; /* Slightly smaller */
  font-weight: 500;
  color: #333; /* Default dark color */
  transition: background-color 0.2s, box-shadow 0.2s;
  border: 1px solid rgba(0, 0, 0, 0.05); /* Subtle border */
}

.topic-pill:hover {
  box-shadow: 0 1px 3px rgba(0,0,0,0.1); /* Add shadow on hover */
}

.topic-name { /* If you were to wrap the name span */
  margin-right: 4px;
}

/* Specific Topic Colors */
.topic-tesla        { background-color: #ffe0e0; border-color: #f8caca; }
.topic-earnings     { background-color: #fff4cc; border-color: #ffeeba; }
.topic-elon         { background-color: #e0f7ff; border-color: #ccefff; }
.topic-finance      { background-color: #e0f0d8; border-color: #cde7c0; }
.topic-market       { background-color: #f0e5ff; border-color: #e3d4ff; }
.topic-corporate    { background-color: #f5f5f5; border-color: #e8e8e8; }
.topic-yahoo        { background-color: #e0e0ff; border-color: #d1d1ff; }
.topic-tech         { background-color: #d0ebff; border-color: #bddfff; }
.topic-health       { background-color: #eaf4fc; border-color: #d7e9f7; }
.topic-retail       { background-color: #fff1e6; border-color: #ffe3cd; }
.topic-analyst      { background-color: #d9f2e6; border-color: #c3e8d9; }
.topic-media        { background-color: #fbe3ff; border-color: #f7d1ff; }
.topic-insider      { background-color: #ffe2cc; border-color: #ffd6b8; }
.topic-aerospace    { background-color: #cfe2ff; border-color: #bbd4ff; }
.topic-ecommerce    { background-color: #f6e6ff; border-color: #edd5ff; }
.topic-energy       { background-color: #fce9d8; border-color: #f8dac0; }
.topic-industrial   { background-color: #e2f0f0; border-color: #d0e5e5; }
.topic-etf          { background-color: #f4e8ff; border-color: #e9d7ff; }
.topic-default      { background-color: #e9ecef; border-color: #dde2e6; }


/* --- Processing / Loading Styles --- */
.article-card.processing {
  opacity: 0.8; /* Slightly less opaque */
}

/* Use a pseudo-element for overlay instead of ::after on the card itself */
.article-card.processing .article-content::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.6); /* Lighter overlay */
  z-index: 1; /* Ensure overlay is above content */
  border-radius: 8px; /* Match card radius */
}

.processing-message {
  text-align: center;
  color: #666;
  font-size: 0.9em;
  padding: 10px;
  background-color: #f8f9fa;
  border-radius: 4px;
  font-style: italic;
}

.processing-text { /* Applied to text that should look disabled */
  color: #999;
  opacity: 0.7;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.6; } /* Deeper pulse */
  100% { opacity: 1; }
}

/* Apply pulse animation selectively */
.article-card.processing .sentiment,
.article-card.processing .topic-pill,
.article-card.processing .summary-container {
  animation: pulse 1.8s infinite ease-in-out; /* Slower, smoother pulse */
}


.no-results {
  text-align: center;
  padding: 30px; /* More padding */
  background-color: #fffbeb; /* Softer yellow */
  border: 1px solid #fef3c7; /* Matching border */
  border-radius: 8px;
  color: #b45309; /* Darker warning text */
  margin-top: 20px;
}
.no-results h3 {
  color: #92400e;
  margin-bottom: 8px;
}


/* Loading spinner */
.loading-spinner {
  display: flex;
  justify-content: center;
  align-items: center; /* Center vertically */
  padding: 40px 0 60px; /* Consistent padding */
  min-height: 80px; /* Ensure space for spinner */
}

.spinner {
  width: 36px; /* Slightly larger */
  height: 36px;
  border: 5px solid #f3f3f3; /* Slightly thicker border */
  border-top: 5px solid #eca406;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>