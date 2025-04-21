<template>
  <div class="reddit-posts">
    <div class="subreddit-selector">
      <select v-model="selectedSubreddit" @change="handleSearch">
        <option
          v-for="subreddit in availableSubreddits"
          :key="subreddit"
          :value="subreddit"
        >
          r/{{ subreddit }}
        </option>
      </select>
    </div>

    <div v-if="loading" class="loading">
      Loading posts...
    </div>

    <div v-else-if="error" class="error">
      {{ error }}
    </div>

    <div v-else-if="items.length === 0 && searchPerformed" class="no-results">
      <h3>No Reddit posts found</h3>
      <p>Try a different subreddit or check back later.</p>
    </div>

    <!-- Item List -->
    <div v-else class="posts-container">
      <div
        v-for="item in visibleItems"
        :key="item.id"
        class="post-card"
         :class="{ processing: item.isProcessing }"
      >
        <h3>{{ item.title }}</h3>

        <!-- Topics Section -->
        <div class="topics-container" v-if="item.topics.length">
          <div class="topic-pills">
            <span :class="['topic-pill', getRedditTopicClass(item.topics[0].name)]" :title="item.topics[0].score ? `Distribution: ${(item.topics[0].score).toFixed(3)}` : ''">
                {{ item.topics[0].name }}
            </span>
          </div>
        </div>
         <div v-else-if="item.isProcessing" class="topics-container">
            <div class="processing-message">Analyzing topics...</div>
          </div>


        <!-- Summary Section -->
        <div class="summary-container">
          <p class="post-content" v-html="highlightedSummary(item)"></p>
        </div>

        <div class="post-meta">
          <span>Score: {{ item.score }}</span>
          <span>Comments: {{ item.num_comments }}</span>
          <span>By: {{ item.author }}</span>
          <span>{{ formatDate(item.publishDate) }}</span>
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

        <div class="post-links">
          <a :href="item.redditUrl" target="_blank" rel="noopener noreferrer" class="reddit-link">
            View on Reddit
          </a>
          <a
            v-if="!item.is_self && item.url && !item.url.includes('reddit.com')"
            :href="item.url"
            target="_blank"
            rel="noopener noreferrer"
            class="external-link"
          >
            View External Link
          </a>
        </div>
      </div>
      <!-- Loading More Spinner -->
      <div v-if="loadingMore" class="loading-spinner">
        <div class="spinner"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';

// --- State ---
const items = ref([]); // Renamed from posts
const loading = ref(false);
const error = ref(null);
const searchPerformed = ref(false); // Track if initial load/search happened
const selectedSubreddit = ref('Stocks');
const availableSubreddits = ref([
  'StockMarket', 'Stocks', 'ValueInvesting', 'Options',
  'Investing', 'CryptoCurrency', 'Bogleheads',
]);

// --- Infinite Scroll State ---
const itemsToShow = ref(5);
const loadingMore = ref(false);
const visibleItems = computed(() => items.value.slice(0, itemsToShow.value));

// --- API Fetching ---
// Ideally, this would be in a `useApiSearch` composable
async function handleSearch() {
  loading.value = true;
  error.value = null;
  items.value = [];
  itemsToShow.value = 5; // Reset visible items count
  searchPerformed.value = true; // Mark search as performed

  try {
    const apiUrl = `${import.meta.env.VITE_API_BASE_URL}/api/reddit/search?subreddit=${selectedSubreddit.value}`;
    const response = await fetch(apiUrl);
    if (!response.ok) throw new Error('Request failed');

    const results = await response.json();

    items.value = results.map(post => ({
      ...post,
      // id: post.id, // Assuming API provides unique ID
      // title: post.title,
      // score: post.score,
      // num_comments: post.num_comments,
      author: post.source,
      // publishDate: post.publishDate,
      sentiment: post.sentiment?.label || 'Unknown',
      confidence: typeof post.sentiment?.confidence === 'number' ? post.sentiment.confidence : null,
      topics: post.topics || [],
      generatedSummary: post.summary || '',
      redditUrl: post.link, // Map link to redditUrl
      // url: post.url, // External link if exists
      // is_self: post.is_self, // To determine if external link exists
      ner_results: post.ner_results || [], // For highlighting
      selftext: post.selftext || '' // Used for fallback summary
      // isProcessing: post.isProcessing // Optional: if API indicates processing status
    }));
  } catch (err) {
    error.value = 'Failed to fetch Reddit posts. Please try again later.';
    console.error('Reddit fetch error:', err);
  } finally {
    loading.value = false;
  }
}

