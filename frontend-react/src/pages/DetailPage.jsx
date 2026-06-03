import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  NavBar, Swiper, Image, Tag, Button, Grid, Dialog, Toast,
} from 'antd-mobile'

// LazyImage: 图片懒加载 + 加载占位 + 失败回退
function LazyImage({ src, alt, className }) {
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)
  // Try to use image CDN proxy for faster loading; fallback to original URL
  const imgUrl = useMemo(() => {
    if (!src || src.startsWith('data:') || src.startsWith('blob:')) return src
    // Use a simple proxy approach — just use original URL for now
    // If images are slow, can add a CDN prefix here later
    return src
  }, [src])

  if (failed) {
    return (
      <div className={`${className || ''} lazy-img-fallback`}
        style={{ background: '#f5f5f5', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ccc', fontSize: 12 }}>
        No Image
      </div>
    )
  }

  return (
    <div className={`${className || ''} lazy-img-wrapper`} style={{ position: 'relative', background: '#eee', minHeight: 200 }}>
      {!loaded && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div className="adm-dot-loading" />
        </div>
      )}
      <img
        src={imgUrl}
        alt={alt || ''}
        loading="lazy"
        onLoad={() => setLoaded(true)}
        onError={() => { setFailed(true); setLoaded(true) }}
        style={{
          width: '100%', height: 'auto', display: loaded ? 'block' : 'none',
          objectFit: 'cover', aspectRatio: '16/9',
        }}
      />
    </div>
  )
}
import { HeartOutline, HeartFill, AddOutline, CheckOutline, LocationOutline } from 'antd-mobile-icons'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import usePropertyStore from '../stores/propertyStore'
import useCompareStore from '../stores/compareStore'
import useUserStore from '../stores/userStore'
import { useT } from '../i18n'
import { fetchAIAnalysis } from '../api'

// Fix Leaflet default icon path issue
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

function formatPrice(property) {
  if (!property) return ''
  const val = property.price_type === 'RENT' ? property.price_rent : property.price_sale
  if (!val) return ''
  if (val >= 10000) {
    return `฿${(val / 10000).toFixed(1)}万`
  }
  return `฿${val.toLocaleString()}`
}

function formatPriceUnit(property, t) {
  return property?.price_type === 'RENT' ? t('perMonth') : ''
}

