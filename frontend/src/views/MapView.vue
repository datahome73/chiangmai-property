<template>
  <div class="map-view">
    <div id="map" ref="mapRef"></div>
    <div class="search-overlay" @click="goSearch">
      <van-search
        placeholder="搜索房源..."
        shape="round"
        background="rgba(255,255,255,0.85)"
        :clearable="false"
        readonly
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePropertyStore } from '@/stores/property'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const router = useRouter()
const store = usePropertyStore()
const mapRef = ref(null)
let mapInstance = null
let markersLayer = null

function formatPrice(property) {
  const val = store.getPriceValue(property)
  if (!val) return ''
  if (val >= 10000) {
    return `฿${(val / 10000).toFixed(1)}万${property.price_type === 'rent' ? '/月' : ''}`
  }
  return `฿${val.toLocaleString()}${property.price_type === 'rent' ? '/月' : ''}`
}

function createMarkerIcon(property) {
  const isRent = property.price_type === 'rent'
  const color = isRent ? '#ee0a24' : '#07c160'
  const price = formatPrice(property)

  return L.divIcon({
    className: 'property-marker',
    html: `<div style="display:flex;flex-direction:column;align-items:center;pointer-events:auto;">
      <div style="background:${color};width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 2px 4px rgba(0,0,0,0.3);"></div>
      <span style="background:${color};color:#fff;font-size:10px;font-weight:600;padding:1px 5px;border-radius:4px;white-space:nowrap;margin-top:2px;line-height:1.5;">${price}</span>
    </div>`,
    iconSize: [80, 34],
    iconAnchor: [40, 34],
    popupAnchor: [0, -34]
  })
}

function renderMarkers() {
  if (!mapInstance) return

  // Clear existing markers
  if (markersLayer) {
    mapInstance.removeLayer(markersLayer)
  }

  markersLayer = L.layerGroup()

  const props = store.filteredProperties
  props.forEach(p => {
    if (p.lat == null || p.lng == null) return

    const marker = L.marker([p.lat, p.lng], {
      icon: createMarkerIcon(p)
    })

    const thumb = p.images?.[0] || 'https://via.placeholder.com/200x150/667eea/ffffff?text=CM'
    const priceLabel = store.getPriceLabel(p)

    marker.bindPopup(`
      <div style="min-width:180px;max-width:240px;">
        <img src="${thumb}" alt="" style="width:100%;height:110px;object-fit:cover;border-radius:6px;margin-bottom:8px;" />
        <div style="font-size:17px;font-weight:700;color:#ee0a24;margin-bottom:4px;">${priceLabel}</div>
        <div style="font-size:13px;color:#333;line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">${p.title}</div>
      </div>
    `, { maxWidth: 280, className: 'property-popup' })

    markersLayer.addLayer(marker)
  })

  markersLayer.addTo(mapInstance)
}

function goSearch() {
  router.push({ name: 'search' })
}

onMounted(() => {
  // Load properties if not loaded yet
  if (store.properties.length === 0) {
    store.loadProperties()
  }

  mapInstance = L.map(mapRef.value, {
    center: [18.7883, 98.9853],
    zoom: 12,
    zoomControl: true
  })

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(mapInstance)

  // Render if properties already available
  if (store.properties.length > 0) {
    renderMarkers()
  }
})

// Watch for initial properties load
watch(() => store.properties.length, (val) => {
  if (val > 0) {
    renderMarkers()
  }
})

// Watch for filter/sort changes
watch(() => store.filteredProperties, () => {
  if (store.properties.length > 0 && mapInstance) {
    renderMarkers()
  }
}, { deep: true })
</script>

<style scoped>
.map-view {
  width: 100%;
  height: calc(100vh - 50px);
  position: relative;
}

#map {
  width: 100%;
  height: 100%;
}

.search-overlay {
  position: absolute;
  top: 12px;
  left: 12px;
  right: 12px;
  z-index: 1000;
  cursor: pointer;
}

.search-overlay :deep(.van-search) {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
</style>

<style>
/* Global style overrides for leaflet markers */
.property-marker {
  background: transparent !important;
  border: none !important;
}

.property-popup .leaflet-popup-content-wrapper {
  border-radius: 10px;
  padding: 4px;
}

.property-popup .leaflet-popup-content {
  margin: 10px 12px;
}
</style>
