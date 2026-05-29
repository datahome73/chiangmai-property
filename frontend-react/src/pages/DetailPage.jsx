import React, { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  NavBar, Swiper, Image, Tag, Button, Grid, Dialog, Toast,
} from 'antd-mobile'
import { HeartOutline, HeartFill, AddOutline, CheckOutline, LocationOutline } from 'antd-mobile-icons'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import usePropertyStore from '../stores/propertyStore'
import useCompareStore from '../stores/compareStore'
import useUserStore from '../stores/userStore'

// Fix Leaflet default icon path issue
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const propertyTypeLabel = {
  CONDO: '公寓',
  HOUSE: '别墅',
  TOWNHOUSE: '联排别墅',
  APARTMENT: '普通公寓',
}

function formatPrice(property) {
  if (!property) return ''
  const val = property.price_type === 'RENT' ? property.price_rent : property.price_sale
  if (!val) return ''
  if (val >= 10000) {
    return `฿${(val / 10000).toFixed(1)}万`
  }
  return `฿${val.toLocaleString()}`
}

function formatPriceUnit(property) {
  return property?.price_type === 'RENT' ? '/月' : ''
}

export default function DetailPage() {
  const navigate = useNavigate()
  const { id } = useParams()
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const markerRef = useRef(null)
  const [contactVisible, setContactVisible] = useState(false)

  const {
    currentProperty,
    detailLoading,
    loadPropertyDetail,
    toggleFavorite,
    isFavorite,
} = usePropertyStore()
  const compareStore = useCompareStore()
  const userStore = useUserStore()

  const property = currentProperty
  const isFav = property ? isFavorite(property.id) : false
  const isCompared = property ? compareStore.hasItem(property.id) : false

  // Load detail on mount
  useEffect(() => {
    if (id) {
      loadPropertyDetail(id)
    }
  }, [id])

  // Initialize map after property loads
  useEffect(() => {
    if (!property) return

    const lat = property.lat || property.latitude
    const lng = property.lng || property.longitude

    if (!lat || !lng) return

    // Wait a tick for DOM to render the map container
    const timer = setTimeout(() => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }

      if (mapRef.current) {
        const map = L.map(mapRef.current, {
          center: [lat, lng],
          zoom: 15,
          zoomControl: true,
        })

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
          maxZoom: 19,
        }).addTo(map)

        const marker = L.marker([lat, lng]).addTo(map)
        marker.bindPopup(property.title || '')

        markerRef.current = marker
        mapInstanceRef.current = map

        // Fix map rendering after container is visible
        setTimeout(() => {
          map.invalidateSize()
        }, 300)
      }
    }, 100)

    return () => {
      clearTimeout(timer)
    }
  }, [property])

  // Cleanup map on unmount
  useEffect(() => {
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove()
        mapInstanceRef.current = null
      }
    }
  }, [])

  const handleToggleFavorite = useCallback(() => {
    if (!userStore.isLoggedIn()) {
      Dialog.confirm({
        content: '请先登录后再收藏房源',
        confirmText: '去登录',
        onConfirm: () => navigate('/profile'),
      })
      return
    }
    if (property) {
      toggleFavorite(property)
      Toast.show({
        icon: isFav ? 'fail' : 'success',
        content: isFav ? '已取消收藏' : '已收藏',
      })
    }
  }, [property, toggleFavorite, isFav, userStore, navigate])

  const handleToggleCompare = useCallback(() => {
    if (!property) return
    if (isCompared) {
      compareStore.removeItem(property.id)
      Toast.show({ content: '已移出比价列表' })
    } else {
      if (compareStore.count >= 4) {
        Toast.show({ icon: 'fail', content: '比价列表最多4套房源' })
        return
      }
      compareStore.addItem(property)
      Toast.show({ icon: 'success', content: '已加入比价列表' })
    }
  }, [property, isCompared, compareStore])

  const handleContact = useCallback(() => {
    if (!property) return
    setContactVisible(true)
  }, [property])

  const handleContactConfirm = useCallback(() => {
    setContactVisible(false)
    Toast.show({ icon: 'success', content: '已发送咨询请求，中介将尽快联系您' })
  }, [])

  if (detailLoading || !property) {
    return (
      <div className="detail-view">
        <NavBar onBack={() => navigate(-1)}>房产详情</NavBar>
        <div style={{ textAlign: 'center', padding: '80px 0' }}>
          <div className="adm-dot-loading" />
          <div style={{ color: '#999', fontSize: 14, marginTop: 12 }}>加载中...</div>
        </div>
      </div>
    )
  }

  const images = property.images && property.images.length > 0
    ? property.images
    : property.image
      ? [property.image]
      : ['https://via.placeholder.com/600x280?text=No+Image']

  const price = formatPrice(property)
  const priceUnit = formatPriceUnit(property)
  const isSale = property.price_type === 'SALE'
  const priceColor = isSale ? 'var(--color-sale)' : 'var(--color-rent)'

  const lat = property.lat || property.latitude
  const lng = property.lng || property.longitude
  const hasLocation = !!lat && !!lng

  return (
    <div className="detail-view">
      {/* NavBar */}
      <NavBar onBack={() => navigate(-1)}>房产详情</NavBar>

      {/* Image Swiper */}
      <Swiper className="detail-swipe" autoplay={false} indicatorProps={{ color: 'white' }}>
        {images.map((img, idx) => (
          <Swiper.Item key={idx}>
            <img
              className="swipe-img"
              src={img}
              alt={`${property.title || ''} ${idx + 1}`}
              onError={(e) => {
                e.target.src = 'https://via.placeholder.com/600x280?text=No+Image'
              }}
            />
          </Swiper.Item>
        ))}
      </Swiper>

      {/* Price Section */}
      <div className="price-section">
        <div className="price-row">
          <span className="price-amount" style={{ color: priceColor }}>
            {price}
          </span>
          {priceUnit && <span className="price-unit">{priceUnit}</span>}
        </div>
        <div className="tag-row">
          <Tag color={isSale ? 'success' : 'danger'}>
            {isSale ? '出售' : '出租'}
          </Tag>
          {property.source && (
            <Tag color="primary" fill="outline">
              {property.source}
            </Tag>
          )}
          {property.decoration && (
            <Tag color="warning" fill="outline">
              {property.decoration}
            </Tag>
          )}
        </div>
      </div>

      {/* Title & Location */}
      <div className="title-section">
        <h1 className="detail-title">{property.title}</h1>
        <div className="location-row">
          <LocationOutline />
          <span>{property.address || property.district || property.location || '暂无地址信息'}</span>
        </div>
      </div>

      {/* Info Grid */}
      <div className="info-section">
        <div className="section-title">基本信息</div>
        <div className="info-grid">
          <div className="info-item">
            <div className="info-label">户型</div>
            <div className="info-value">{property.bedrooms ? `${property.bedrooms}室` : '-'}</div>
          </div>
          <div className="info-item">
            <div className="info-label">面积</div>
            <div className="info-value">{property.area ? `${property.area}㎡` : '-'}</div>
          </div>
          <div className="info-item">
            <div className="info-label">楼层</div>
            <div className="info-value">{property.floor || '-'}</div>
          </div>
          <div className="info-item">
            <div className="info-label">装修</div>
            <div className="info-value">{property.decoration || '-'}</div>
          </div>
          <div className="info-item">
            <div className="info-label">类型</div>
            <div className="info-value">{propertyTypeLabel[property.property_type] || property.property_type || '-'}</div>
          </div>
          <div className="info-item">
            <div className="info-label">来源</div>
            <div className="info-value">{property.source || '-'}</div>
          </div>
        </div>
      </div>

      {/* Description */}
      {property.description && (
        <div className="desc-section">
          <div className="section-title">房源描述</div>
          <p className="desc-text">{property.description}</p>
        </div>
      )}

      {/* Map */}
      {hasLocation && (
        <div className="map-section">
          <div className="section-title">
            <LocationOutline />
            位置信息
          </div>
          {property.address && (
            <div className="location-text">
              <LocationOutline />
              <span>{property.address}</span>
            </div>
          )}
          <div
            className="detail-map"
            ref={mapRef}
            style={{ width: '100%', height: 250, borderRadius: 8 }}
          />
        </div>
      )}

      {/* Bottom Action Bar */}
      <div className="bottom-bar">
        <Button
          style={{ flex: 1 }}
          fill={isFav ? 'solid' : 'none'}
          color="default"
          onClick={handleToggleFavorite}
        >
          {isFav ? <HeartFill style={{ color: 'red' }} /> : <HeartOutline />}
          <span style={{ marginLeft: 4 }}>{isFav ? '已收藏' : '收藏'}</span>
        </Button>
        <Button
          style={{ flex: 1 }}
          fill={isCompared ? 'solid' : 'none'}
          color="primary"
          onClick={handleToggleCompare}
        >
          {isCompared ? <CheckOutline /> : <AddOutline />}
          <span style={{ marginLeft: 4 }}>{isCompared ? '已加入' : '加入比价'}</span>
        </Button>
        <Button
          style={{ flex: 1.5 }}
          color="warning"
          fill="solid"
          onClick={handleContact}
        >
          联系中介
        </Button>
      </div>

      {/* Contact Dialog */}
      <Dialog
        visible={contactVisible}
        onClose={() => setContactVisible(false)}
        content={
          <div className="contact-content">
            <div style={{ fontSize: 40, marginBottom: 8 }}>🏠</div>
            <p>
              对 {property.title || '该房源'} 感兴趣？
            </p>
            <p style={{ fontSize: 13, color: '#999' }}>
              我们将为您联系对应中介，获取更多详细信息。
            </p>
          </div>
        }
        actions={[
          { key: 'cancel', text: '取消', onClick: () => setContactVisible(false) },
          { key: 'confirm', text: '确认咨询', bold: true, color: 'warning', onClick: handleContactConfirm },
        ]}
      />
    </div>
  )
}