// Trigger initial load
onMounted(() => {
  handleSearch();
});

// --- Infinite Scroll Logic ---
// Ideally, this would be in a `useInfiniteScroll` composable
function loadMoreItems() {
  if (visibleItems.value.length >= items.value.length || loadingMore.value) return;

  loadingMore.value = true;
  setTimeout(() => {
    itemsToShow.value += 5;
    loadingMore.value = false;
  }, 500); // Simulate load time
}

let scrollHandler = null;

onMounted(() => {
  scrollHandler = () => {
    const scrollY = window.scrollY;
    const viewportHeight = window.innerHeight;
    const fullHeight = document.documentElement.scrollHeight;
    if (scrollY + viewportHeight >= fullHeight - 150) {
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
// Reusing the same functions as NewsSearch (ideally from shared source)
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
   return String(sentiment).toLowerCase().replace(/\s+/g, '-');
}

// --- Highlighting Logic ---
// Reusing the same functions as NewsSearch (ideally from shared source)
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
// Ideally, this would be in a `useTopicStyling` composable (or combined with the news one)
const redditTopicClassMap = {
  "Reddit Governance & Moons": "reddit-governance",
  "Market ETFs & Index Trading": "reddit-etf",
  "Geopolitics: Oil & Energy": "reddit-energy",
  "Inflation & Fed Policy": "reddit-finance",
  "Options Mechanics (Calls, Puts)": "reddit-options",
  "Crypto Trading & Sentiment": "reddit-crypto",
  "Crypto Tech & Transactions": "reddit-crypto-tech",
  "Tesla, Musk & Investors": "reddit-tesla",
  "Crypto Payments & Loans": "reddit-crypto-loans",
  "Options Strategy & Learning": "reddit-options-strategy",
  "US & Global Economic News": "reddit-economy",
  "Stock Investing (Dividends, Growth)": "reddit-stock",
  "Earnings Reports & Forecasts": "reddit-earnings",
  "Investment Basics & Valuation": "reddit-basics",
  "Reddit Rules & Trading Schemes": "reddit-rules",
  "Meme Stocks & Squeezes (GME, AMC)": "reddit-meme",
  "Options Volatility (IV, VIX)": "reddit-volatility",
  "Investment Strategy & Advice": "reddit-strategy",
  "Trading Predictions & Platforms": "reddit-predictions"
};

function getRedditTopicClass(topicName) {
  return redditTopicClassMap[topicName] || "reddit-default";
}

</script>

<style>
/* ... existing styles ... */
/* Ensure styles for .post-card, .topics-container, .summary-container, .post-meta, .sentiment, .topic-pill, .loading-spinner etc. are defined */
/* --- Base Styles (Consider moving to App.vue or main.css) --- */
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap');

* {
  font-family: "Inter", Arial, sans-serif; /* Add sans-serif fallback */
  box-sizing: border-box; /* Add globally */
}

/* --- Component Specific Styles --- */
.reddit-posts {
  width: 100%;
  /* Removed margin: 0 auto; as App.vue handles centering */
  padding: 20px 0;
}

.subreddit-selector {
  margin-bottom: 30px; /* Increased margin */
  text-align: center;
}

.subreddit-selector select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  padding: 12px 45px 12px 18px; /* Adjusted padding */
  font-size: 16px; /* Slightly larger font */
  border-radius: 8px;
  border: 1px solid #ccc;
  min-width: 280px; /* Wider dropdown */
  background-color: white; /* Ensure background is white */
  background-image: url('data:image/svg+xml;utf8,<svg fill="%23555" height="20" viewBox="0 0 24 24" width="20" xmlns="http://www.w3.org/2000/svg"><path d="M7 10l5 5 5-5z"/></svg>'); /* Darker arrow */
  background-repeat: no-repeat;
  background-position: right 15px center; /* Adjusted arrow position */
  background-size: 18px 18px; /* Adjusted arrow size */
  cursor: pointer;
  transition: border-color 0.2s ease;
}

.subreddit-selector select:hover {
  border-color: #aaa;
}

.subreddit-selector select:focus {
  outline: none;
  border-color: #eca406; /* Highlight color on focus */
  box-shadow: 0 0 0 2px rgba(236, 164, 6, 0.2);
}


.posts-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px; /* Use gap instead of margin-bottom on cards */
}

.post-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  /* Removed margin-bottom */
  box-shadow: 0 5px 8px rgba(98, 65, 0, 0.3);
  border: 1px solid #eee;
  position: relative; /* For processing overlay */
  overflow: hidden;
}

