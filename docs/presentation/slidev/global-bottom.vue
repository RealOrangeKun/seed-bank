<script setup lang="ts">
import { useNav } from '@slidev/client'
const { currentPage, total } = useNav()
</script>

<template>
  <footer class="deck-chrome">
    <div class="wm">
      <img src="./media/logos/seed.png" alt="" />
      <span>Seed Bank</span>
    </div>
    <div class="pagenum">{{ currentPage }} / {{ total }}</div>
  </footer>
</template>

<style scoped>
.deck-chrome {
  position: absolute;
  inset: auto 0 0 0;
  height: 2.4rem;
  padding: 0 1.1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  pointer-events: none;
  z-index: 50;
  font-family: 'Inter', sans-serif;
}
.wm {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  opacity: 0.7;
}
.wm img { height: 1.15rem; width: auto; }
.wm span {
  font-size: 0.72rem;
  font-weight: 700;
  /* neutral tone: legible on both the warm off-white and the soil-night bg */
  color: #8a978f;
  letter-spacing: 0.02em;
}
.pagenum {
  font-size: 0.72rem;
  font-weight: 500;
  color: #8a978f;
  opacity: 0.9;
}
</style>
