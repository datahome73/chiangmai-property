import React, { useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import usePropertyStore from '../stores/propertyStore'
import { useT } from '../i18n'

// Fix default leaflet icon issue
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

export default function MapPage() {
  const navigate = useNavigate()
  const t = useT()
  const mapRef = useRef(null)
  const markerLayerRef = useRef(null)
  const mapInstanceRef = useRef(null)

  const markers = usePropertyStore((s) => s.markers)
  const fetchMarkers = usePropertyStore((s) => s.fetchMarkers)
  const getPriceLabel = usePropertyStore((s) => s.getPriceLabel)

  // Initialize map
  useEffect(() => {
    if (mapInstanceRef.current) return

    const map = L.map('map', {
      center: [18.7883, 98.9853],
      zoom: 12,
      zoomControl: true,
      attributionControl: false,
    })

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
    }).addTo(map)

    mapInstanceRef.current = map
    markerLayerRef.current = L.layerGroup().addTo(map)

    // Fetch markers when map moves
    const handleMoveEnd = () => {
      const bounds = map.getBounds()
      fetchMarkers({
        min_lat: bounds.getSouth(),
        max_lat: bounds.getNorth(),
        min_lng: bounds.getWest(),
        max_lng: bounds.getEast(),
      })
    }

    map.on('moveend', handleMoveEnd)

    // Initial fetch
    fetchMarkers({
      min_lat: map.getBounds().getSouth(),
      max_lat: map.getBounds().getNorth(),
      min_lng: map.getBounds().getWest(),
      max_lng: map.getBounds().getEast(),
    })

    return () => {
      map.remove()
      mapInstanceRef.current = null
    }
  }, [fetchMarkers])

  // Update markers when data changes
  useEffect(() => {
    const layer = markerLayerRef.current
    if (!layer) return

    layer.clearLayers()

    if (!markers || markers.length === 0) return

    markers.forEach((marker) => {
      const lat = marker.lat || marker.latitude
      const lng = marker.lng || marker.longitude
      if (!lat || !lng) return

      const isRent = marker.price_type === 'RENT'
      const price = isRent ? marker.price_rent : marker.price_sale
      const color = isRent ? '#ee0a24' : '#07c160'
      const labelText = price
        ? `฿${price >= 10000 ? `${(price / 10000).toFixed(1)}万` : price.toLocaleString()}`
        : ''

      const html = `
        <div style="
          background: ${color};
          color: #fff;
          border-radius: 12px;
          padding: 4px 8px;
          font-size: 11px;
          font-weight: 600;
          white-space: nowrap;
          box-shadow: 0 2px 6px rgba(0,0,0,0.3);
          border: 2px solid #fff;
          display: flex;
          align-items: center;
          gap: 4px;
          cursor: pointer;
        ">
          <span style="
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #fff;
            display: inline-block;
          "></span>
          ${labelText}
        </div>
      `

      const icon = L.divIcon({
        html,
        className: '',
        iconSize: [80, 28],
        iconAnchor: [40, 14],
        popupAnchor: [0, -18],
      })

      const leafletMarker = L.marker([lat, lng], { icon }).addTo(layer)

      const thumbnail = marker.images?.[0] || ''
      const title = marker.title || ''

      const popupHtml = `
        <div style="width: 200px; cursor: pointer;" onclick="window.__mapNavigate && window.__mapNavigate('${marker.id}')">
          ${thumbnail ? `<img src="${thumbnail}" alt="" style="width:100%;height:100px;object-fit:cover;border-radius:6px;margin-bottom:6px;" />` : ''}
          <div style="font-size:16px;font-weight:700;color:${color};margin-bottom:2px;">
            ${labelText}
          </div>
          <div style="font-size:13px;color:#333;line-height:1.3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
            ${title}
          </div>
        </div>
      `

      leafletMarker.bindPopup(popupHtml, { maxWidth: 220, className: '' })
    })
  }, [markers])

  // Global navigate function for popup clicks
  useEffect(() => {
    window.__mapNavigate = (id) => {
      navigate(`/detail/${id}`)
    }
    return () => {
      delete window.__mapNavigate
    }
  }, [navigate])

  const handleSearchClick = useCallback(() => {
    navigate('/search')
  }, [navigate])

  return (
    <div className="map-view">
      <div id="map" />
      <div className="map-search-overlay" onClick={handleSearchClick}>
        <div
          style={{
            background: 'rgba(255,255,255,0.95)',
            borderRadius: '24px',
            padding: '10px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            boxShadow: '0 2px 12px rgba(0,0,0,0.12)',
            backdropFilter: 'blur(4px)',
          }}
        >
          <span style={{ fontSize: 16 }}>🔍</span>
          <span style={{ color: '#999', fontSize: 14 }}>{t('searchOnMap')}</span>
        </div>
      </div>
    </div>
  )
}