.post-card h3 {
  margin: 0 0 10px 0;
  color: #333; /* Consistent heading color */
  font-weight: 600; /* Slightly bolder titles */
  line-height: 1.3; /* Improve title spacing */
}

/* --- Reusable/Shared Styles (apply consistency) --- */
.summary-container {
  margin: 15px 0;
  padding: 15px;
  background-color: #f8f8f8; /* Slightly different background */
  border-radius: 8px;
  border-left: 4px solid #ff4500; /* Reddit orange */
}

.post-content {
  color: #333;
  line-height: 1.6;
}

strong.highlight {
  font-weight: 675;
  background-color: #ffebae; /* Consistent highlight */
  padding: 1px 3px;
  border-radius: 4px;
  box-shadow: 0 0 0 1px #ffe08a;
}

.post-meta {
  display: flex;
  gap: 15px;
  font-size: 0.9em;
  color: #666;
  margin: 15px 0 10px 0; /* Adjusted margins */
  flex-wrap: wrap;
  align-items: center;
}

.post-meta span { /* Add spacing between meta items */
  margin-right: 5px;
}

.sentiment {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 0.85em;
  font-weight: 500;
  margin-left: auto; /* Push to right */
  text-transform: capitalize;
}
.sentiment.unknown { background-color: #e9ecef; color: #6c757d; }
.sentiment.very-positive { background-color: #a4e1b3; color: #064414; }
.sentiment.positive { background-color: #e6f4ea; color: #1e7e34; }
.sentiment.neutral { background-color: #d7dfe2; color: #6c757d; }
.sentiment.negative { background-color: #fff3cd; color: #856404; }
.sentiment.very-negative { background-color: #f8d7da; color: #721c24; }

.loading, .error {
  text-align: center;
  padding: 30px 20px; /* More padding */
  color: #555;
  font-size: 1.1em;
  margin-top: 20px;
}

.error {
  color: #c90a0a;
  background-color: #fff5f5;
  border: 1px solid #fecaca;
  border-radius: 8px;
}


/* --- Topic Pills Styling --- */
.topics-container {
  margin: 10px 0 15px 0;
}

.topic-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.topic-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 0.85em;
  font-weight: 500;
  color: #333;
  transition: background-color 0.2s, box-shadow 0.2s;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.topic-pill:hover {
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.topic-name {
  margin-right: 4px;
}

/* Reddit-specific topic color palette */
.topic-pill.reddit-governance       { background-color: #fbeae5; border-color: #f8dcd5;}
.topic-pill.reddit-etf              { background-color: #d0ebff; border-color: #bddfff;} /* matches news etf */
.topic-pill.reddit-energy           { background-color: #fce9d8; border-color: #f8dac0;} /* similar to energy in news */
.topic-pill.reddit-finance          { background-color: #e0f0d8; border-color: #cde7c0;} /* matches finance */
.topic-pill.reddit-options          { background-color: #fff1e6; border-color: #ffe3cd;}
.topic-pill.reddit-crypto           { background-color: #e0f7ff; border-color: #ccefff;}
.topic-pill.reddit-crypto-tech      { background-color: #d4f4ff; border-color: #c0ecff;}
.topic-pill.reddit-tesla            { background-color: #ffe0e0; border-color: #f8caca;} /* matches Tesla group */
.topic-pill.reddit-crypto-loans     { background-color: #f3faff; border-color: #e5f5ff;}
.topic-pill.reddit-options-strategy { background-color: #fff4cc; border-color: #ffeeba;} /* soft yellow like earnings */
.topic-pill.reddit-economy          { background-color: #daedfc; border-color: #c6e3fa;}
.topic-pill.reddit-stock            { background-color: #e0e0ff; border-color: #d1d1ff;}
.topic-pill.reddit-earnings         { background-color: #fff4cc; border-color: #ffeeba;}
.topic-pill.reddit-basics           { background-color: #d9f2e6; border-color: #c3e8d9;}
.topic-pill.reddit-rules            { background-color: #f5f5f5; border-color: #e8e8e8;}
.topic-pill.reddit-meme             { background-color: #fbe3ff; border-color: #f7d1ff;} /* meme: pink-ish */
.topic-pill.reddit-volatility       { background-color: #cfe2ff; border-color: #bbd4ff;}
.topic-pill.reddit-strategy         { background-color: #e2f0f0; border-color: #d0e5e5;}
.topic-pill.reddit-predictions      { background-color: #f4e8ff; border-color: #e9d7ff;}
.topic-pill.reddit-default          { background-color: #e9ecef; border-color: #dde2e6;}


/* Processing styles (consistent with NewsSearch) */
.post-card.processing {
  opacity: 0.8;
}

.post-card.processing .post-content::before, /* Apply overlay to content area */
.post-card.processing h3::before /* Apply overlay to title too */
 {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.6);
  z-index: 1;
  border-radius: 8px;
}
.post-card.processing h3 { position: relative; } /* Needed for ::before positioning */

.processing-message {
  text-align: center;
  color: #666;
  font-size: 0.9em;
  padding: 10px;
  background-color: #f8f9fa;
  border-radius: 4px;
  font-style: italic;
}

.processing-text {
  color: #999;
  opacity: 0.7;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.6; }
  100% { opacity: 1; }
}

.post-card.processing .sentiment,
.post-card.processing .topic-pill,
.post-card.processing .summary-container {
  animation: pulse 1.8s infinite ease-in-out;
}

/* Link Styles */
.post-links {
  display: flex;
  gap: 15px;
  margin-top: 15px; /* More space above links */
}

.reddit-link,
.external-link {
  display: inline-block;
  text-decoration: none;
  padding: 6px 14px; /* Adjusted padding */
  border-radius: 6px; /* Slightly rounder */
  font-size: 0.9em;
  font-weight: 500; /* Medium weight */
  transition: all 0.2s ease;
  border: 1px solid transparent; /* Base border */
}

.reddit-link {
  color: #ff4500;
  background-color: #fff0e6; /* Lighter orange background */
  border-color: #ffc9ac; /* Subtle border */
}

.reddit-link:hover {
  background-color: #ffded0; /* Slightly darker hover */
  color: #cc3700; /* Darker text */
  border-color: #ffb38f;
}

.external-link {
  color: #555;
  background-color: #f5f5f5;
  border-color: #ddd;
}

.external-link:hover {
  background-color: #eee;
  border-color: #ccc;
  color: #333;
}

/* Loading spinner (consistent style) */
.loading-spinner {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px 0 60px;
  min-height: 80px;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 5px solid #f3f3f3;
  border-top: 5px solid #eca406; /* Use consistent spinner color */
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.no-results { /* Consistent no-results style */
  text-align: center;
  padding: 30px;
  background-color: #fffbeb;
  border: 1px solid #fef3c7;
  border-radius: 8px;
  color: #b45309;
  margin-top: 20px;
}
.no-results h3 {
  color: #92400e;
  margin-bottom: 8px;
}


</style>