export default function DetailPage() {
  const t = useT()
  const navigate = useNavigate()
  const { id } = useParams()

  const propertyTypeLabel = {
    CONDO: t('condo'),
    HOUSE: t('house'),
    TOWNHOUSE: t('townhouse'),
    APARTMENT: t('apartment'),
  }
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const markerRef = useRef(null)
  const [contactVisible, setContactVisible] = useState(false)
  const [priceHistory, setPriceHistory] = useState([])
  const [priceHistoryLoading, setPriceHistoryLoading] = useState(false)
  const [aiAnalysis, setAIAnalysis] = useState(null)
  const [aiLoading, setAILoading] = useState(false)
  const [aiVisible, setAIVisible] = useState(false)

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

  // Load price history when property loads
  useEffect(() => {
    if (!property?.id) return
    setPriceHistoryLoading(true)
    import('../api').then(({ fetchPriceHistory }) => {
      fetchPriceHistory(property.id)
        .then(res => setPriceHistory(res.data || []))
        .catch(() => setPriceHistory([]))
        .finally(() => setPriceHistoryLoading(false))
    })
  }, [property?.id])

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
        content: t('loginRequired'),
        confirmText: t('login'),
        onConfirm: () => navigate('/profile'),
      })
      return
    }
    if (property) {
      toggleFavorite(property)
      Toast.show({
        icon: isFav ? 'fail' : 'success',
        content: isFav ? t('unfavorited') : t('favorited'),
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
        Toast.show({ icon: 'fail', content: t('maxCompare') })
        return
      }
      compareStore.addItem(property)
      Toast.show({ icon: 'success', content: t('addedToCompare') })
    }
  }, [property, isCompared, compareStore])

  const handleContact = useCallback(() => {
    if (!property) return
    setContactVisible(true)
  }, [property])

  const handleContactConfirm = useCallback(() => {
    setContactVisible(false)
    Toast.show({ icon: 'success', content: t('consultSent') })
  }, [])

  const handleAIAnalysis = useCallback(async () => {
    if (!property?.id) return
    setAILoading(true)
    setAIVisible(true)
    try {
      const res = await fetchAIAnalysis(property.id)
      setAIAnalysis(res.data)
    } catch (e) {
      setAIAnalysis({ error: '分析失败，请稍后重试' })
      Toast.show({ icon: 'fail', content: 'AI 分析失败' })
    } finally {
      setAILoading(false)
    }
  }, [property?.id])

  function renderAIAnalysisContent() {
    if (aiLoading) {
      return (
        <div style={{ textAlign: 'center', padding: '30px 0' }}>
          <div className="adm-dot-loading" />
          <div style={{ color: '#999', fontSize: 14, marginTop: 12 }}>AI 分析中...</div>
        </div>
      )
    }
    if (!aiAnalysis || aiAnalysis.error) {
      return <div style={{ padding: 20, color: '#999' }}>{aiAnalysis?.error || '暂无分析数据'}</div>
    }
    const pa = aiAnalysis.price_assessment || {}
    const vs = aiAnalysis.value_score || {}
    const tr = aiAnalysis.trend || {}
    const score = vs.score

    return (
      <div className="ai-analysis-content" style={{ padding: '0 4px' }}>
        {/* 一句话总结 */}
        {aiAnalysis.summary && (
          <div style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: '#fff', borderRadius: 8, padding: '10px 14px', marginBottom: 12, fontSize: 13, lineHeight: 1.6 }}>
            {aiAnalysis.summary}
          </div>
        )}

        {/* 评分 */}
        {score != null && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#f5f5f5', borderRadius: 8, padding: '10px 14px', marginBottom: 12 }}>
            <span style={{ fontSize: 14, fontWeight: 600 }}>综合评分</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 24, fontWeight: 700, color: score >= 80 ? '#52c41a' : score >= 60 ? '#faad14' : '#ff4d4f' }}>{score}</span>
              <span style={{ fontSize: 13, color: '#666' }}>{vs.label}</span>
            </div>
          </div>
        )}

        {/* 价格评估 */}
        {pa.level && (
          <div style={{ background: '#f0f5ff', borderRadius: 8, padding: '10px 14px', marginBottom: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>💰 价格评估</div>
            <div style={{ fontSize: 13, color: '#666' }}>{pa.label}</div>
            {pa.avg_price && (
              <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>同区均价：฿{(pa.avg_price / 10000).toFixed(1)}万</div>
            )}
          </div>
        )}

        {/* 价格趋势 */}
        {tr.has_trend && (
          <div style={{ background: tr.direction === 'down' ? '#fff1f0' : tr.direction === 'up' ? '#f6ffed' : '#f5f5f5', borderRadius: 8, padding: '10px 14px', marginBottom: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>📊 价格趋势</div>
            <div style={{ fontSize: 13, color: '#666' }}>{tr.label}</div>
            <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>{tr.records_count} 次记录</div>
          </div>
        )}

        {/* 位置 */}
        <div style={{ background: '#f5f5f5', borderRadius: 8, padding: '10px 14px', marginBottom: 12 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>📍 位置</div>
          <div style={{ fontSize: 13, color: '#666' }}>{aiAnalysis.district || '未知区域'}</div>
        </div>

        {/* 分析时间 */}
        <div style={{ fontSize: 11, color: '#ccc', textAlign: 'right', marginTop: 8 }}>
          AI 分析报告 · {new Date(aiAnalysis.analysis_time).toLocaleString('zh-CN')}
        </div>
      </div>
    )
  }

  if (detailLoading || !property) {
    return (
      <div className="detail-view">
        <NavBar onBack={() => navigate(-1)}>{t('propertyDetail')}</NavBar>
        <div style={{ textAlign: 'center', padding: '80px 0' }}>
          <div className="adm-dot-loading" />
          <div style={{ color: '#999', fontSize: 14, marginTop: 12 }}>{t('loading')}</div>
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
  const priceUnit = formatPriceUnit(property, t)
  const isSale = property.price_type === 'SALE'
  const priceColor = isSale ? 'var(--color-sale)' : 'var(--color-rent)'

  const lat = property.lat || property.latitude
  const lng = property.lng || property.longitude
  const hasLocation = !!lat && !!lng

  return (
    <div className="detail-view">
      {/* NavBar */}
      <NavBar onBack={() => navigate(-1)}>{t('propertyDetail')}</NavBar>

      {/* Image Swiper */}
      <Swiper className="detail-swipe" autoplay={false} indicatorProps={{ color: 'white' }}>
        {images.map((img, idx) => (
          <Swiper.Item key={idx}>
            <LazyImage
              className="swipe-img"
              src={img}
              alt={`${property.title || ''} ${idx + 1}`}
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
            {isSale ? t('sale') : t('rent')}
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
          <span>{property.address || property.district || property.location || t('unknownLocation')}</span>
        </div>
      </div>

      {/* Info Grid */}
      <div className="info-section">
        <div className="section-title">基本信息</div>
        <div className="info-grid">
          <div className="info-item">
            <div className="info-label">{t('layout')}</div>
            <div className="info-value">{property.bedrooms ? `${property.bedrooms}室` : '-'}</div>
          </div>
          <div className="info-item">
            <div className="info-label">{t('area')}</div>
            <div className="info-value">{property.area ? `${property.area}㎡` : '-'}</div>
          </div>
          <div className="info-item">
            <div className="info-label">{t('floor')}</div>
            <div className="info-value">{property.floor || '-'}</div>
          </div>
          <div className="info-item">
            <div className="info-label">{t('decoration')}</div>
            <div className="info-value">{property.decoration || '-'}</div>
          </div>
          <div className="info-item">
            <div className="info-label">{t('propertyType')}</div>
            <div className="info-value">{propertyTypeLabel[property.property_type] || property.property_type || '-'}</div>
          </div>
          <div className="info-item">
            <div className="info-label">{t('source')}</div>
            <div className="info-value">{property.source || '-'}</div>
          </div>
        </div>
      </div>

      {/* Description */}
      {property.description && (
        <div className="desc-section">
          <div className="section-title">{t('description')}</div>
          <p className="desc-text">{property.description}</p>
        </div>
      )}

      {/* Price History */}
      {priceHistory.length > 0 && (
        <div className="price-history-section">
          <div className="section-title">
            📊 价格走势
          </div>
          <div className="price-history-list">
            {priceHistory.map((h, idx) => (
              <div key={idx} className="price-history-item">
                <span className="price-history-date">
                  {new Date(h.recorded_at || h.date).toLocaleDateString()}
                </span>
                <span className="price-history-price">
                  ฿{(h.price || h.price_rent || h.price_sale || 0).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Map */}
      {hasLocation && (
        <div className="map-section">
          <div className="section-title">
            <LocationOutline />
            {t('location')}
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
          fill="none"
          color="primary"
          onClick={handleToggleFavorite}
        >
          {isFav ? <HeartFill style={{ color: 'red' }} /> : <HeartOutline />}
          <span style={{ marginLeft: 4 }}>{isFav ? t('favorited') : t('favorite')}</span>
        </Button>
        <Button
          style={{ flex: 1 }}
          fill={isCompared ? 'solid' : 'none'}
          color="primary"
          onClick={handleToggleCompare}
        >
          {isCompared ? <CheckOutline /> : <AddOutline />}
          <span style={{ marginLeft: 4 }}>{isCompared ? t('inCompare') : t('addCompare')}</span>
        </Button>
        <Button
          style={{ flex: 1 }}
          color="success"
          fill="none"
          onClick={handleAIAnalysis}
        >
          🤖 AI
        </Button>
        <Button
          style={{ flex: 1.5 }}
          color="warning"
          fill="solid"
          onClick={handleContact}
        >
          {t('contact')}
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
              {t('contactDesc')}
            </p>
          </div>
        }
        actions={[
          { key: 'cancel', text: t('cancel'), onClick: () => setContactVisible(false) },
          { key: 'confirm', text: t('contactConfirm'), bold: true, color: 'warning', onClick: handleContactConfirm },
        ]}
      />

      {/* AI Analysis Dialog */}
      <Dialog
        visible={aiVisible}
        onClose={() => { setAIVisible(false); setAIAnalysis(null) }}
        content={renderAIAnalysisContent()}
        actions={[
          { key: 'close', text: '关闭', onClick: () => { setAIVisible(false); setAIAnalysis(null) } },
        ]}
      />
    </div>
  )
}
