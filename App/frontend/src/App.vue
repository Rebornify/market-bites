<!-- src/App.vue -->

<template>
  <div class="app">
    <h1>Market Bites</h1>
    <div class="content-container">
      <SourceToggle v-model="selectedSource"/>
      
      <div v-if="selectedSource === 'reddit'" class="content-section">
        <RedditPosts />
      </div>
      <div v-else class="content-section">
        <NewsSearch />
      </div>
    </div>
  </div>
</template>

<script>
import SourceToggle from './components/SourceToggle.vue';
import RedditPosts from './components/RedditSearch.vue';
import NewsSearch from './components/NewsSearch.vue';

export default {
  name: 'App',
  components: {
    SourceToggle,
    RedditPosts,
    NewsSearch
  },
  data() {
    return {
      selectedSource: 'news'
    };
  }
};
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap');

#app {
  display: block !important;
  grid-template-columns: none !important;
}

.app {
  font-family: 'Inter', Arial;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  display: flex !important;
  flex-direction: column;
  align-items: center;
  box-sizing: border-box;
}

.content-container {
  width: 100%;
  max-width: 800px;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-sizing: border-box;
}

.content-section {
  width: 100%;
  box-sizing: border-box;
}

h1 {
  text-align: center;
  color: #333;
  margin-bottom: 5px;
  width: 100%;
  font-weight: 900;
  font-size: 60px;
}

.placeholder {
  text-align: center;
  padding: 40px;
  background: #dcdcdc;
  border-radius: 8px;
  color: #666;
}
</style>
